#!/usr/bin/env python3
"""
Example MCP Client for OpenAPI Server

This example shows how to use the MCP OpenAPI server as a client.
"""

import asyncio
import json
from mcp.client import Client
from mcp.client.stdio import stdio_client

async def main():
    """Example usage of the MCP OpenAPI server."""
    
    # Connect to the MCP server
    async with stdio_client("python", ["mcp_openapi_server.py", "keylink-updated-api.yaml"]) as (read, write):
        client = Client("example-client")
        
        # Initialize the client
        await client.initialize(read, write)
        
        print("🔧 Connected to MCP OpenAPI Server")
        print("=" * 50)
        
        # List available tools
        print("\n📋 Available Tools:")
        tools_result = await client.list_tools()
        
        for tool in tools_result.tools:
            print(f"\n🔸 {tool.name}")
            print(f"   Description: {tool.description}")
            print(f"   Input Schema: {json.dumps(tool.inputSchema, indent=2)}")
        
        # Example: Call the getAccounts tool
        if tools_result.tools:
            tool_name = tools_result.tools[0].name  # getAccounts
            print(f"\n🚀 Calling tool: {tool_name}")
            
            # Call with different category values
            test_categories = ["EDO_TRANSACTION", "MAILBOX", "CASH_ALL"]
            
            for category in test_categories:
                print(f"\n📞 Testing with category: {category}")
                
                try:
                    result = await client.call_tool(
                        name=tool_name,
                        arguments={"category": category}
                    )
                    
                    if result.isError:
                        print(f"❌ Error: {result.content[0].text}")
                    else:
                        print(f"✅ Success: {result.content[0].text[:200]}...")
                        
                except Exception as e:
                    print(f"❌ Exception: {e}")
        
        print("\n🎉 Example completed!")

if __name__ == "__main__":
    asyncio.run(main())