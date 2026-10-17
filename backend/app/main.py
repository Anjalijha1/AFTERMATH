import asyncio
import logging
import os
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .models import RunAccepted, RunInput, RunView, ScenarioIn
from .runner import MockRunner, Runner
from .store import CapacityExceeded, IdempotencyConflict, ScenarioExists, Store

logger = logging.getLogger(__name__)


def _armoriq_status():
    try:
        from . import armoriq
        return armoriq.status()
    except Exception:
        return {'available': False, 'sdk_installed': False, 'api_key_configured': False,
                'missing': ['armoriq adapter failed to load']}


def create_app(db_path=None, runner: Runner | None = None, api_key=None):
    store = Store(db_path or os.getenv('AFTERMATH_DB_PATH', './data/aftermath.db'))
    adapter = runner
    if adapter is None:
        limit = int(os.getenv('AFTERMATH_REFUND_LIMIT_MINOR', '100000'))
        if os.getenv('AFTERMATH_RUNNER', 'mock').strip().lower() in ('live', 'armoriq', 'real'):
            # Live mode reads keys from the environment; as a convenience it also
            # loads the repo-root .env (gitignored) when python-dotenv is installed.
            try:
                from dotenv import load_dotenv
                from pathlib import Path
                load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False)
            except ImportError:
                pass
            from .live_runner import LiveRunner
            adapter = LiveRunner(limit)
        else:
            adapter = MockRunner(limit)
    if hasattr(adapter, 'scenario_lookup'):
        adapter.scenario_lookup = store.get_scenario
    key = api_key if api_key is not None else os.getenv('AFTERMATH_API_KEY', '')

    @asynccontextmanager
    async def lifespan(app):
        # Single API process only. Do not run multiple uvicorn workers against this DB.
        store.recover()
        app.state.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='aftermath')
        try:
            yield
        finally:
            await asyncio.to_thread(app.state.executor.shutdown, wait=True)

    app = FastAPI(title='AFTERMATH Backend', version='0.1.0', lifespan=lifespan,
                  description=('Member 1 backend. Mock runner by default; set AFTERMATH_RUNNER=live with '
                  'ARMORIQ_API_KEY and GEMINI_API_KEY for the real agent + ArmorIQ path.'))
    app.state.store = store
    @app.middleware('http')
    async def guard(request: Request, call_next):
        if key and request.url.path not in ('/health', '/api/health') and request.method != 'OPTIONS':
            supplied_keys = request.headers.getlist('x-api-key')
            supplied = supplied_keys[0] if len(supplied_keys) == 1 else ''
            if not secrets.compare_digest(supplied.encode(), key.encode()):
                return JSONResponse(status_code=401, content={'error': {'code': 'UNAUTHORIZED', 'message': 'Valid X-API-Key required.'}})
        if request.method == 'POST':
            if len(request.headers.getlist('idempotency-key')) > 1:
                return JSONResponse(status_code=422, content={'error': {'code': 'INVALID_IDEMPOTENCY_KEY', 'message': 'Send exactly one Idempotency-Key header.'}})
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                if size > 65_536:
                    return JSONResponse(status_code=413, content={'error': {'code': 'BODY_TOO_LARGE', 'message': 'Maximum request body is 64 KiB.'}})
                # Preserve body for the downstream request parser.
                chunks.append(chunk)
            request._body = b''.join(chunks)
        return await call_next(request)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={'error': exc.detail}, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not echo raw user input in validation errors.
        details = [{'field': '.'.join(map(str, e['loc'])), 'message': e['msg'], 'type': e['type']} for e in exc.errors()]
        return JSONResponse(status_code=422, content={'error': {'code': 'VALIDATION_ERROR', 'message': 'Invalid request.', 'details': details}})

    def route(method, path, **kw):
        """Register /path (legacy, hidden from docs) and /api/path (documented)."""
        def deco(fn):
            app.add_api_route('/api' + path, fn, methods=[method], **kw)
            app.add_api_route(path, fn, methods=[method], include_in_schema=False, **kw)
            return fn
        return deco

    def api_prefix(request):
        # Links keep the prefix the client used: /api clients get /api links, old clients old links.
        return '/api' if request.url.path.startswith('/api/') else ''

    def missing(code, message):
        raise HTTPException(404, detail={'code': code, 'message': message})

    def execute(run_id, inputs):
        try:
            if not store.start(run_id):
                return
            result = adapter.execute(run_id, inputs, lambda kind, message, data: store.emit(run_id, kind, message, data))
            store.complete(run_id, result)
        except Exception:
            logger.exception('Run failed: %s', run_id)
            store.fail(run_id)

    def submit(inputs, idempotency_key, replay_of=None, prefix=''):
        if store.get_scenario(inputs.scenario_id) is None:
            raise HTTPException(422, detail={'code': 'VALIDATION_ERROR', 'message': 'Invalid request.', 'details': [{'field': 'body.scenario_id', 'message': 'Unknown scenario_id. List scenarios with GET /api/scenarios.', 'type': 'scenario_not_found'}]})
        if idempotency_key is not None and not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', idempotency_key):
            raise HTTPException(422, detail={'code': 'INVALID_IDEMPOTENCY_KEY', 'message': 'Key must be 1-128 ASCII letters, digits, dot, underscore, colon or dash.'})
        try:
            run_id, created = store.create(inputs, idempotency_key, replay_of)
        except IdempotencyConflict:
            raise HTTPException(409, detail={'code': 'IDEMPOTENCY_CONFLICT', 'message': 'This key already belongs to different inputs or replay.'})
        except CapacityExceeded:
            raise HTTPException(429, detail={'code': 'RUN_CAPACITY_REACHED', 'message': '100 active runs already queued. Retry later.'}, headers={'Retry-After': '5'})
        if created:
            try:
                app.state.executor.submit(execute, run_id, inputs)
            except Exception:
                store.fail(run_id)
                raise HTTPException(503, detail={'code': 'WORKER_UNAVAILABLE', 'message': 'Run worker unavailable.'})
        return RunAccepted(run_id=run_id, status=store.get(run_id)['status'], status_url=f'{prefix}/runs/{run_id}', execution_mode=getattr(adapter, 'mode', 'mock'))

    @route('GET', '/health')
    def health():
        with store.connection() as db:
            db.execute('SELECT 1')
        return {'status': 'ok', 'execution_mode': getattr(adapter, 'mode', 'mock'),
                'real_armoriq': bool(getattr(adapter, 'real_armoriq', False)),
                'armoriq': _armoriq_status(),
                'mock_refund_limit_minor': getattr(adapter, 'refund_limit_minor', None)}

    @route('GET', '/scenarios')
    def scenarios():
        return {'execution_mode': getattr(adapter, 'mode', 'mock'), 'items': store.list_scenarios()}

    @route('POST', '/scenarios', status_code=201)
    def create_scenario(scenario: ScenarioIn):
        try:
            return store.create_scenario(scenario)
        except ScenarioExists:
            raise HTTPException(409, detail={'code': 'SCENARIO_EXISTS', 'message': 'A scenario with this ID already exists. Scenarios are not edited; pick a new ID.'})
        except CapacityExceeded:
            raise HTTPException(429, detail={'code': 'SCENARIO_LIMIT', 'message': 'At most 200 scenarios can be saved.'})

    @route('GET', '/scenarios/{scenario_id}')
    def get_scenario(scenario_id: str):
        found = store.get_scenario(scenario_id)
        if found is None:
            missing('SCENARIO_NOT_FOUND', 'No scenario exists with this ID.')
        return found

    @route('POST', '/runs', response_model=RunAccepted, status_code=202)
    def start_run(request: Request, inputs: RunInput, idempotency_key: str | None = Header(default=None)):
        return submit(inputs, idempotency_key, prefix=api_prefix(request))

    @route('GET', '/runs')
    def list_runs(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100_000)):
        return store.list_runs(limit, offset)

    @route('GET', '/runs/{run_id}', response_model=RunView)
    def get_run(run_id: str):
        result = store.get(run_id)
        if result is None:
            missing('RUN_NOT_FOUND', 'No run exists with this ID.')
        return result

    @route('GET', '/runs/{run_id}/evidence')
    def evidence(run_id: str):
        result = store.get(run_id)
        if result is None:
            missing('RUN_NOT_FOUND', 'No run exists with this ID.')
        return {'run_id': run_id, 'status': result['status'], 'items': result['evidence']}

    @route('GET', '/runs/{run_id}/events')
    def events(run_id: str):
        # Same data as /evidence. Doc contract name for the ordered timeline.
        return evidence(run_id)

    @route('GET', '/regressions')
    def regressions(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100_000)):
        return store.regressions(limit, offset)

    @route('GET', '/regressions/{regression_id}')
    def regression(regression_id: str):
        fixture = store.regression(regression_id)
        if fixture is None:
            missing('REGRESSION_NOT_FOUND', 'No regression exists with this ID.')
        return fixture

    @route('POST', '/regressions/{regression_id}/replay', response_model=RunAccepted, status_code=202)
    def replay(request: Request, regression_id: str, idempotency_key: str | None = Header(default=None)):
        fixture = store.regression(regression_id)
        if fixture is None:
            missing('REGRESSION_NOT_FOUND', 'No regression exists with this ID.')
        return submit(RunInput.model_validate(fixture['input']), idempotency_key, replay_of=regression_id, prefix=api_prefix(request))

    # Outermost user middleware so guard-generated 401/413/422 responses get CORS.
    app.add_middleware(CORSMiddleware,
                       allow_origins=[s.strip() for s in os.getenv('AFTERMATH_CORS_ORIGINS', 'http://localhost:5173').split(',') if s.strip()],
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'X-API-Key', 'Idempotency-Key'])

    return app


app = create_app()
