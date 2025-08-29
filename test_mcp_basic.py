#!/usr/bin/env python3
"""
Basic MCP Protocol Test
Test the MCP protocol with the available API.
"""

import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters, stdio_client, Tool, CallToolRequest, ListToolsResult

async def test_mcp_basic():
    """Test basic MCP functionality."""
    print("Testing MCP protocol...")
    
    try:
        # Create server parameters
        mcp_server_path = os.path.join(os.getcwd(), "mcp_server.py")
        server_params = StdioServerParameters(
            command=f"{sys.executable} {mcp_server_path}",
            args=[],
            env={}
        )
        
        print(f"Server command: {server_params.command}")
        print(f"Server args: {server_params.args}")
        
        # Try to connect
        async with stdio_client(server_params) as session:
            print("✅ Connected to MCP server")
            
            # Try to list tools
            try:
                tools_result = await session.list_tools()
                print(f"✅ Listed {len(tools_result.tools)} tools")
                for tool in tools_result.tools:
                    print(f"  - {tool.name}: {tool.description[:50]}...")
            except Exception as e:
                print(f"❌ Failed to list tools: {e}")
            
    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_mcp_basic())
    if success:
        print("✅ MCP basic test passed!")
    else:
        print("❌ MCP basic test failed!")
        sys.exit(1)
