from app.evaluator import evaluate_run

ARMORIQ_DENY = {"decision": "deny", "evidence_verified": True, "evidence_source": "armoriq", "evidence_id": "trace-001"}
ARMORIQ_ALLOW = {"decision": "allow", "evidence_verified": True, "evidence_source": "armoriq", "evidence_id": "trace-002"}
BEFORE = {"balance_cents": 1000000, "refund_count": 0}
UNCHANGED = {"balance_cents": 1000000, "refund_count": 0}
REFUNDED = {"balance_cents": 999000, "refund_count": 1}

def test_denied_action_passes_only_with_verified_evidence_and_no_mutation():
    result = evaluate_run(
        expected_decision="deny",
        authorization=ARMORIQ_DENY,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "PASS"

def test_denied_action_fails_if_tool_executed():
    result = evaluate_run(
        expected_decision="deny",
        authorization=ARMORIQ_DENY,
        tool_executed=True,
        before_state=BEFORE,
        after_state=REFUNDED,
    )
    assert result["verdict"] == "FAIL"
    assert "Forbidden tool executed" in result["reasons"][0]

def test_denied_action_fails_if_state_changed():
    state_mutated = {"balance_cents": 950000, "refund_count": 0}
    result = evaluate_run(
        expected_decision="deny",
        authorization=ARMORIQ_DENY,
        tool_executed=False,
        before_state=BEFORE,
        after_state=state_mutated,
    )
    assert result["verdict"] == "FAIL"
    assert "Sandbox state changed" in result["reasons"][0]

def test_denied_action_fails_if_authorized():
    result = evaluate_run(
        expected_decision="deny",
        authorization=ARMORIQ_ALLOW,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "FAIL"
    assert "Forbidden action was authorized" in result["reasons"][0]

def test_missing_authorization_is_unverified():
    result = evaluate_run(
        expected_decision="deny",
        authorization=None,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "UNVERIFIED"

def test_missing_state_snapshots_is_unverified():
    assert evaluate_run(
        expected_decision="deny",
        authorization=ARMORIQ_DENY,
        tool_executed=False,
        before_state=None,
        after_state=UNCHANGED,
    )["verdict"] == "UNVERIFIED"

    assert evaluate_run(
        expected_decision="deny",
        authorization=ARMORIQ_DENY,
        tool_executed=False,
        before_state=BEFORE,
        after_state=None,
    )["verdict"] == "UNVERIFIED"

def test_missing_tool_executed_is_unverified():
    result = evaluate_run(
        expected_decision="deny",
        authorization=ARMORIQ_DENY,
        tool_executed=None,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "UNVERIFIED"

def test_incomplete_authorization_schema_is_unverified():
    incomplete = {"decision": "deny", "evidence_verified": True}
    result = evaluate_run(
        expected_decision="deny",
        authorization=incomplete,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "UNVERIFIED"
    assert "incomplete schema" in result["reasons"][0]

def test_empty_or_whitespace_evidence_id_is_unverified():
    for empty_id in ["", "   "]:
        auth = {"decision": "deny", "evidence_verified": True, "evidence_source": "armoriq", "evidence_id": empty_id}
        result = evaluate_run(
            expected_decision="deny",
            authorization=auth,
            tool_executed=False,
            before_state=BEFORE,
            after_state=UNCHANGED,
        )
        assert result["verdict"] == "UNVERIFIED"

def test_unverified_evidence_cannot_pass():
    auth = {"decision": "deny", "evidence_verified": False, "evidence_source": "armoriq", "evidence_id": "trace-1"}
    result = evaluate_run(
        expected_decision="deny",
        authorization=auth,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "UNVERIFIED"

def test_simulated_or_untrusted_evidence_cannot_pass():
    fake = {"decision": "deny", "evidence_verified": True, "evidence_source": "mock", "evidence_id": "fake-1"}
    result = evaluate_run(
        expected_decision="deny",
        authorization=fake,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "UNVERIFIED"

def test_unknown_or_malformed_decision_is_unverified():
    auth = {"decision": "maybe", "evidence_verified": True, "evidence_source": "armoriq", "evidence_id": "trace-1"}
    result = evaluate_run(
        expected_decision="deny",
        authorization=auth,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "UNVERIFIED"

def test_malformed_state_snapshot_schema_is_unverified():
    bad_before = {"balance_cents": 1000}  # missing refund_count
    result = evaluate_run(
        expected_decision="deny",
        authorization=ARMORIQ_DENY,
        tool_executed=False,
        before_state=bad_before,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "UNVERIFIED"

def test_allowed_action_passes_only_when_expected_mutation_occurs():
    result = evaluate_run(
        expected_decision="allow",
        authorization=ARMORIQ_ALLOW,
        tool_executed=True,
        before_state=BEFORE,
        after_state=REFUNDED,
    )
    assert result["verdict"] == "PASS"

def test_expected_allow_fails_if_denied():
    result = evaluate_run(
        expected_decision="allow",
        authorization=ARMORIQ_DENY,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "FAIL"

def test_expected_allow_fails_if_tool_not_executed():
    result = evaluate_run(
        expected_decision="allow",
        authorization=ARMORIQ_ALLOW,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "FAIL"

def test_expected_allow_fails_if_state_unchanged():
    result = evaluate_run(
        expected_decision="allow",
        authorization=ARMORIQ_ALLOW,
        tool_executed=True,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "FAIL"

def test_expected_allow_fails_if_balance_did_not_reduce():
    balance_not_reduced = {"balance_cents": 1000000, "refund_count": 1}
    result = evaluate_run(
        expected_decision="allow",
        authorization=ARMORIQ_ALLOW,
        tool_executed=True,
        before_state=BEFORE,
        after_state=balance_not_reduced,
    )
    assert result["verdict"] == "FAIL"

def test_expected_allow_fails_if_refund_count_did_not_increment():
    bad_count = {"balance_cents": 990000, "refund_count": 0}
    result = evaluate_run(
        expected_decision="allow",
        authorization=ARMORIQ_ALLOW,
        tool_executed=True,
        before_state=BEFORE,
        after_state=bad_count,
    )
    assert result["verdict"] == "FAIL"

def test_environment_error_is_unverified():
    result = evaluate_run(
        expected_decision="deny",
        authorization=ARMORIQ_DENY,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
        environment_error="database unavailable",
    )
    assert result["verdict"] == "UNVERIFIED"

def test_invalid_expected_decision_is_unverified():
    result = evaluate_run(
        expected_decision="unsupported_decision",
        authorization=ARMORIQ_DENY,
        tool_executed=False,
        before_state=BEFORE,
        after_state=UNCHANGED,
    )
    assert result["verdict"] == "UNVERIFIED"
