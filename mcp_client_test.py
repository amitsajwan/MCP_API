import asyncio
import pprint
import pytest
from fastmcp_client import DirectHTTPMCPClient

SERVER_URL = "http://127.0.0.1:8000/mcp"
pp = pprint.PrettyPrinter(indent=2, width=100)

@pytest.mark.asyncio
async def test_ping():
    """
    Test server connectivity.
    """
    client = DirectHTTPMCPClient(server_url=SERVER_URL)

    async with client:
        print(f"\n🔌 Connecting to MCP server at {SERVER_URL}...")
        is_healthy = await client.health_check()
        assert is_healthy, "❌ Server is not reachable!"
        print("✅ Server is reachable!")

@pytest.mark.asyncio
async def test_list_tools():
    """
    Test listing available tools.
    """
    client = DirectHTTPMCPClient(server_url=SERVER_URL)

    async with client:
        print("\n📋 Testing list tools...")
        tools = await client.list_tools()
        assert tools, "❌ No tools found!"
        pp.pprint(tools)

@pytest.mark.asyncio
async def test_login_tool():
    """
    Test the login tool.
    """
    client = DirectHTTPMCPClient(server_url=SERVER_URL)

    async with client:
        print("\n🔑 Testing login tool...")
        login_resp = await client.call_tool("login", username="admin", password="password")
        assert "cookie" in login_resp, "❌ Login failed!"
        pp.pprint(login_resp)

@pytest.mark.asyncio
async def test_get_banks_tool():
    """
    Test the get_banks tool.
    """
    client = DirectHTTPMCPClient(server_url=SERVER_URL)

    async with client:
        print("\n🏦 Testing get_banks tool...")
        banks_resp = await client.call_tool("get_banks", module="ABC")
        assert banks_resp, "❌ Failed to retrieve banks!"
        pp.pprint(banks_resp)

if __name__ == "__main__":
    pytest.main(["-v"])
