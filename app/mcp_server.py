"""MCP server exposing synthetic support tools.

Run with: python -m app.mcp_server
The mutation tool requires a trusted ArmorIQ authorization record in SQLite.
"""
from . import db
from .sandbox import read_ticket, lookup_customer, issue_refund

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # clear message if dependency is missing
    raise SystemExit("MCP dependency missing. Install requirements.txt first.") from exc

mcp = FastMCP("AFTERMATH Synthetic Support Sandbox")

@mcp.tool()
def read_ticket_tool(ticket_id: str) -> dict:
    """Read a synthetic support ticket by ID."""
    return read_ticket(ticket_id)

@mcp.tool()
def lookup_customer_tool(customer_id: str) -> dict:
    """Read a synthetic customer's profile and balance."""
    return lookup_customer(customer_id)

@mcp.tool()
def issue_refund_tool(customer_id: str, amount: float, authorization_id: str) -> dict:
    """Issue a synthetic refund only after a verified ArmorIQ allow decision."""
    return issue_refund(customer_id, amount, authorization_id)

def main() -> None:
    db.init_db(seed=True)
    mcp.run()

if __name__ == "__main__":
    main()
