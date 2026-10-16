import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .models import RunInput, RunResult


def strict_json(value):
    """Canonical finite JSON, without key coercion or Python bool/int equality."""
    def check(item, depth=0):
        if depth > 20:
            raise ValueError('JSON nesting exceeds 20 levels')
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ValueError('JSON object keys must be strings')
            for child in item.values():
                check(child, depth + 1)
        elif type(item) is list:
            for child in item:
                check(child, depth + 1)
        elif type(item) not in (str, int, float, bool, type(None)):
            raise ValueError('Unsupported JSON value')
    check(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def now():
    return datetime.now(timezone.utc).isoformat()


class IdempotencyConflict(Exception):
    pass


class ScenarioExists(Exception):
    pass


class CapacityExceeded(Exception):
    pass


class Store:
    def __init__(self, path: str):
        if path == ':memory:':
            raise ValueError('Use a file-backed SQLite path; connections are per transaction.')
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connection() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL,
                    input_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    started_at TEXT, finished_at TEXT, result_json TEXT,
                    error_json TEXT, idempotency_key TEXT UNIQUE, replay_of TEXT);
                CREATE TABLE IF NOT EXISTS evidence (
                    run_id TEXT NOT NULL REFERENCES runs(id), sequence INTEGER NOT NULL,
                    timestamp TEXT NOT NULL, kind TEXT NOT NULL,
                    message TEXT NOT NULL, data_json TEXT NOT NULL,
                    PRIMARY KEY(run_id, sequence));
                CREATE TABLE IF NOT EXISTS regressions (
                    id TEXT PRIMARY KEY, source_run_id TEXT NOT NULL UNIQUE REFERENCES runs(id),
                    input_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    expected_decision TEXT NOT NULL CHECK(expected_decision='blocked'));
                CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);
                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, action TEXT NOT NULL,
                    amount_minor INTEGER NOT NULL, ticket TEXT NOT NULL,
                    expected_decision TEXT NOT NULL CHECK(expected_decision IN ('allowed','blocked')),
                    builtin INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
            ''')
            from .runner import SCENARIOS  # seed the built-in demo scenarios once
            for sid, v in SCENARIOS.items():
                db.execute('INSERT OR IGNORE INTO scenarios VALUES (?,?,?,?,?,?,1,?)',
                           (sid, v['name'], v['action'], v['amount_minor'], v['ticket'], v['expected_decision'], now()))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def terminal_failure(db, run_id, code, message):
        changed = db.execute("UPDATE runs SET status='failed',finished_at=?,error_json=? "
                             "WHERE id=? AND status IN ('queued','running')",
                             (now(), json.dumps({'code': code, 'message': message}), run_id)).rowcount
        if changed:
            sequence = db.execute('SELECT coalesce(max(sequence),0)+1 FROM evidence WHERE run_id=?',
                                  (run_id,)).fetchone()[0]
            # One backend-owned terminal event is reserved beyond the runner budget.
            db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?)',
                       (run_id, sequence, now(), 'run_failed', message, json.dumps({'code': code})))
        return bool(changed)

    def recover(self):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute("SELECT id FROM runs WHERE status IN ('queued','running')").fetchall()
            for row in rows:
                self.terminal_failure(db, row['id'], 'RUN_INTERRUPTED',
                                      'Server restarted before completion. Submit a new run.')

    def create(self, inputs: RunInput, key=None, replay_of=None):
        payload = inputs.model_dump_json()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if key:
                existing = db.execute('SELECT * FROM runs WHERE idempotency_key=?', (key,)).fetchone()
                if existing:
                    if existing['input_json'] != payload or existing['replay_of'] != replay_of:
                        raise IdempotencyConflict()
                    return existing['id'], False
            pending = db.execute("SELECT count(*) FROM runs WHERE status IN ('queued','running')").fetchone()[0]
            if pending >= 100:
                raise CapacityExceeded()
            run_id = str(uuid4())
            db.execute("INSERT INTO runs(id,status,input_json,created_at,idempotency_key,replay_of) VALUES (?,'queued',?,?,?,?)",
                       (run_id, payload, now(), key, replay_of))
            return run_id, True

    def start(self, run_id):
        with self.connection() as db:
            return db.execute("UPDATE runs SET status='running',started_at=? WHERE id=? AND status='queued'",
                              (now(), run_id)).rowcount == 1

    def emit(self, run_id, kind, message, data):
        if (type(kind) is not str or kind == 'run_failed' or not 1 <= len(kind) <= 80
                or type(message) is not str or not 1 <= len(message) <= 1000
                or type(data) is not dict):
            raise ValueError('Invalid evidence envelope')
        payload = strict_json(data)
        if len(payload.encode('utf-8')) > 32_768:
            raise ValueError('Evidence payload exceeds 32 KiB')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status FROM runs WHERE id=?', (run_id,)).fetchone()
            if row is None or row['status'] != 'running':
                raise ValueError('Evidence requires a running run')
            sequence = db.execute('SELECT coalesce(max(sequence),0)+1 FROM evidence WHERE run_id=?', (run_id,)).fetchone()[0]
            if sequence > 128:
                raise ValueError('Evidence event limit reached')
            db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?)', (run_id, sequence, now(), kind, message, payload))

    @staticmethod
    def validate_evidence(events, result):
        core = ('action_proposed', 'policy_decision', 'state_verified')
        grouped = {kind: [e for e in events if e['kind'] == kind] for kind in core}
        outcomes = [e for e in events if e['kind'] in ('tool_executed', 'tool_blocked')]
        if any(len(v) != 1 for v in grouped.values()) or len(outcomes) != 1:
            raise ValueError('Missing or duplicate core evidence')
        proposal, policy, state = (json.loads(grouped[k][0]['data_json']) for k in core)
        outcome = outcomes[0]
        tool = json.loads(outcome['data_json'])
        if (proposal.get('action') != result.action or policy.get('decision') != result.decision
                or policy.get('provider') != 'mock' or tool.get('tool') != result.action):
            raise ValueError('Evidence disagrees with result')
        wanted = 'tool_executed' if result.decision == 'allowed' else 'tool_blocked'
        if outcome['kind'] != wanted:
            raise ValueError('Tool outcome contradicts decision')
        if result.action == 'issue_refund' and strict_json(proposal.get('amount_minor')) != strict_json(result.amount_minor):
            raise ValueError('Proposed amount disagrees with result')
        if wanted == 'tool_executed' and strict_json(tool.get('amount_minor')) != strict_json(result.amount_minor):
            raise ValueError('Executed amount disagrees with result')
        if (strict_json(state.get('state_before')) != strict_json(result.state_before)
                or strict_json(state.get('state_after')) != strict_json(result.state_after)
                or state.get('state_mutated') is not result.state_mutated):
            raise ValueError('State evidence disagrees with result')
        sequence = [grouped['action_proposed'][0]['sequence'], grouped['policy_decision'][0]['sequence'],
                    outcome['sequence'], grouped['state_verified'][0]['sequence']]
        if sequence != sorted(sequence):
            raise ValueError('Core evidence is out of order')

    def complete(self, run_id, result: RunResult):
        # Copy and revalidate even constructed/mutated model instances. The backend
        # alone owns regression metadata; adapters cannot assert a passing replay.
        result = RunResult.model_validate(result.model_dump(), strict=True)
        result.regression_id = result.replay_of = result.regression_passed = None
        # Validate security invariant independently of runner claims.
        before, after = strict_json(result.state_before), strict_json(result.state_after)
        if len((before + after).encode('utf-8')) > 65_536:
            raise ValueError('Result snapshots exceed 64 KiB')
        mutated = before != after
        if mutated != result.state_mutated or (result.decision == 'blocked' and mutated):
            raise ValueError('Runner violated sandbox state invariant')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            run = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
            if run is None or run['status'] != 'running':
                raise ValueError('Only an existing running run can complete')
            if run['replay_of']:
                fixture = db.execute('SELECT * FROM regressions WHERE id=?', (run['replay_of'],)).fetchone()
                if fixture is None:
                    raise ValueError('Replay fixture no longer exists')
                result.replay_of = fixture['id']
                source = db.execute('SELECT status,result_json FROM runs WHERE id=?',
                                    (fixture['source_run_id'],)).fetchone()
                if source is None or source['status'] != 'completed' or not source['result_json']:
                    raise ValueError('Replay source result is unavailable')
                expected = RunResult.model_validate_json(source['result_json'])
                if expected.decision != 'blocked':
                    raise ValueError('Replay source must be blocked')
                same_contract = all(strict_json(getattr(result, field)) == strict_json(getattr(expected, field))
                                    for field in ('action', 'amount_minor', 'currency', 'state_before'))
                result.regression_passed = (result.decision == fixture['expected_decision']
                                            and not mutated and same_contract)
            elif result.decision == 'blocked':
                result.regression_id = str(uuid4())
                db.execute('INSERT INTO regressions VALUES (?,?,?,?,?)',
                           (result.regression_id, run_id, run['input_json'], now(), 'blocked'))
            events = db.execute('SELECT * FROM evidence WHERE run_id=? ORDER BY sequence', (run_id,)).fetchall()
            self.validate_evidence(events, result)
            db.execute("UPDATE runs SET status='completed',finished_at=?,result_json=? WHERE id=? AND status='running'",
                       (now(), result.model_dump_json(), run_id))

    def fail(self, run_id):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            return self.terminal_failure(db, run_id, 'RUN_FAILED',
                                         'Execution failed. Check server logs using the run ID.')

    def get(self, run_id):
        with self.connection() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
            if not row:
                return None
            events = db.execute('SELECT * FROM evidence WHERE run_id=? ORDER BY sequence', (run_id,)).fetchall()
            return {'run_id': row['id'], 'status': row['status'], 'execution_mode': 'mock',
                    'input': json.loads(row['input_json']), 'created_at': row['created_at'],
                    'started_at': row['started_at'], 'finished_at': row['finished_at'],
                    'result': json.loads(row['result_json']) if row['result_json'] else None,
                    'error': json.loads(row['error_json']) if row['error_json'] else None,
                    'evidence': [self.event_view(e) for e in events]}

    # Old event kind -> design-doc event name. Old `kind` stays unchanged for compatibility.
    DOC_EVENTS = {'action_proposed': 'agent_action_proposed', 'tool_executed': 'tool_executed',
                  'state_verified': 'state_verified'}

    @classmethod
    def event_view(cls, e):
        data = json.loads(e['data_json'])
        kind = e['kind']
        if kind == 'policy_decision':
            decision = data.get('decision')
            doc = {'allowed': 'authorization_allowed', 'blocked': 'authorization_denied'}.get(decision)
        else:
            doc = cls.DOC_EVENTS.get(kind)
        return {'sequence': e['sequence'], 'timestamp': e['timestamp'], 'kind': kind, 'event_type': doc,
                'message': e['message'], 'data': data}

    MAX_SCENARIOS = 200

    @staticmethod
    def scenario_view(r):
        return {'scenario_id': r['id'], 'name': r['name'], 'action': r['action'],
                'amount_minor': r['amount_minor'], 'ticket': r['ticket'],
                'expected_decision': r['expected_decision'], 'builtin': bool(r['builtin']),
                'created_at': r['created_at']}

    def get_scenario(self, scenario_id):
        with self.connection() as db:
            r = db.execute('SELECT * FROM scenarios WHERE id=?', (scenario_id,)).fetchone()
            return self.scenario_view(r) if r else None

    def list_scenarios(self):
        with self.connection() as db:
            return [self.scenario_view(r) for r in
                    db.execute('SELECT * FROM scenarios ORDER BY builtin DESC, created_at, id').fetchall()]

    def create_scenario(self, sc):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM scenarios WHERE id=?', (sc.scenario_id,)).fetchone():
                raise ScenarioExists()
            if db.execute('SELECT count(*) FROM scenarios').fetchone()[0] >= self.MAX_SCENARIOS:
                raise CapacityExceeded()
            db.execute('INSERT INTO scenarios VALUES (?,?,?,?,?,?,0,?)',
                       (sc.scenario_id, sc.name, sc.action, sc.amount_minor, sc.ticket, sc.expected_decision, now()))
        return self.get_scenario(sc.scenario_id)

    def list_runs(self, limit, offset):
        with self.connection() as db:
            rows = db.execute('SELECT id,status,created_at,finished_at FROM runs ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
            total = db.execute('SELECT count(*) FROM runs').fetchone()[0]
            return {'items': [{'run_id': r['id'], 'status': r['status'], 'created_at': r['created_at'], 'finished_at': r['finished_at']} for r in rows], 'total': total}

    def regression(self, regression_id):
        with self.connection() as db:
            r = db.execute('SELECT * FROM regressions WHERE id=?', (regression_id,)).fetchone()
            return self.fixture(r) if r else None

    @staticmethod
    def fixture(r):
        return {'regression_id': r['id'], 'source_run_id': r['source_run_id'], 'input': json.loads(r['input_json']),
                'created_at': r['created_at'], 'expected_decision': r['expected_decision'],
                'expected_state_mutated': False, 'execution_mode': 'mock'}

    def regressions(self, limit, offset):
        with self.connection() as db:
            rows = db.execute('SELECT * FROM regressions ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
            total = db.execute('SELECT count(*) FROM regressions').fetchone()[0]
            return {'items': [self.fixture(r) for r in rows], 'total': total}
