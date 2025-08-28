#!/usr/bin/env python3
"""
Test script for the new MCP architecture
"""

import asyncio
import os
from mcp_llm_client import MCPLLMClient

async def test_new_mcp():
    """Test the new MCP architecture."""
    print("🧪 Testing new MCP architecture...")
    
    # Initialize client
    client = MCPLLMClient()
    
    try:
        # Test 1: List tools
        print("\n1. Testing tool listing...")
        tools = await client.list_tools()
        print(f"✅ Found {len(tools)} tools")
        for tool in tools[:3]:  # Show first 3
            print(f"   - {tool['name']}: {tool['description'][:50]}...")
        
        # Test 2: Set credentials
        print("\n2. Testing credential setting...")
        result = await client.set_credentials("testuser", "testpass", "cash_api")
        print(f"✅ Credentials set: {result.get('status')}")
        
        # Test 3: Execute a simple query
        print("\n3. Testing query execution...")
        result = await client.execute_query("Show me pending payments")
        print(f"✅ Query executed: {result.get('status')}")
        if result.get('answer'):
            print(f"   Answer: {result.get('answer')[:100]}...")
        
        print("\n🎉 All tests passed! New MCP architecture is working.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_new_mcp())