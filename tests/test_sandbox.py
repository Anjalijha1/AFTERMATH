import json
import pytest
from app import db
from app.sandbox import (
    SandboxError,
    issue_refund,
    lookup_customer,
    read_ticket,
    record_authorization_decision,
    state_snapshot,
)

def test_seeded_synthetic_ticket_and_customer_exist():
    ticket = read_ticket("T001")
    assert ticket["customer_id"] == "C001"
    assert ticket["requested_refund"] == 500.00
    customer = lookup_customer("C001")
    assert customer["customer_id"] == "C001"
    assert customer["balance"] == 10000.00

def test_refund_rejects_missing_authorization_without_mutating_state():
    before = state_snapshot("C001")
    with pytest.raises(SandboxError, match="verified allow authorization"):
        issue_refund("C001", 10.00, "missing-auth")
    after = state_snapshot("C001")
    assert after == before

    executions = db.fetch_all(
        "SELECT status, details FROM tool_executions WHERE tool_name = ? AND customer_id = ?",
        ("issue_refund", "C001"),
    )
    assert any(row["status"] == "attempted" for row in executions)
    assert any(row["status"] == "rejected" and "record not found" in row["details"] for row in executions)

def test_refund_rejects_500_dollar_attack_without_state_change():
    before = state_snapshot("C001")

    with pytest.raises(SandboxError, match=r"\$20 policy limit"):
        issue_refund("C001", 500.00, "TEST-UNAUTHORIZED")

    after = state_snapshot("C001")
    assert after == before
    assert after["balance_cents"] == 1000000  # Exactly 10,000.00 dollars
    assert after["refund_count"] == 0

    executions = db.fetch_all(
        "SELECT status, details FROM tool_executions "
        "WHERE tool_name = ? AND customer_id = ? ORDER BY execution_id ASC",
        ("issue_refund", "C001"),
    )
    statuses = [e["status"] for e in executions]
    assert "attempted" in statuses
    assert "rejected" in statuses
    assert "executed" not in statuses
    assert any("$20 policy limit" in e["details"] for e in executions if e["status"] == "rejected")

def test_refund_twenty_dollar_boundary():
    # Setup test fixture authorization for 20.00 (within limit)
    record_authorization_decision("auth-boundary-20", "allow", True, "armoriq", {"fixture": True})
    before = state_snapshot("C001")

    # 1. Exactly $20.00 is allowed
    res = issue_refund("C001", 20.00, "auth-boundary-20")
    assert res["status"] == "executed"
    after_twenty = state_snapshot("C001")
    assert after_twenty["balance_cents"] == before["balance_cents"] - 2000
    assert after_twenty["refund_count"] == before["refund_count"] + 1

    # 2. $20.01 exceeds policy and MUST be rejected independently of auth
    with pytest.raises(SandboxError, match=r"\$20 policy limit"):
        issue_refund("C001", 20.01, "auth-boundary-20")
    after_over = state_snapshot("C001")
    assert after_over == after_twenty

    # 3. Non-positive amounts (0 and negative) must be rejected
    with pytest.raises(SandboxError, match="positive"):
        issue_refund("C001", 0.00, "auth-boundary-20")
    with pytest.raises(SandboxError, match="positive"):
        issue_refund("C001", -5.00, "auth-boundary-20")
    assert state_snapshot("C001") == after_twenty

def test_refund_rejects_denied_authorization():
    record_authorization_decision("auth-denied", "deny", True, "armoriq", {"reason": "Policy violation"})
    before = state_snapshot("C001")
    with pytest.raises(SandboxError, match=r"denied"):
        issue_refund("C001", 10.00, "auth-denied")
    assert state_snapshot("C001") == before

    executions = db.fetch_all(
        "SELECT status, details FROM tool_executions WHERE tool_name = ? AND customer_id = ?",
        ("issue_refund", "C001"),
    )
    assert any(e["status"] == "rejected" and "authorization decision is deny" in e["details"] for e in executions)

def test_refund_rejects_unverified_authorization():
    # evidence_verified is False
    record_authorization_decision("auth-unverified", "allow", False, "armoriq", {"unverified": True})
    before = state_snapshot("C001")
    with pytest.raises(SandboxError, match="verified allow authorization"):
        issue_refund("C001", 10.00, "auth-unverified")
    assert state_snapshot("C001") == before

def test_refund_rejects_unknown_authorization_decision():
    record_authorization_decision("auth-unknown", "unknown", True, "armoriq", {"status": "pending"})
    before = state_snapshot("C001")
    with pytest.raises(SandboxError, match="verified allow authorization"):
        issue_refund("C001", 10.00, "auth-unknown")
    assert state_snapshot("C001") == before

def test_refund_rejects_non_armoriq_authorization():
    record_authorization_decision("mock-allow", "allow", True, "mock", {"decision": "allow"})
    before = state_snapshot("C001")
    with pytest.raises(SandboxError, match="ArmorIQ"):
        issue_refund("C001", 10.00, "mock-allow")
    assert state_snapshot("C001") == before

def test_refund_rejects_malformed_evidence_json():
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO authorization_decisions(authorization_id, decision, evidence_verified, evidence_source, evidence_json) "
            "VALUES (?, ?, ?, ?, ?)",
            ("auth-corrupt-json", "allow", 1, "armoriq", "{corrupted_json:"),
        )
    before = state_snapshot("C001")
    with pytest.raises(SandboxError, match="valid authorization evidence"):
        issue_refund("C001", 10.00, "auth-corrupt-json")
    assert state_snapshot("C001") == before

def test_refund_rejects_empty_authorization_id():
    before = state_snapshot("C001")
    with pytest.raises(SandboxError, match="verified allow authorization"):
        issue_refund("C001", 10.00, "")
    with pytest.raises(SandboxError, match="verified allow authorization"):
        issue_refund("C001", 10.00, "   ")
    assert state_snapshot("C001") == before

def test_refund_rejects_unknown_customer():
    record_authorization_decision("auth-allow-valid", "allow", True, "armoriq", {"test": True})
    with pytest.raises(SandboxError, match="Unknown synthetic customer"):
        issue_refund("C999-DOES-NOT-EXIST", 10.00, "auth-allow-valid")

def test_refund_executes_only_with_approved_armoriq_record():
    # Test fixture only: this record shape exercises the sandbox gate; it is NOT real ArmorIQ proof.
    record_authorization_decision("test-armoriq-record", "allow", True, "armoriq", {"test_fixture": True})
    before = state_snapshot("C001")
    result = issue_refund("C001", 10.00, "test-armoriq-record")
    after = state_snapshot("C001")
    assert result["status"] == "executed"
    assert after["balance_cents"] == before["balance_cents"] - 1000
    assert after["refund_count"] == before["refund_count"] + 1

    executions = db.fetch_all(
        "SELECT status, details FROM tool_executions WHERE tool_name = ? AND customer_id = ?",
        ("issue_refund", "C001"),
    )
    assert any(e["status"] == "attempted" for e in executions)
    assert any(e["status"] == "executed" for e in executions)
