#!/usr/bin/env python3
"""
Test Tool Loading - Verify Modular Service Loads All Tools
========================================================
Test script to verify that the modular MCP service loads all available tools
from the MCP server.
"""

import asyncio
import subprocess
import time
import signal
import os
from modular_mcp_service import create_modular_service

async def test_tool_loading():
    """Test that the modular service loads all tools from MCP server"""
    print("🧪 Testing Tool Loading with Modular MCP Service")
    print("=" * 60)
    
    # Start MCP server in background
    print("🔄 Starting MCP server...")
    server_process = subprocess.Popen([
        "python3", "mcp_server_fastmcp2.py", "--transport", "stdio"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait a moment for server to start
    time.sleep(2)
    
    try:
        print("🔄 Creating modular MCP service...")
        service = await create_modular_service(use_mock=False)
        
        print("🔄 Loading tools...")
        tools = await service.get_available_tools()
        
        print(f"✅ Successfully loaded {len(tools)} tools")
        print("\n📋 Tool List:")
        print("-" * 40)
        
        for i, tool in enumerate(tools, 1):
            name = tool.get('function', {}).get('name', 'unknown')
            description = tool.get('function', {}).get('description', 'No description')
            print(f"{i:2d}. {name}")
            print(f"    {description}")
            print()
        
        # Test a simple message processing
        print("🔄 Testing message processing...")
        result = await service.process_message(
            user_message="What tools are available?",
            session_id="test_session"
        )
        
        print(f"✅ Message processed successfully")
        print(f"   Response: {result.get('response', 'No response')[:100]}...")
        
        await service.cleanup()
        print("✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up server process
        print("🔄 Stopping MCP server...")
        server_process.terminate()
        server_process.wait()
        print("✅ MCP server stopped")

if __name__ == "__main__":
    asyncio.run(test_tool_loading())