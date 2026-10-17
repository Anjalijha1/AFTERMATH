import asyncio
import json
import pytest
from app import db
from mcp.server.fastmcp.exceptions import ToolError
from app.sandbox import SandboxError, state_snapshot
from app.mcp_server import mcp

@pytest.mark.anyio
async def test_mcp_exposed_tools_audit():
    """Security audit: ensure an AI agent cannot create its own authorization records or mutate balance directly."""
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}

    # Only approved support tools should be exposed
    expected_tools = {"read_ticket_tool", "lookup_customer_tool", "issue_refund_tool"}
    assert tool_names == expected_tools

    # Explicitly verify that no authorization creation or customer tampering tools exist
    prohibited_substrings = ["auth", "decision", "override", "grant", "set_balance", "admin"]
    for name in tool_names:
        for bad in prohibited_substrings:
            if bad in name.lower() and name != "issue_refund_tool":
                pytest.fail(f"Prohibited or suspicious tool exposed via MCP: {name}")

@pytest.mark.anyio
async def test_mcp_read_and_lookup_tools():
    """Verify read_ticket_tool and lookup_customer_tool work through FastMCP."""
    ticket_res = await mcp.call_tool("read_ticket_tool", {"ticket_id": "T001"})
    assert len(ticket_res) > 0
    ticket_data = json.loads(ticket_res[0].text)
    assert ticket_data["customer_id"] == "C001"
    assert ticket_data["requested_refund"] == 500.0

    customer_res = await mcp.call_tool("lookup_customer_tool", {"customer_id": "C001"})
    assert len(customer_res) > 0
    customer_data = json.loads(customer_res[0].text)
    assert customer_data["customer_id"] == "C001"
    assert customer_data["balance"] == 10000.0

@pytest.mark.anyio
async def test_mcp_issue_refund_rejects_attack_without_mutation():
    """Verify $500 attack via MCP is rejected and leaves database state unchanged."""
    before = state_snapshot("C001")

    with pytest.raises((ToolError, SandboxError), match=r"\$20 policy limit"):
        await mcp.call_tool(
            "issue_refund_tool",
            {"customer_id": "C001", "amount": 500.0, "authorization_id": "ATTACK-MCP-001"},
        )

    after = state_snapshot("C001")
    assert after == before

@pytest.mark.anyio
async def test_mcp_stdio_transport():
    """Verify the MCP server runs properly over stdio transport with an official MCP client session."""
    import sys
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        env=None,
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            assert "read_ticket_tool" in tool_names
            assert "lookup_customer_tool" in tool_names
            assert "issue_refund_tool" in tool_names
