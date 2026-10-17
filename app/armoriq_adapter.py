"""ArmorIQ Integration Boundary Adapter.

This module enforces a strict, truthful boundary with ArmorIQ:
- If the official 'armoriq-sdk' package and valid ARMORIQ_API_KEY credentials
  are present, it communicates with the real ArmorIQ service.
- If the SDK or credentials are unavailable, it safely and explicitly returns
  UNAVAILABLE / UNVERIFIED, detailing exactly what configuration is missing.
- It NEVER manufactures fake authorization tokens or claims real ArmorIQ enforcement
  occurred without live verification.
"""
from __future__ import annotations
import os
import sys
from typing import Any

def check_armoriq_status() -> dict[str, Any]:
    """Check whether the official ArmorIQ SDK and credentials are configured."""
    sdk_installed = False
    try:
        import armoriq_sdk  # type: ignore # noqa: F401
        sdk_installed = True
    except ImportError:
        try:
            import armoriq  # type: ignore # noqa: F401
            sdk_installed = True
        except ImportError:
            sdk_installed = False

    api_key = os.getenv("ARMORIQ_API_KEY", "").strip()
    api_key_configured = bool(api_key)

    missing: list[str] = []
    if not sdk_installed:
        missing.append("ArmorIQ SDK ('armoriq-sdk') is not installed in the Python environment")
    if not api_key_configured:
        missing.append("ARMORIQ_API_KEY environment variable is not set or empty")

    return {
        "available": sdk_installed and api_key_configured,
        "sdk_installed": sdk_installed,
        "api_key_configured": api_key_configured,
        "missing": missing,
    }

def request_intent_authorization(
    *,
    tool_name: str,
    customer_id: str,
    amount: float,
    user_prompt: str = "",
) -> dict[str, Any]:
    """Request policy authorization through the ArmorIQ governance layer.

    Returns a standardized authorization evidence dictionary. If the SDK or
    credentials are not present, explicitly marks the evidence as unverified.
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
        }

    # If the official SDK is installed and credentials exist:
    try:
        from armoriq_sdk import ArmorIQClient  # type: ignore
        client = ArmorIQClient(api_key=os.getenv("ARMORIQ_API_KEY"))

        plan = {
            "goal": f"Execute synthetic support tool {tool_name}",
            "steps": [
                {
                    "action": tool_name,
                    "mcp": "aftermath-support-sandbox",
                    "params": {"customer_id": customer_id, "amount": amount},
                }
            ],
        }

        captured = client.capture_plan(llm="aftermath-eval", prompt=user_prompt or f"Refund request for {customer_id}", plan=plan)
        token = client.get_intent_token(captured)
        invocation = client.invoke("aftermath-support-sandbox", tool_name, token, user_email="support@synthetic.local")

        decision = "allow" if getattr(invocation, "authorized", False) else "deny"
        evidence_id = getattr(invocation, "trace_id", "") or getattr(token, "token_id", "")

        return {
            "decision": decision,
            "evidence_verified": True,
            "evidence_source": "armoriq",
            "evidence_id": str(evidence_id),
            "status": "VERIFIED",
            "reasons": [],
            "raw_evidence": {"invocation": str(invocation)},
        }
    except Exception as exc:
        return {
            "decision": "unknown",
            "evidence_verified": False,
            "evidence_source": "armoriq",
            "evidence_id": "",
            "status": "ERROR",
            "reasons": [f"ArmorIQ SDK runtime exception: {exc}"],
            "raw_evidence": {},
        }
