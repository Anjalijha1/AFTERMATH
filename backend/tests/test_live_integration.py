"""Live-runner (agent + ArmorIQ) integration tests. All ArmorIQ calls are mocked;
these tests never touch the network or a real API key."""
import time

import pytest
from fastapi.testclient import TestClient

from app import armoriq
from app.live_runner import LiveRunner
from app.main import create_app


def wait(c, run_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        data = c.get('/runs/' + run_id).json()
        if data['status'] in ('completed', 'failed'):
            return data
        time.sleep(0.005)
    pytest.fail('Run failed to reach terminal state')


def run(c, payload):
    r = c.post('/runs', json=payload)
    assert r.status_code == 202, r.text
    assert r.json()['execution_mode'] == 'live'
    return wait(c, r.json()['run_id'])


@pytest.fixture
def live_client(tmp_path, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)  # force the fallback agent
    with TestClient(create_app(str(tmp_path / 'test.db'), runner=LiveRunner())) as c:
        yield c


def fake_allow(**kwargs):
    return {'decision': 'allow', 'evidence_verified': True, 'evidence_source': 'armoriq',
            'evidence_id': 'tok-test-allow', 'status': 'ALLOWED_BY_ARMORIQ',
            'reasons': ['ArmorIQ policy authorized the requested tool call'], 'raw_evidence': {}}


def fake_deny(**kwargs):
    return {'decision': 'deny', 'evidence_verified': True, 'evidence_source': 'armoriq',
            'evidence_id': 'tok-test-deny', 'status': 'BLOCKED_BY_ARMORIQ_POLICY',
            'reasons': ['ArmorIQ policy denied the action'], 'raw_evidence': {}}


def test_live_allowed_refund(live_client, monkeypatch):
    monkeypatch.setattr(armoriq, 'authorize', fake_allow)
    data = run(live_client, {'scenario_id': 'allowed_refund'})
    assert data['status'] == 'completed'
    result = data['result']
    assert result['execution_mode'] == 'live'
    assert result['decision'] == 'allowed'
    assert result['amount_minor'] == 50_000  # fallback parsed INR 500 from the ticket
    assert result['state_after']['refunded_minor'] == 50_000
    assert result['verdict'] == 'PASS'
    policy = [e for e in data['evidence'] if e['kind'] == 'policy_decision'][0]
    assert policy['data']['provider'] == 'armoriq'
    assert policy['data']['evidence_id'] == 'tok-test-allow'
    assert policy['data']['evidence_verified'] is True
    proposal = [e for e in data['evidence'] if e['kind'] == 'action_proposed'][0]
    assert proposal['data']['proposal_source'] == 'fallback'


def test_live_blocked_excessive_refund(live_client, monkeypatch):
    monkeypatch.setattr(armoriq, 'authorize', fake_deny)
    data = run(live_client, {'scenario_id': 'excessive_refund'})
    result = data['result']
    assert result['decision'] == 'blocked'
    assert result['state_before'] == result['state_after']
    assert result['verdict'] == 'PASS'
    assert result['regression_id']
    assert not any(e['kind'] == 'tool_executed' for e in data['evidence'])
    policy = [e for e in data['evidence'] if e['kind'] == 'policy_decision'][0]
    assert policy['data']['provider'] == 'armoriq'
    assert policy['data']['evidence_id'] == 'tok-test-deny'


def test_live_injection_proposes_worst_case_amount(live_client, monkeypatch):
    captured = {}

    def spy(**kwargs):
        captured.update(kwargs)
        return fake_deny(**kwargs)

    monkeypatch.setattr(armoriq, 'authorize', spy)
    data = run(live_client, {'scenario_id': 'injection_refund'})
    assert data['result']['decision'] == 'blocked'
    # Fallback picks the largest mentioned amount: the injected INR 50000, not INR 500.
    assert captured['amount_major'] == 50_000
    assert data['result']['amount_minor'] == 5_000_000


def test_live_email_change_goes_to_armoriq_with_its_own_tool(live_client, monkeypatch):
    seen = []

    def fake_deny(**kwargs):
        seen.append(kwargs['tool_name'])
        return {'decision': 'deny', 'evidence_verified': True, 'evidence_source': 'armoriq',
                'evidence_id': 'tok-test-deny', 'status': 'BLOCKED_BY_ARMORIQ_POLICY',
                'reasons': ['denied'], 'raw_evidence': {}}
    monkeypatch.setattr(armoriq, 'authorize', fake_deny)
    data = run(live_client, {'scenario_id': 'account_email_change'})
    result = data['result']
    assert result['decision'] == 'blocked'
    assert result['state_before'] == result['state_after']
    policy = [e for e in data['evidence'] if e['kind'] == 'policy_decision'][0]
    assert policy['data']['provider'] == 'armoriq'
    assert seen == [f'{armoriq.MCP_ID}.change_account_email_tool']


def test_live_refund_tier_tool_follows_amount(live_client, monkeypatch):
    seen = []

    def spy(**kwargs):
        seen.append(kwargs['tool_name'].split('.')[-1])
        return fake_allow(**kwargs)
    monkeypatch.setattr(armoriq, 'authorize', spy)
    run(live_client, {'scenario_id': 'allowed_refund'})
    run(live_client, {'scenario_id': 'excessive_refund'})
    assert 'issue_refund_tool' in seen and 'issue_large_refund_tool' in seen


def test_live_run_fails_honestly_when_armoriq_unavailable(live_client, monkeypatch):
    monkeypatch.delenv('ARMORIQ_API_KEY', raising=False)
    # No monkeypatched authorize: the real adapter sees no key (and maybe no SDK).
    data = run(live_client, {'scenario_id': 'allowed_refund'})
    assert data['status'] == 'failed'
    assert data['error']['code'] == 'RUN_FAILED'


def test_armoriq_authorize_unavailable_without_key(monkeypatch):
    monkeypatch.delenv('ARMORIQ_API_KEY', raising=False)
    out = armoriq.authorize(tool_name='issue_refund_tool', customer_id='CUST-001',
                            amount_major=5.0, limit_major=1000.0)
    assert out['decision'] == 'unknown'
    assert out['evidence_verified'] is False
    assert out['status'] == 'UNAVAILABLE'
    assert out['reasons']


def test_armoriq_evidence_requires_evidence_id():
    from app.store import Store
    events = [
        {'kind': 'action_proposed', 'sequence': 1, 'data_json': '{"action": "issue_refund", "amount_minor": 100}'},
        {'kind': 'policy_decision', 'sequence': 2,
         'data_json': '{"provider": "armoriq", "decision": "blocked", "evidence_verified": true}'},
        {'kind': 'tool_blocked', 'sequence': 3, 'data_json': '{"tool": "issue_refund"}'},
        {'kind': 'state_verified', 'sequence': 4,
         'data_json': '{"state_before": {"a": 1}, "state_after": {"a": 1}, "state_mutated": false}'},
    ]
    from app.models import RunResult
    result = RunResult(action='issue_refund', decision='blocked', reason='x', amount_minor=100,
                       state_before={'a': 1}, state_after={'a': 1}, state_mutated=False,
                       execution_mode='live')
    with pytest.raises(ValueError, match='evidence_id'):
        Store.validate_evidence(events, result)
    events[1]['data_json'] = '{"provider": "armoriq", "decision": "blocked", "evidence_verified": true, "evidence_id": "tok-1"}'
    Store.validate_evidence(events, result)  # passes with an evidence id


def test_health_reports_mock_by_default(tmp_path):
    with TestClient(create_app(str(tmp_path / 't.db'))) as c:
        body = c.get('/health').json()
        assert body['execution_mode'] == 'mock'
        assert body['real_armoriq'] is False
        assert body['armoriq']['available'] is False


def test_health_live_mode(tmp_path, monkeypatch):
    monkeypatch.setenv('AFTERMATH_RUNNER', 'live')
    with TestClient(create_app(str(tmp_path / 't.db'))) as c:
        body = c.get('/health').json()
        assert body['execution_mode'] == 'live'
        # No key configured in tests: honest unavailability, not a fake green.
        assert body['armoriq']['available'] is False
