#!/usr/bin/env python3
"""
Simple test to verify validation behavior
"""

import asyncio
import json
import logging
from fastmcp import Client as MCPClient
from fastmcp.client import PythonStdioTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_validation")

async def test_simple_validation():
    """Simple test to verify validation behavior"""
    
    print("🔧 Simple Validation Test")
    print("=" * 40)
    
    # Connect to MCP server
    transport = PythonStdioTransport("mcp_server_fastmcp2.py", args=["--transport", "stdio"])
    
    async with MCPClient(transport) as mcp:
        print("✅ Connected to MCP server")
        
        # Get tools and examine their schemas
        tools = await mcp.list_tools()
        api_tools = [tool for tool in tools if not tool.name in ["set_credentials", "perform_login"]]
        
        print(f"\n📋 Found {len(api_tools)} API tools")
        
        # Examine the first tool's schema
        if api_tools:
            tool = api_tools[0]
            print(f"\n🔍 Examining tool: {tool.name}")
            print(f"Description: {tool.description[:100]}...")
            print(f"Input Schema:")
            print(json.dumps(tool.inputSchema, indent=2))
            
            # Test calling the tool with the correct format
            print(f"\n🧪 Testing tool call with arguments wrapper:")
            try:
                result = await mcp.call_tool(tool.name, {
                    "arguments": {
                        "status": "pending",
                        "date_from": "2024-01-01"
                    }
                })
                print("✅ Tool call with arguments wrapper works!")
                print(f"Response: {str(result)[:100]}...")
            except Exception as e:
                print(f"❌ Tool call with arguments wrapper failed: {e}")
            
            # Test calling the tool without arguments wrapper
            print(f"\n🧪 Testing tool call without arguments wrapper:")
            try:
                result = await mcp.call_tool(tool.name, {
                    "status": "pending",
                    "date_from": "2024-01-01"
                })
                print("✅ Tool call without arguments wrapper works!")
                print(f"Response: {str(result)[:100]}...")
            except Exception as e:
                print(f"❌ Tool call without arguments wrapper failed: {e}")
        
        print(f"\n🎯 Simple Validation Test Results")
        print("=" * 40)
        print("This test shows the current behavior and helps identify the correct calling format.")

if __name__ == "__main__":
    asyncio.run(test_simple_validation())
