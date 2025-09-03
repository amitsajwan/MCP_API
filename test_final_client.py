#!/usr/bin/env python3
"""
Test script for the final production-ready MCP client.
This script tests HTTP-only communication with the MCP server.
"""

import json
import logging
from mcp_client import MCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_connection():
    """Test basic connection to MCP server."""
    print("\n=== Testing Connection ===")
    client = MCPClient()
    
    if client.connect():
        print("✅ Successfully connected to MCP server")
        client.disconnect()
        return True
    else:
        print("❌ Failed to connect to MCP server")
        return False

def test_list_tools():
    """Test listing available tools."""
    print("\n=== Testing Tool Listing ===")
    client = MCPClient()
    
    if not client.connect():
        print("❌ Failed to connect")
        return False
    
    try:
        tools = client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools[:5]:  # Show first 5 tools
            print(f"  - {tool.name}: {tool.description[:50]}...")
        if len(tools) > 5:
            print(f"  ... and {len(tools) - 5} more tools")
        client.disconnect()
        return True
    except Exception as e:
        print(f"❌ Error listing tools: {e}")
        client.disconnect()
        return False

def test_authentication_flow():
    """Test authentication and login flow."""
    print("\n=== Testing Authentication Flow ===")
    client = MCPClient()
    
    if not client.connect():
        print("❌ Failed to connect")
        return False
    
    try:
        # Test setting credentials
        print("Testing credential setting...")
        result = client.set_credentials(
            username="test_user",
            password="test_password",
            api_key="test_api_key"
        )
        print(f"Set credentials result: {result}")
        
        # Test login process
        print("Testing login process...")
        login_result = client.perform_login()
        print(f"Login result: {login_result}")
        
        client.disconnect()
        return True
    except Exception as e:
        print(f"❌ Error in authentication flow: {e}")
        client.disconnect()
        return False

def test_query_processing():
    """Test query processing with function calling."""
    print("\n=== Testing Query Processing ===")
    client = MCPClient()
    
    if not client.connect():
        print("❌ Failed to connect")
        return False
    
    try:
        # Test a simple query
        query = "What tools are available?"
        print(f"Processing query: '{query}'")
        
        result = client.process_query(query)
        print(f"✅ Query processed successfully")
        print(f"Status: {result['status']}")
        print(f"Summary: {result['summary'][:100]}...")
        
        client.disconnect()
        return True
    except Exception as e:
        print(f"❌ Error processing query: {e}")
        client.disconnect()
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Final MCP Client")
    print("============================")
    print("Make sure the MCP server is running:")
    print("  python mcp_server.py --transport http --port 8000")
    print()
    
    tests = [
        ("Connection Test", test_connection),
        ("Tool Listing Test", test_list_tools),
        ("Authentication Flow Test", test_authentication_flow),
        ("Query Processing Test", test_query_processing)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n=== Test Results ===")
    passed = 0
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! The final MCP client is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the server and try again.")

if __name__ == "__main__":
    main()