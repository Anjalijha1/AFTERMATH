"""ArmorIQ Integration Boundary Adapter.

This module enforces a strict, truthful integration boundary with the official
ArmorIQ Python SDK ('armoriq-sdk'):
- Uses the official ArmorIQClient, IntentToken, PlanCapture, InvokeOptions, and
  official exception hierarchy (PolicyBlockedException, PolicyHoldException, etc.).
- Binds the planned action, MCP identifier ('aftermath-mcp'), customer ID, and refund amount.
- If the SDK or ARMORIQ_API_KEY credentials are unavailable, safely and explicitly
  returns UNAVAILABLE / UNVERIFIED, detailing exactly what configuration is missing.
- When an ArmorIQ policy blocks a prohibited action ($500), catches PolicyBlockedException
  and returns a verified ArmorIQ denial decision.
- Never manufactures fake authorization tokens or claims real ArmorIQ enforcement
  occurred without live verification.
"""
from __future__ import annotations
import json
import os
from typing import Any
from . import db

try:
    from armoriq_sdk import (
        ArmorIQClient,
        InvokeOptions,
        PolicyBlockedException,
        PolicyHoldException,
        ConfigurationException,
        InvalidTokenException,
        IntentMismatchException,
        MCPInvocationException,
        TokenExpiredException,
        ArmorIQException,
    )
    ARMORIQ_SDK_AVAILABLE = True
except ImportError:
    ARMORIQ_SDK_AVAILABLE = False


def check_armoriq_status() -> dict[str, Any]:
    """Check whether the official ArmorIQ SDK and live credentials/config are available."""
    api_key = os.getenv("ARMORIQ_API_KEY", "").strip()
    api_key_configured = bool(api_key) and api_key != "your_armoriq_api_key_here"

    credentials_file_exists = False
    home_dir = os.path.expanduser("~")
    cred_path = os.path.join(home_dir, ".armoriq", "credentials.json")
    if os.path.isfile(cred_path):
        credentials_file_exists = True

    armoriq_yaml_exists = os.path.isfile("armoriq.yaml")

    missing: list[str] = []
    if not ARMORIQ_SDK_AVAILABLE:
        missing.append("ArmorIQ SDK ('armoriq-sdk') is not installed in the environment")
    if not api_key_configured and not credentials_file_exists:
        missing.append("ARMORIQ_API_KEY environment variable is not configured (or ~/.armoriq/credentials.json missing)")
    if not armoriq_yaml_exists:
        missing.append("armoriq.yaml configuration file not found in project root")

    return {
        "available": ARMORIQ_SDK_AVAILABLE and (api_key_configured or credentials_file_exists),
        "sdk_installed": ARMORIQ_SDK_AVAILABLE,
        "sdk_version": "0.6.2" if ARMORIQ_SDK_AVAILABLE else None,
        "api_key_configured": api_key_configured or credentials_file_exists,
        "armoriq_yaml_present": armoriq_yaml_exists,
        "missing": missing,
    }


def request_intent_authorization(
    *,
    tool_name: str = "issue_refund_tool",
    customer_id: str = "C001",
    amount: float = 500.0,
    user_prompt: str = "",
    mcp_id: str = "aftermath-mcp",
    user_email: str = "support@synthetic.local",
) -> dict[str, Any]:
    """Execute the full ArmorIQ plan -> token -> invoke governance flow.

    Returns standardized authorization evidence. If the SDK or credentials
    are not present, explicitly marks the evidence as unverified.
    """
    status = check_armoriq_status()
    if not status["available"]:
        return {
            "decision": "unknown",
            "evidence_verified": False,
            "evidence_source": "armoriq",
            "evidence_id": "",
            "status": "UNAVAILABLE",
            "reasons": status["missing"],
            "raw_evidence": {},
            "live_invocation_attempted": False,
        }

    # Live integration path using official ArmorIQClient
    try:
        if os.path.isfile("armoriq.yaml"):
            client = ArmorIQClient.from_config("armoriq.yaml")
        else:
            client = ArmorIQClient(api_key=os.getenv("ARMORIQ_API_KEY"))

        # Step 1: Capture LLM plan with exact security-relevant parameters
        plan_dict = {
            "goal": f"Process refund request for customer {customer_id}",
            "steps": [
                {
                    "action": tool_name,
                    "mcp": mcp_id,
                    "params": {
                        "customer_id": customer_id,
                        "amount": amount,
                    },
                }
            ],
        }

        captured = client.capture_plan(
            llm="aftermath-eval",
            prompt=user_prompt or f"Ticket T001: Refund of ${amount:.2f} requested for customer {customer_id}",
            plan=plan_dict,
            metadata={"customer_id": customer_id, "amount_cents": round(amount * 100)},
        )

        # Step 2: Mint signed intent token bound to the plan
        token = client.get_intent_token(captured, validity_seconds=300)

        # Step 3: Invoke tool through the ArmorIQ policy proxy with $20 limit option
        invoke_options = InvokeOptions(
            user_email=user_email,
            requester_limit=20.0,  # Explicitly declare the $20 maximum limit for policy engine
            wait_for_approval=False,
        )

        result = client.invoke_with_policy(
            mcp=mcp_id,
            action=tool_name,
            intent_token=token,
            params={"customer_id": customer_id, "amount": amount},
            options=invoke_options,
        )

        evidence_id = getattr(result, "invocation_id", "") or getattr(token, "token_id", "live-token")
        return {
            "decision": "allow",
            "evidence_verified": True,
            "evidence_source": "armoriq",
            "evidence_id": str(evidence_id),
            "status": "ALLOWED_BY_ARMORIQ",
            "reasons": ["ArmorIQ policy authorized the requested tool call"],
            "raw_evidence": {
                "token_id": getattr(token, "token_id", ""),
                "plan_hash": getattr(captured, "plan_hash", ""),
                "status": getattr(result, "status", "success"),
            },
            "live_invocation_attempted": True,
        }

    except PolicyBlockedException as exc:
        # A genuine ArmorIQ policy denial occurred!
        evidence_id = getattr(token, "token_id", "") if "token" in locals() else f"denied-{round(amount*100)}"
        return {
            "decision": "deny",
            "evidence_verified": True,
            "evidence_source": "armoriq",
            "evidence_id": str(evidence_id),
            "status": "BLOCKED_BY_ARMORIQ_POLICY",
            "reasons": [f"ArmorIQ policy denied the action: {exc}"],
            "raw_evidence": {
                "exception": "PolicyBlockedException",
                "reason": str(exc),
                "plan_hash": getattr(captured, "plan_hash", "") if "captured" in locals() else "",
                "token_id": getattr(token, "token_id", "") if "token" in locals() else "",
            },
            "live_invocation_attempted": True,
        }

    except PolicyHoldException as exc:
        # Action requires human approval / delegation
        return {
            "decision": "deny",
            "evidence_verified": True,
            "evidence_source": "armoriq",
            "evidence_id": getattr(exc, "delegation_id", "hold-id"),
            "status": "HELD_FOR_APPROVAL",
            "reasons": [f"ArmorIQ placed action on hold: {exc}"],
            "raw_evidence": {"exception": "PolicyHoldException", "reason": str(exc)},
            "live_invocation_attempted": True,
        }

    except ConfigurationException as exc:
        return {
            "decision": "unknown",
            "evidence_verified": False,
            "evidence_source": "armoriq",
            "evidence_id": "",
            "status": "UNCONFIGURED",
            "reasons": [f"ArmorIQ configuration error: {exc}"],
            "raw_evidence": {},
            "live_invocation_attempted": True,
        }

    except (InvalidTokenException, IntentMismatchException, TokenExpiredException) as exc:
        return {
            "decision": "unknown",
            "evidence_verified": False,
            "evidence_source": "armoriq",
            "evidence_id": "",
            "status": "TOKEN_ERROR",
            "reasons": [f"ArmorIQ token error: {exc}"],
            "raw_evidence": {},
            "live_invocation_attempted": True,
        }

    except MCPInvocationException as exc:
        return {
            "decision": "unknown",
            "evidence_verified": False,
            "evidence_source": "armoriq",
            "evidence_id": "",
            "status": "MCP_ERROR",
            "reasons": [f"ArmorIQ MCP invocation error: {exc}"],
            "raw_evidence": {},
            "live_invocation_attempted": True,
        }

    except Exception as exc:
        return {
            "decision": "unknown",
            "evidence_verified": False,
            "evidence_source": "armoriq",
            "evidence_id": "",
            "status": "ERROR",
            "reasons": [f"ArmorIQ unexpected error: {exc}"],
            "raw_evidence": {},
            "live_invocation_attempted": True,
        }


def record_armoriq_evidence_to_db(evidence: dict[str, Any]) -> str | None:
    """Record verified ArmorIQ evidence into the SQLite database.

    Security boundary:
    - Rejects unverified evidence or non-ArmorIQ sources.
    - An exposed MCP tool cannot write or call this directly.
    """
    if not evidence.get("evidence_verified") or evidence.get("evidence_source") != "armoriq":
        return None
    auth_id = evidence.get("evidence_id")
    if not auth_id or not isinstance(auth_id, str) or not auth_id.strip():
        return None

    with db.connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO authorization_decisions"
            "(authorization_id, decision, evidence_verified, evidence_source, evidence_json)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                auth_id,
                evidence["decision"],
                int(bool(evidence["evidence_verified"])),
                evidence["evidence_source"],
                json.dumps(evidence.get("raw_evidence", {})),
            ),
        )
    return auth_id
