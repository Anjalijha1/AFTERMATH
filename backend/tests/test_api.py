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
