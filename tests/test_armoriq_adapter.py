from app.armoriq_adapter import check_armoriq_status, request_intent_authorization
from app.evaluator import evaluate_run

def test_armoriq_adapter_truthful_status():
    status = check_armoriq_status()
    # Truthful inspection: either installed and configured or clearly reporting missing items
    assert "available" in status
    assert "sdk_installed" in status
    assert "api_key_configured" in status
    assert "missing" in status
    assert isinstance(status["missing"], list)

def test_armoriq_adapter_returns_unverified_when_unconfigured(monkeypatch):
    monkeypatch.delenv("ARMORIQ_API_KEY", raising=False)
    evidence = request_intent_authorization(
        tool_name="issue_refund",
        customer_id="C001",
        amount=500.0,
        user_prompt="I want a $500 refund.",
    )
    assert evidence["status"] == "UNAVAILABLE"
    assert evidence["evidence_verified"] is False
    assert evidence["decision"] == "unknown"
    assert len(evidence["reasons"]) > 0

    # Ensure this evidence can never lead to a PASS verdict in the evaluator
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
