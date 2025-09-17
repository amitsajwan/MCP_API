#!/usr/bin/env python3
"""
Test Full Tool Loading - Verify All Tools Are Loaded from MCP Server
===================================================================
Test script to verify that the modular service loads all tools from the MCP server.
"""

import asyncio
import subprocess
import time
import signal
import os
from modular_mcp_service import create_modular_service

async def test_full_tool_loading():
    """Test that the modular service loads all tools from MCP server"""
    print("🧪 Testing Full Tool Loading from MCP Server")
    print("=" * 60)
    
    # Start MCP server in background
    print("🔄 Starting MCP server...")
    server_process = subprocess.Popen([
        "python3", "mcp_server_fastmcp2.py", "--transport", "stdio"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait a moment for server to start
    time.sleep(3)
    
    try:
        print("🔄 Creating modular MCP service...")
        service = await create_modular_service(use_mock=False, use_mock_llm=True)
        
        print("🔄 Loading tools from MCP server...")
        tools = await service.get_available_tools()
        
        print(f"✅ Successfully loaded {len(tools)} tools from MCP server")
        print("\n📋 Tool Categories:")
        print("-" * 40)
        
        # Group tools by API spec
        tool_categories = {}
        for tool in tools:
            name = tool.get('function', {}).get('name', 'unknown')
            # Extract category from tool name (e.g., cash_get_payments -> cash)
            category = name.split('_')[0] if '_' in name else 'other'
            if category not in tool_categories:
                tool_categories[category] = []
            tool_categories[category].append(name)
        
        for category, tool_list in sorted(tool_categories.items()):
            print(f"\n🔧 {category.upper()} API ({len(tool_list)} tools):")
            for tool_name in sorted(tool_list)[:5]:  # Show first 5 tools per category
                print(f"  - {tool_name}")
            if len(tool_list) > 5:
                print(f"  ... and {len(tool_list) - 5} more tools")
        
        # Test a simple message processing
        print("\n🔄 Testing message processing...")
        result = await service.process_message(
            user_message="What tools are available?",
            session_id="test_session"
        )
        
        print(f"✅ Message processed successfully")
        print(f"   Response: {result.get('response', 'No response')[:100]}...")
        print(f"   Tool calls executed: {len(result.get('tool_calls', []))}")
        
        await service.cleanup()
        print("✅ Test completed successfully")
        
        return len(tools)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 0
    
    finally:
        # Clean up server process
        print("\n🔄 Stopping MCP server...")
        server_process.terminate()
        server_process.wait()
        print("✅ MCP server stopped")

if __name__ == "__main__":
    print("🚀 Starting Full Tool Loading Test")
    print("=" * 60)
    
    tool_count = asyncio.run(test_full_tool_loading())
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"  Tools loaded: {tool_count}")
    
    if tool_count > 40:  # Expect around 49 tools
        print("🎉 SUCCESS: All API specs are being parsed and loaded correctly!")
    elif tool_count > 0:
        print("⚠️  PARTIAL: Some tools loaded, but not all API specs may be parsed")
    else:
        print("❌ FAILED: No tools were loaded from MCP server")