import asyncio
import pprint
from fastmcp import Client
from fastmcp.transports import StreamableHttpTransport

SERVER_URL = "http://127.0.0.1:8000/mcp"
pp = pprint.PrettyPrinter(indent=2, width=100)

async def main():
    transport = StreamableHttpTransport(url=SERVER_URL)
    client = Client(transport)

    async with client:
        print(f"\n🔌 Connecting to MCP server at {SERVER_URL}...")

        # 1. Ping
        print("\n🛠 Testing connectivity...")
        await client.ping()
        print("✅ Server is reachable!\n")

        # 2. List tools
        print("📋 Available tools:")
        tools = await client.list_tools()
        pp.pprint(tools)

        # 3. Call login tool
        print("\n🔑 Calling login tool...")
        login_resp = await client.call_tool("login")
        pp.pprint(login_resp)

        # 4. Call get_banks tool
        print("\n🏦 Calling get_banks tool for module='ABC'...")
        banks_resp = await client.call_tool("get_banks", module="ABC")
        pp.pprint(banks_resp)

if __name__ == "__main__":
    asyncio.run(main())
