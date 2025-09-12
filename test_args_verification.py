#!/usr/bin/env python3
"""
Test script to verify that arguments are properly passed to OpenAPI endpoints
"""

import asyncio
import json
import logging
from fastmcp import Client as MCPClient
from fastmcp.client import PythonStdioTransport

# Configure logging to see argument passing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_args")

async def test_argument_passing():
    """Test that arguments are properly passed to OpenAPI endpoints"""
    
    print("🧪 Testing MCP Argument Passing")
    print("=" * 50)
    
    # Connect to MCP server
    transport = PythonStdioTransport("mcp_server_fastmcp2.py", args=["--transport", "stdio"])
    
    async with MCPClient(transport) as mcp:
        print("✅ Connected to MCP server")
        
        # Test 1: List available tools
        print("\n📋 Available Tools:")
        tools = await mcp.list_tools()
        print(f"Found {len(tools)} tools")
        
        # Show some tool examples
        for i, tool in enumerate(tools[:5]):  # Show first 5 tools
            print(f"  {i+1}. {tool.name}")
            print(f"     Description: {tool.description[:100]}...")
            if tool.inputSchema and 'properties' in tool.inputSchema:
                props = list(tool.inputSchema['properties'].keys())
                print(f"     Parameters: {props}")
            print()
        
        # Test 2: Test set_credentials tool with arguments
        print("🔐 Testing set_credentials tool:")
        try:
            result = await mcp.call_tool("set_credentials", {
                "username": "test_user",
                "password": "test_password",
                "login_url": "http://localhost:8080/auth/login"
            })
            print("✅ set_credentials called successfully")
            print(f"Result: {result.content[:200] if hasattr(result, 'content') else str(result)[:200]}...")
        except Exception as e:
            print(f"❌ set_credentials failed: {e}")
        
        # Test 3: Test perform_login tool
        print("\n🔑 Testing perform_login tool:")
        try:
            result = await mcp.call_tool("perform_login", {
                "force_login": True
            })
            print("✅ perform_login called successfully")
            print(f"Result: {result.content[:200] if hasattr(result, 'content') else str(result)[:200]}...")
        except Exception as e:
            print(f"❌ perform_login failed: {e}")
        
        # Test 4: Find and test an API tool with parameters
        print("\n🌐 Testing API tool with parameters:")
        api_tools = [tool for tool in tools if tool.name not in ["set_credentials", "perform_login"]]
        
        if api_tools:
            # Find a tool with parameters
            test_tool = None
            for tool in api_tools:
                if tool.inputSchema and 'properties' in tool.inputSchema and tool.inputSchema['properties']:
                    test_tool = tool
                    break
            
            if test_tool:
                print(f"Testing tool: {test_tool.name}")
                print(f"Parameters: {list(tool.inputSchema['properties'].keys())}")
                
                # Create test arguments based on the schema
                # FastMCP 2.0 passes parameters directly to the function
                test_args = {}
                if 'properties' in test_tool.inputSchema:
                    for param_name, param_schema in test_tool.inputSchema['properties'].items():
                        param_type = param_schema.get('type', 'string')
                        if param_type == 'string':
                            test_args[param_name] = f"test_{param_name}"
                        elif param_type == 'number':
                            test_args[param_name] = 100
                        elif param_type == 'boolean':
                            test_args[param_name] = True
                        elif param_type == 'integer':
                            test_args[param_name] = 1
                
                print(f"Test arguments: {test_args}")
                
                try:
                    result = await mcp.call_tool(test_tool.name, test_args)
                    print("✅ API tool called successfully")
                    print(f"Result: {result.content[:300] if hasattr(result, 'content') else str(result)[:300]}...")
                except Exception as e:
                    print(f"❌ API tool failed: {e}")
            else:
                print("No API tools with parameters found")
        else:
            print("No API tools found")
        
        print("\n🎯 Argument Passing Test Complete!")
        print("Check the logs above to verify arguments are being passed correctly.")

if __name__ == "__main__":
    asyncio.run(test_argument_passing())
