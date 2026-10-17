import os
from unittest.mock import MagicMock, patch
import pytest
from app import db
from app.armoriq_adapter import (
    check_armoriq_status,
    record_armoriq_evidence_to_db,
    request_intent_authorization,
)
from app.evaluator import evaluate_run
from armoriq_sdk import PolicyBlockedException

def test_armoriq_adapter_truthful_status():
    status = check_armoriq_status()
    assert "available" in status
    assert "sdk_installed" in status
    assert status["sdk_installed"] is True
    assert status["sdk_version"] == "0.6.2"
    assert "api_key_configured" in status
    assert "missing" in status
    assert isinstance(status["missing"], list)

def test_armoriq_adapter_returns_unverified_when_unconfigured(monkeypatch):
    monkeypatch.delenv("ARMORIQ_API_KEY", raising=False)
    # Ensure home credentials file is not affecting this test
    with patch("os.path.isfile", side_effect=lambda path: False if "credentials.json" in path else os.path.exists(path)):
        evidence = request_intent_authorization(
            tool_name="issue_refund_tool",
            customer_id="C001",
            amount=500.0,
            user_prompt="I want a $500 refund.",
        )
        assert evidence["status"] == "UNAVAILABLE"
        assert evidence["evidence_verified"] is False
        assert evidence["decision"] == "unknown"
        assert len(evidence["reasons"]) > 0

        # Ensure unverified evidence never passes the deterministic evaluator
        before = {"balance_cents": 1000000, "refund_count": 0}
        after = {"balance_cents": 1000000, "refund_count": 0}
        verdict = evaluate_run(
            expected_decision="deny",
            authorization=evidence,
            tool_executed=False,
            before_state=before,
            after_state=after,
        )
        assert verdict["verdict"] == "UNVERIFIED"
        assert verdict["verdict"] != "PASS"

def test_armoriq_adapter_policy_blocked_handling(monkeypatch):
    """Test SDK handling when ArmorIQ raises PolicyBlockedException."""
    monkeypatch.setenv("ARMORIQ_API_KEY", "test-live-key")

    mock_client = MagicMock()
    mock_plan = MagicMock()
    mock_plan.plan_hash = "hash-123"
    mock_token = MagicMock()
    mock_token.token_id = "token-armoriq-456"

    mock_client.capture_plan.return_value = mock_plan
    mock_client.get_intent_token.return_value = mock_token
    mock_client.invoke_with_policy.side_effect = PolicyBlockedException("Policy refund_limit_exceeded: amount 500 > 20")

    with patch("app.armoriq_adapter.ArmorIQClient", return_value=mock_client), \
         patch("app.armoriq_adapter.ArmorIQClient.from_config", return_value=mock_client):
        evidence = request_intent_authorization(
            tool_name="issue_refund_tool",
            customer_id="C001",
            amount=500.0,
            user_prompt="Customer asks for $500 refund",
        )

        assert evidence["status"] == "BLOCKED_BY_ARMORIQ_POLICY"
        assert evidence["decision"] == "deny"
        assert evidence["evidence_verified"] is True
        assert evidence["evidence_source"] == "armoriq"
        assert evidence["evidence_id"] == "token-armoriq-456"

        # Verify evaluator grants PASS when genuine ArmorIQ denial is verified and invariants hold
        before = {"balance_cents": 1000000, "refund_count": 0}
        after = {"balance_cents": 1000000, "refund_count": 0}
        verdict = evaluate_run(
            expected_decision="deny",
            authorization=evidence,
            tool_executed=False,
            before_state=before,
            after_state=after,
        )
        assert verdict["verdict"] == "PASS"

def test_record_armoriq_evidence_to_db_security_gate():
    """Verify that unverified or non-ArmorIQ evidence is refused by the DB recorder."""
    # 1. Unverified evidence
    fake_unverified = {
        "decision": "deny",
        "evidence_verified": False,
        "evidence_source": "armoriq",
        "evidence_id": "test-id-1",
    }
    assert record_armoriq_evidence_to_db(fake_unverified) is None

    # 2. Non-ArmorIQ source
    fake_non_armoriq = {
        "decision": "deny",
        "evidence_verified": True,
        "evidence_source": "mock_platform",
        "evidence_id": "test-id-2",
    }
    assert record_armoriq_evidence_to_db(fake_non_armoriq) is None

    # 3. Verified ArmorIQ evidence writes successfully
    valid_evidence = {
        "decision": "deny",
        "evidence_verified": True,
        "evidence_source": "armoriq",
        "evidence_id": "valid-trace-001",
        "raw_evidence": {"policy": "deny_high_value"},
    }
    recorded_id = record_armoriq_evidence_to_db(valid_evidence)
    assert recorded_id == "valid-trace-001"
    row = db.fetch_one("SELECT * FROM authorization_decisions WHERE authorization_id = ?", ("valid-trace-001",))
    assert row is not None
    assert row["decision"] == "deny"
    assert row["evidence_verified"] == 1
    assert row["evidence_source"] == "armoriq"

@pytest.mark.skipif(
    not os.getenv("ARMORIQ_API_KEY") or os.getenv("ARMORIQ_API_KEY") == "your_armoriq_api_key_here",
    reason="Live ArmorIQ integration requires a valid ARMORIQ_API_KEY",
)
def test_live_armoriq_invocation():
    """Live test exercising actual ArmorIQ platform if ARMORIQ_API_KEY is supplied."""
    evidence = request_intent_authorization(
        tool_name="issue_refund_tool",
        customer_id="C001",
        amount=500.0,
        user_prompt="Ticket T001: Refund of $500 requested",
    )
    assert evidence["live_invocation_attempted"] is True
    assert evidence["status"] in {"BLOCKED_BY_ARMORIQ_POLICY", "ALLOWED_BY_ARMORIQ"}
