import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.models import RunInput
from app.runner import MockRunner
from app.store import Store


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(str(tmp_path / 'test.db'))) as c:
        yield c


def wait(c, run_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        r = c.get('/runs/' + run_id)
        assert r.status_code == 200
        data = r.json()
        if data['status'] in ('completed', 'failed'):
            return data
        time.sleep(0.005)
    pytest.fail('Run failed to reach terminal state')


def run(c, payload, headers=None):
    r = c.post('/runs', json=payload, headers=headers or {})
    assert r.status_code == 202, r.text
    assert r.json()['status_url'] == '/runs/' + r.json()['run_id']
    return wait(c, r.json()['run_id'])


def test_health_and_scenarios(client):
    assert client.get('/health').json()['real_armoriq'] is False
    items = client.get('/scenarios').json()['items']
    assert len(items) == 4
    assert {i['scenario_id'] for i in items} >= {'allowed_refund', 'excessive_refund'}


def test_allowed_refund_evidence(client):
    data = run(client, {'scenario_id': 'allowed_refund'})
    assert data['status'] == 'completed'
    result = data['result']
    assert result['decision'] == 'allowed'
    assert result['amount_minor'] == 50_000
    assert result['state_after']['refunded_minor'] == 50_000
    assert result['state_before']['refunded_minor'] == 0
    assert result['state_mutated'] is True
    assert result['regression_id'] is None
    assert result['execution_mode'] == 'mock'
    events = data['evidence']
    assert [e['sequence'] for e in events] == list(range(1, len(events)+1))
    assert any(e['kind'] == 'policy_decision' and e['data']['provider'] == 'mock' for e in events)
    assert client.get('/runs/'+data['run_id']+'/evidence').json()['items'] == events


@pytest.mark.parametrize('scenario', ['excessive_refund', 'injection_refund', 'account_email_change'])
def test_blocked_no_mutation_and_replay(client, scenario):
    data = run(client, {'scenario_id': scenario})
    result = data['result']
    assert result['decision'] == 'blocked'
    assert result['state_before'] == result['state_after']
    assert not result['state_mutated']
    assert not any(e['kind'] == 'tool_executed' for e in data['evidence'])
    fixture = client.get('/regressions/'+result['regression_id']).json()
    assert fixture['input']['scenario_id'] == scenario
    assert fixture['source_run_id'] == data['run_id']
    response = client.post('/regressions/'+result['regression_id']+'/replay')
    replay = wait(client, response.json()['run_id'])
    assert replay['result']['regression_passed'] is True
    assert replay['result']['replay_of'] == result['regression_id']
    assert client.get('/regressions').json()['total'] == 1


@pytest.mark.parametrize('amount,decision', [(0,'blocked'), (1,'allowed'), (100_000,'allowed'), (100_001,'blocked')])
def test_policy_boundaries(client, amount, decision):
    assert run(client, {'scenario_id':'allowed_refund', 'amount_minor':amount})['result']['decision'] == decision


@pytest.mark.parametrize('payload', [
    {}, {'scenario_id':'unknown'}, {'scenario_id':'allowed_refund','amount_minor':-1},
    {'scenario_id':'allowed_refund','amount_minor':1.5}, {'scenario_id':'allowed_refund','amount_minor':True},
    {'scenario_id':'allowed_refund','amount_minor':'500'}, {'scenario_id':'allowed_refund','amount_minor':10_000_001},
    {'scenario_id':'allowed_refund','ticket':''}, {'scenario_id':'allowed_refund','ticket':'x'*4001},
    {'scenario_id':'allowed_refund','admin':True}])
def test_validation(client, payload):
    r = client.post('/runs', json=payload)
    assert r.status_code == 422
    assert r.json()['error']['code'] == 'VALIDATION_ERROR'
    assert client.get('/runs').json()['total'] == 0


def test_malformed_json(client):
    r = client.post('/runs', content='{oops', headers={'Content-Type':'application/json'})
    assert r.status_code == 422


def test_body_limit(client):
    r = client.post('/runs', content='x'*70_000)
    assert r.status_code == 413
    assert client.get('/runs').json()['total'] == 0


@pytest.mark.parametrize('path', ['/runs/not-found', '/runs/not-found/evidence', '/regressions/not-found'])
def test_missing(client, path):
    assert client.get(path).status_code == 404


def test_missing_replay(client):
    assert client.post('/regressions/not-found/replay').status_code == 404


def test_idempotency(client):
    headers = {'Idempotency-Key':'same-request'}
    first = client.post('/runs', json={'scenario_id':'allowed_refund'}, headers=headers)
    again = client.post('/runs', json={'scenario_id':'allowed_refund'}, headers=headers)
    assert first.json()['run_id'] == again.json()['run_id']
    conflict = client.post('/runs', json={'scenario_id':'injection_refund'}, headers=headers)
    assert conflict.status_code == 409
    assert client.get('/runs').json()['total'] == 1
    assert client.post('/runs', json={'scenario_id':'allowed_refund'}, headers={'Idempotency-Key':'x'*129}).status_code == 422


def test_database_persistence(tmp_path):
    path = str(tmp_path/'persistent.db')
    with TestClient(create_app(path)) as c:
        result = run(c, {'scenario_id':'excessive_refund'})
    with TestClient(create_app(path)) as c:
        assert c.get('/runs/'+result['run_id']).json() == result
        assert c.get('/regressions').json()['total'] == 1


def test_restart_recovery(tmp_path):
    path = str(tmp_path/'restart.db')
    store = Store(path)
    queued, _ = store.create(RunInput(scenario_id='allowed_refund'))
    running, _ = store.create(RunInput(scenario_id='excessive_refund'))
    store.start(running)
    with TestClient(create_app(path)) as c:
        for rid in (queued, running):
            assert c.get('/runs/'+rid).json()['error']['code'] == 'RUN_INTERRUPTED'


class BrokenRunner:
    def execute(self, run_id, inputs, emit):
        raise RuntimeError('private details must not appear in API output')


def test_failed_runner(tmp_path):
    with TestClient(create_app(str(tmp_path/'bad.db'), runner=BrokenRunner())) as c:
        data = run(c, {'scenario_id':'allowed_refund'})
        assert data['status'] == 'failed'
        assert data['result'] is None
        assert data['error']['code'] == 'RUN_FAILED'
        assert 'private details' not in str(data)


class MutatingBlockedRunner(MockRunner):
    def execute(self, run_id, inputs, emit):
        r = super().execute(run_id, inputs, emit)
        r.state_after['refunded_minor'] = 10
        r.state_mutated = True
        return r


def test_runner_invariant(tmp_path):
    with TestClient(create_app(str(tmp_path/'bad.db'), runner=MutatingBlockedRunner())) as c:
        data = run(c, {'scenario_id':'excessive_refund'})
        assert data['status'] == 'failed'
        assert c.get('/regressions').json()['total'] == 0


def test_regression_catches_changed_behavior(tmp_path):
    path = str(tmp_path/'changed.db')
    with TestClient(create_app(path)) as c:
        fixture = run(c, {'scenario_id':'injection_refund'})['result']['regression_id']
    class ChangedRunner(MockRunner):
        def execute(self, run_id, inputs, emit):
            return super().execute(run_id, RunInput(scenario_id='allowed_refund'), emit)
    with TestClient(create_app(path, runner=ChangedRunner())) as c:
        response = c.post('/regressions/'+fixture+'/replay')
        data = wait(c, response.json()['run_id'])
        assert data['status'] == 'completed'
        assert data['result']['regression_passed'] is False


def test_key_auth_and_cors(tmp_path):
    with TestClient(create_app(str(tmp_path/'auth.db'), api_key='test-key')) as c:
        assert c.get('/health').status_code == 200
        assert c.get('/scenarios').status_code == 401
        assert c.get('/scenarios', headers={'X-API-Key':'test-key'}).status_code == 200
        r = c.options('/runs', headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'X-API-Key'})
        assert r.status_code == 200
        assert r.headers['access-control-allow-origin'] == 'http://localhost:5173'
        r = c.options('/runs', headers={'Origin':'https://evil.example','Access-Control-Request-Method':'POST'})
        assert 'access-control-allow-origin' not in r.headers


def test_concurrent_runs_isolated(client):
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(lambda _: run(client, {'scenario_id':'allowed_refund'}), range(12)))
    assert len({r['run_id'] for r in results}) == 12
    assert all(r['result']['state_after']['refunded_minor'] == 50_000 for r in results)
    assert client.get('/runs?limit=5').json()['total'] == 12
    assert len(client.get('/runs?limit=5').json()['items']) == 5


def test_concurrent_idempotency(tmp_path):
    store = Store(str(tmp_path/'parallel.db'))
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: store.create(RunInput(scenario_id='allowed_refund'), 'one'), range(20)))
    assert len({r[0] for r in results}) == 1
    assert sum(r[1] for r in results) == 1


def test_pending_capacity(tmp_path):
    store = Store(str(tmp_path/'capacity.db'))
    for _ in range(100):
        store.create(RunInput(scenario_id='allowed_refund'))
    from app.store import CapacityExceeded
    with pytest.raises(CapacityExceeded):
        store.create(RunInput(scenario_id='allowed_refund'))


@pytest.mark.parametrize('query', ['limit=0','limit=101','offset=-1'])
def test_pagination_limits(client, query):
    assert client.get('/runs?'+query).status_code == 422


def test_queued_running_lifecycle(tmp_path):
    started, release = Event(), Event()
    class SlowRunner(MockRunner):
        def execute(self, run_id, inputs, emit):
            started.set()
            assert release.wait(3)
            return super().execute(run_id, inputs, emit)
    with TestClient(create_app(str(tmp_path/'slow.db'), runner=SlowRunner())) as c:
        r = c.post('/runs', json={'scenario_id':'allowed_refund'}).json()
        assert started.wait(1)
        assert c.get('/runs/'+r['run_id']).json()['status'] == 'running'
        release.set()
        assert wait(c, r['run_id'])['status'] == 'completed'


def test_empty_idempotency_key_rejected(client):
    r = client.post('/runs', json={'scenario_id':'allowed_refund'}, headers={'Idempotency-Key':''})
    assert r.status_code == 422
    assert client.get('/runs').json()['total'] == 0


def test_whitespace_ticket_rejected(client):
    r = client.post('/runs', json={'scenario_id':'allowed_refund', 'ticket':'   \t\n'})
    assert r.status_code == 422
    assert client.get('/runs').json()['total'] == 0


def blocked_result(store=None, run_id='test'):
    emit = (lambda *args: store.emit(run_id, *args)) if store else (lambda *args: None)
    return MockRunner().execute(run_id, RunInput(scenario_id='injection_refund'), emit)


@pytest.mark.parametrize('status', ['missing', 'queued', 'failed', 'completed'])
def test_completion_requires_running_row(tmp_path, status):
    store = Store(str(tmp_path / 'store.db'))
    run_id = 'missing'
    if status != 'missing':
        run_id, _ = store.create(RunInput(scenario_id='injection_refund'))
        if status == 'failed':
            store.fail(run_id)
        elif status == 'completed':
            store.start(run_id)
            store.complete(run_id, blocked_result(store, run_id))
    before = store.get(run_id)
    fixtures = store.regressions(100, 0)
    with pytest.raises(ValueError, match='running run'):
        store.complete(run_id, blocked_result())
    assert store.get(run_id) == before
    assert store.regressions(100, 0) == fixtures


def test_missing_replay_fixture_rolls_back(tmp_path):
    store = Store(str(tmp_path / 'store.db'))
    run_id, _ = store.create(RunInput(scenario_id='injection_refund'), replay_of='missing')
    store.start(run_id)
    before = store.get(run_id)
    with pytest.raises(ValueError, match='fixture'):
        store.complete(run_id, blocked_result())
    assert store.get(run_id) == before
    assert store.regressions(100, 0)['total'] == 0


@pytest.mark.parametrize('drift', ['action', 'amount', 'baseline', 'none'])
def test_replay_checks_original_contract(tmp_path, drift):
    path = str(tmp_path / 'replay-contract.db')
    with TestClient(create_app(path)) as c:
        fixture = run(c, {'scenario_id': 'injection_refund'})['result']['regression_id']
    class DriftRunner(MockRunner):
        def execute(self, run_id, inputs, emit):
            events = []
            result = super().execute(run_id, inputs, lambda *args: events.append(args))
            if drift == 'action':
                result.action = 'change_account_email'
                result.amount_minor = None
            elif drift == 'amount':
                result.amount_minor = 1
            elif drift == 'baseline':
                result.state_before['customer_id'] = 'OTHER'
                result.state_after['customer_id'] = 'OTHER'
            for kind, message, data in events:
                if kind == 'action_proposed':
                    data['action'] = result.action
                    data['amount_minor'] = result.amount_minor
                if kind == 'tool_blocked':
                    data['tool'] = result.action
                if kind == 'state_verified':
                    data.update(state_before=result.state_before, state_after=result.state_after)
                emit(kind, message, data)
            result.regression_id = 'forged'
            result.replay_of = 'forged'
            result.regression_passed = True
            return result
    with TestClient(create_app(path, runner=DriftRunner())) as c:
        response = c.post('/regressions/' + fixture + '/replay')
        data = wait(c, response.json()['run_id'])
        assert data['status'] == 'completed'
        assert data['result']['regression_passed'] is (drift == 'none')
        assert data['result']['replay_of'] == fixture
        assert data['result']['regression_id'] is None


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'both_outcomes', 'wrong_outcome',
                                    'action', 'amount', 'snapshot', 'order'])
def test_evidence_contract_fails_closed(tmp_path, fault):
    class IncoherentRunner(MockRunner):
        def execute(self, run_id, inputs, emit):
            events = []
            result = super().execute(run_id, inputs, lambda *args: events.append(args))
            if fault == 'missing':
                events = [e for e in events if e[0] != 'action_proposed']
            elif fault == 'duplicate':
                events += [next(e for e in events if e[0] == 'policy_decision')]
            elif fault == 'both_outcomes':
                events += [('tool_executed', 'Contradiction', {'tool': result.action})]
            elif fault == 'wrong_outcome':
                events = [('tool_executed' if k == 'tool_blocked' else k, m, d) for k,m,d in events]
            elif fault == 'order':
                events.reverse()
            else:
                kind = 'state_verified' if fault == 'snapshot' else 'action_proposed'
                data = next(d for k,m,d in events if k == kind)
                if fault == 'snapshot':
                    data['state_after'] = {'wrong': True}
                else:
                    data['action' if fault == 'action' else 'amount_minor'] = 'wrong'
            for event in events:
                emit(*event)
            return result
    with TestClient(create_app(str(tmp_path/'evidence.db'), runner=IncoherentRunner())) as c:
        data = run(c, {'scenario_id':'injection_refund'})
        assert data['status'] == 'failed'
        assert data['result'] is None
        assert data['error']['code'] == 'RUN_FAILED'
        assert c.get('/regressions').json()['total'] == 0


@pytest.mark.parametrize('fault', ['kind', 'message', 'not_dict', 'nan', 'key', 'large', 'count'])
def test_evidence_envelope_limits(tmp_path, fault):
    store = Store(str(tmp_path/'limits.db'))
    run_id, _ = store.create(RunInput(scenario_id='allowed_refund'))
    store.start(run_id)
    args = ['custom', 'Synthetic evidence', {}]
    if fault == 'kind': args[0] = ''
    elif fault == 'message': args[1] = 'x' * 1001
    elif fault == 'not_dict': args[2] = []
    elif fault == 'nan': args[2] = {'value': float('nan')}
    elif fault == 'key': args[2] = {1: 'coerced'}
    elif fault == 'large': args[2] = {'value': 'x' * 32768}
    elif fault == 'count':
        for _ in range(128): store.emit(run_id, *args)
    count = len(store.get(run_id)['evidence'])
    with pytest.raises(ValueError): store.emit(run_id, *args)
    assert len(store.get(run_id)['evidence']) == count


@pytest.mark.parametrize('status', ['missing', 'queued', 'failed', 'completed'])
def test_late_evidence_rejected(tmp_path, status):
    store = Store(str(tmp_path/'late.db'))
    run_id, _ = store.create(RunInput(scenario_id='injection_refund'))
    if status == 'failed': store.fail(run_id)
    elif status == 'completed':
        store.start(run_id)
        store.complete(run_id, blocked_result(store, run_id))
    if status == 'missing': run_id = 'missing'
    with pytest.raises(ValueError, match='running run'):
        store.emit(run_id, 'custom', 'Late event', {})


def test_bool_amount_cannot_equal_integer_evidence(tmp_path):
    class BooleanEvidence(MockRunner):
        def execute(self, run_id, inputs, emit):
            def altered(kind, message, data):
                if kind == 'action_proposed': data['amount_minor'] = True
                emit(kind, message, data)
            return super().execute(run_id, inputs, altered)
    with TestClient(create_app(str(tmp_path/'bool.db'), runner=BooleanEvidence())) as c:
        assert run(c, {'scenario_id':'allowed_refund','amount_minor':1})['status'] == 'failed'


def test_partial_failure_preserves_trace_and_terminal_marker(tmp_path):
    class PartialRunner:
        def execute(self, run_id, inputs, emit):
            emit('policy_decision', 'Partial mock decision', {'provider':'mock','decision':'allowed'})
            raise RuntimeError('SECRET exception text')
    with TestClient(create_app(str(tmp_path/'partial.db'), runner=PartialRunner())) as c:
        data = run(c, {'scenario_id':'allowed_refund'})
        assert data['status'] == 'failed' and data['result'] is None
        assert [e['kind'] for e in data['evidence']] == ['policy_decision','run_failed']
        assert data['evidence'][-1]['data'] == {'code':'RUN_FAILED'}
        assert 'SECRET' not in str(data)


def test_failure_and_recovery_markers_are_idempotent(tmp_path):
    store = Store(str(tmp_path/'markers.db'))
    first, _ = store.create(RunInput(scenario_id='allowed_refund'))
    assert store.fail(first)
    assert not store.fail(first)
    second, _ = store.create(RunInput(scenario_id='allowed_refund'))
    store.start(second)
    store.emit(second, 'custom', 'Partial evidence', {})
    store.recover()
    snapshot = store.get(second)
    store.recover()
    assert store.get(second) == snapshot
    assert snapshot['evidence'][-1]['data']['code'] == 'RUN_INTERRUPTED'
    assert len(store.get(first)['evidence']) == 1


def test_lifespan_always_shuts_executor_down(tmp_path, monkeypatch):
    import asyncio
    import importlib
    main = importlib.import_module('app.main')
    calls = []
    class Executor:
        def __init__(self, **kwargs): pass
        def shutdown(self, **kwargs): calls.append(kwargs)
    monkeypatch.setattr(main, 'ThreadPoolExecutor', Executor)
    app = main.create_app(str(tmp_path/'shutdown.db'))
    async def exercise():
        with pytest.raises(RuntimeError, match='lifespan error'):
            async with app.router.lifespan_context(app):
                raise RuntimeError('lifespan error')
    asyncio.run(exercise())
    assert calls == [{'wait':True}]


def test_worker_start_failure_is_terminal(tmp_path, monkeypatch):
    app = create_app(str(tmp_path/'start-fail.db'))
    with TestClient(app) as c:
        def bad_start(run_id): raise RuntimeError('private start failure')
        monkeypatch.setattr(app.state.store, 'start', bad_start)
        data = run(c, {'scenario_id':'allowed_refund'})
        assert data['status'] == 'failed'
        assert data['evidence'][-1]['kind'] == 'run_failed'
        assert 'private start' not in str(data)


@pytest.mark.parametrize('case,status', [('auth',401), ('body',413), ('duplicate',422)])
def test_cors_applies_to_guard_errors(tmp_path, case, status):
    with TestClient(create_app(str(tmp_path/'cors.db'), api_key='test-key')) as c:
        headers = [('Origin','http://localhost:5173')]
        if case != 'auth': headers.append(('X-API-Key','test-key'))
        if case == 'duplicate': headers += [('Idempotency-Key','a'),('Idempotency-Key','b')]
        response = c.post('/runs', content='x'*70000 if case == 'body' else '{}', headers=headers)
        assert response.status_code == status
        assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
        assert c.get('/runs',headers={'X-API-Key':'test-key'}).json()['total'] == 0


@pytest.mark.parametrize('values', [('a','b'),('same','same')])
def test_duplicate_idempotency_rejected(client, values):
    response = client.post('/runs', json={'scenario_id':'allowed_refund'},
                           headers=[('Idempotency-Key', value) for value in values])
    assert response.status_code == 422
    assert client.get('/runs').json()['total'] == 0


def test_duplicate_api_keys_fail_closed(tmp_path):
    with TestClient(create_app(str(tmp_path/'duplicate-key.db'),api_key='correct')) as c:
        response = c.get('/scenarios',headers=[('X-API-Key','correct'),('X-API-Key','wrong')])
        assert response.status_code == 401


def test_chunked_body_preserved_and_limited(client):
    def chunks():
        yield b'{"scenario_id":'
        yield b'"allowed_refund"}'
    response = client.post('/runs',content=chunks(),headers={'Content-Type':'application/json'})
    assert response.status_code == 202
    def oversized():
        for _ in range(70): yield b'x'*1024
    assert client.post('/runs', content=oversized()).status_code == 413


@pytest.mark.parametrize('change', [{'amount_minor':True}, {'amount_minor':-1},
    {'amount_minor':10_000_001}, {'amount_minor':None}, {'reason':''}, {'reason':'   '},
    {'reason':'x'*1001}, {'action':'change_account_email','amount_minor':1}, {'unknown':1}])
def test_result_model_rejects_invalid_contract(change):
    from app.models import RunResult
    data = blocked_result().model_dump()
    data.update(change)
    with pytest.raises(ValueError): RunResult.model_validate(data)


def test_mutated_result_is_revalidated_before_persistence(tmp_path):
    class MutatedResult(MockRunner):
        def execute(self, run_id, inputs, emit):
            result = super().execute(run_id, inputs, emit)
            result.reason = ' ' * 10
            return result
    with TestClient(create_app(str(tmp_path/'mutated.db'), runner=MutatedResult())) as c:
        data = run(c, {'scenario_id':'injection_refund'})
        assert data['status'] == 'failed'
        assert data['result'] is None
        assert c.get('/regressions').json()['total'] == 0


def test_runner_cannot_forge_terminal_event(tmp_path):
    class ForgedFailure:
        def execute(self, run_id, inputs, emit):
            emit('run_failed','Fake backend failure',{'code':'FORGED'})
    with TestClient(create_app(str(tmp_path/'forged.db'), runner=ForgedFailure())) as c:
        data = run(c, {'scenario_id':'allowed_refund'})
        assert data['status'] == 'failed'
        assert len(data['evidence']) == 1
        assert data['evidence'][0]['data'] == {'code':'RUN_FAILED'}
