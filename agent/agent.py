"""AFTERMATH support agent: interpret a ticket into a structured proposal.

The agent only INTERPRETS the ticket. It never authorizes and never executes;
ArmorIQ (governance) and the backend evaluator own those decisions. When no
Gemini key/SDK is available, a deterministic fallback parser keeps the system
usable and labels itself clearly in the explanation.
"""
from __future__ import annotations

import re

from .schemas import AgentResult, ProposedAction

_AMOUNT_RE = re.compile(r"(\d+(?:\.\d{1,2})?)")


def _fallback_proposal(ticket: str, customer_id: str, refund_limit: float) -> ProposedAction:
    """Deterministic, conservative ticket parser used when no LLM is available."""
    amounts = [float(m.group(1)) for m in _AMOUNT_RE.finditer(ticket)]
    # The largest mentioned amount is the riskiest reading of the ticket, so
    # governance (ArmorIQ) sees the worst case an injected ticket asks for.
    amount = max(amounts) if amounts else 0.0
    lowered = ticket.lower()
    wants_refund = "refund" in lowered or ("request" in lowered and amount > 0)
    if wants_refund and amount > 0:
        return ProposedAction(
            action="issue_refund",
            customer_id=customer_id,
            amount=amount,
            reason=(
                f"Ticket requests a refund of {amount:g}. Whether it is within the "
                f"{refund_limit:g} limit is for the governance layer to decide, not the agent."
            ),
        )
    return ProposedAction(
        action="deny_request",
        customer_id=customer_id,
        amount=0.0,
        reason="Ticket does not contain a refund request the agent can act on.",
    )


def propose_action(*, ticket: str, customer_id: str, refund_limit: float) -> tuple[AgentResult, str]:
    """Return (AgentResult, source); source is 'gemini' or 'fallback'."""
    try:
        from .llm_client import gemini_propose

        proposed = gemini_propose(ticket=ticket, customer_id=customer_id, refund_limit=refund_limit)
        return (
            AgentResult(
                proposed_action=proposed,
                explanation="Gemini interpretation of the ticket. A proposal only - not an authorization.",
            ),
            "gemini",
        )
    except Exception as exc:
        proposed = _fallback_proposal(ticket, customer_id, refund_limit)
        return (
            AgentResult(
                proposed_action=proposed,
                explanation=(
                    f"Deterministic fallback used because the LLM path was unavailable ({exc}). "
                    "A proposal only - not an authorization."
                ),
            ),
            "fallback",
        )
