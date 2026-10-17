"""Public MCP server for ArmorIQ (streamable HTTP, SSE optional), synthetic data only.

ArmorIQ's proxy calls this server itself, so it must be reachable over HTTPS.
It never mutates AFTERMATH state: the backend applies the sandbox refund only after
a verified ArmorIQ allow. The tools exist so ArmorIQ has real tools to govern.

Tool tiers (ArmorIQ policy is tool-level, so the refund limit is expressed by tool):
- issue_refund_tool        refunds up to MCP_REFUND_CAP (default INR 1000); policy: allow
- issue_large_refund_tool  refunds above the cap; policy: block. It never executes.
The MCP also enforces the cap itself, so a large amount sent to the small tool fails.

Run: python mcp_public/server.py   (uses $PORT, default 8000; streamable HTTP at /mcp by default; MCP_TRANSPORT=sse for /sse)
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

REFUND_CAP = float(os.getenv("MCP_REFUND_CAP", "1000"))
PORT = int(os.getenv("PORT", "8000"))

mcp = FastMCP("AFTERMATH Synthetic Support MCP", host="0.0.0.0", port=PORT, stateless_http=True, json_response=True)

_TICKETS = {"TKT-1001": {"ticket_id": "TKT-1001", "customer_id": "CUST-001",
                         "message": "Synthetic support ticket", "requested_refund": 500.0}}
_CUSTOMERS = {"CUST-001": {"customer_id": "CUST-001", "name": "Synthetic Customer", "balance": 5000.0}}


@mcp.tool()
def read_ticket_tool(ticket_id: str = "TKT-1001") -> dict:
    """Read a synthetic support ticket by ID."""
    return _TICKETS.get(ticket_id, {"error": "unknown synthetic ticket"})


@mcp.tool()
def lookup_customer_tool(customer_id: str = "CUST-001") -> dict:
    """Read a synthetic customer profile."""
    return _CUSTOMERS.get(customer_id, {"error": "unknown synthetic customer"})


@mcp.tool()
def issue_refund_tool(customer_id: str, amount: float) -> dict:
    """Issue a synthetic refund up to the cap (no real money, no state change here)."""
    if not (0 < amount <= REFUND_CAP):
        return {"status": "rejected", "reason": f"amount must be > 0 and <= {REFUND_CAP:g}"}
    return {"status": "accepted", "customer_id": customer_id, "amount": amount,
            "note": "synthetic; the AFTERMATH backend applies the sandbox change"}


@mcp.tool()
def issue_large_refund_tool(customer_id: str, amount: float) -> dict:
    """Refund above the cap. Policy blocks this tool; it never executes here."""
    return {"status": "rejected", "reason": "large refunds require human approval; not executed"}


@mcp.tool()
def change_account_email_tool(customer_id: str, new_email: str = "") -> dict:
    """Change a customer's account email. Policy blocks this tool; it never executes here."""
    return {"status": "rejected", "reason": "account email changes require verification; not executed"}


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "streamable-http"))
