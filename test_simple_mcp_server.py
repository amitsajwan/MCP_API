#!/usr/bin/env python3
"""
Test Simple MCP Server
Verifies that the simplified MCP server works correctly.
"""

import json
import requests
import asyncio
from simple_mcp_server import SimpleMCPServer


def test_http_server():
    """Test the HTTP server functionality."""
    print("🧪 Testing Simple MCP Server HTTP functionality...")
    
    base_url = "http://localhost:8001/mcp"
    
    # Test tools/list
    print("\n1. Testing tools/list...")
    list_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        response = requests.post(base_url, json=list_request, timeout=10)
        if response.status_code == 200:
            result = response.json()
            tools = result.get('result', {}).get('tools', [])
            print(f"✅ Found {len(tools)} tools")
            
            # Show some example tools
            auth_tools = [t for t in tools if t['name'] in ['set_credentials', 'perform_login']]
            api_tools = [t for t in tools if t['name'] not in ['set_credentials', 'perform_login']][:3]
            
            print("\n📋 Authentication tools:")
            for tool in auth_tools:
                print(f"  - {tool['name']}: {tool['description'][:60]}...")
            
            print("\n📋 Sample API tools:")
            for tool in api_tools:
                print(f"  - {tool['name']}: {tool['description'][:60]}...")
                
        else:
            print(f"❌ Failed to list tools: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing tools/list: {e}")
        return False
    
    # Test set_credentials
    print("\n2. Testing set_credentials...")
    cred_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "set_credentials",
            "arguments": {
                "username": "test_user",
                "password": "test_pass",
                "login_url": "http://localhost:8080/auth/login"
            }
        }
    }
    
    try:
        response = requests.post(base_url, json=cred_request, timeout=10)
        if response.status_code == 200:
            result = response.json()
            content = result.get('result', {}).get('content', [])
            if content:
                cred_result = json.loads(content[0]['text'])
                if cred_result.get('status') == 'success':
                    print(f"✅ Credentials set successfully for user: {cred_result.get('username')}")
                else:
                    print(f"❌ Failed to set credentials: {cred_result.get('message')}")
                    return False
        else:
            print(f"❌ Failed to set credentials: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing set_credentials: {e}")
        return False
    
    print("\n✅ All HTTP tests passed!")
    return True


async def test_direct_server():
    """Test the server directly without HTTP."""
    print("\n🧪 Testing Simple MCP Server directly...")
    
    try:
        server = SimpleMCPServer()
        
        # Test that tools are loaded
        print(f"✅ Server initialized with {len(server.api_tools)} API tools from {len(server.api_specs)} specs")
        
        # Show loaded specs
        print("\n📋 Loaded API specs:")
        for spec_name, spec in server.api_specs.items():
            print(f"  - {spec_name}: {spec.base_url}")
        
        # Show some tools
        sample_tools = list(server.api_tools.items())[:5]
        print("\n📋 Sample tools:")
        for tool_name, tool in sample_tools:
            print(f"  - {tool_name}: {tool.method} {tool.path}")
        
        print("\n✅ Direct server test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing direct server: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Simple MCP Server Tests")
    print("=" * 50)
    
    # Test direct server
    direct_success = asyncio.run(test_direct_server())
    
    # Test HTTP server (assumes it's running on port 8001)
    http_success = test_http_server()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  Direct Server: {'✅ PASS' if direct_success else '❌ FAIL'}")
    print(f"  HTTP Server:   {'✅ PASS' if http_success else '❌ FAIL'}")
    
    if direct_success and http_success:
        print("\n🎉 All tests passed! Simple MCP Server is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)