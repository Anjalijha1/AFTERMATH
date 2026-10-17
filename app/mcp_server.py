"""MCP server exposing synthetic support tools.

Run with stdio (default): python -m app.mcp_server
Run with SSE:             python -m app.mcp_server --transport sse

The mutation tool requires a trusted ArmorIQ authorization record in SQLite.
All governance authorization decisions must be produced by the trusted ArmorIQ
adapter, never via an agent-accessible MCP tool.
"""
from __future__ import annotations
import argparse
import sys
from . import db
from .sandbox import read_ticket, lookup_customer, issue_refund

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
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
    parser = argparse.ArgumentParser(description="AFTERMATH FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol: 'stdio' (default) or 'sse'",
    )
    args = parser.parse_args()

    db.init_db(seed=True)
    if args.transport == "sse":
        sys.stderr.write("Starting AFTERMATH MCP Server over SSE transport on http://127.0.0.1:8000/sse\n")
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
