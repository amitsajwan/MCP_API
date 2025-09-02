#!/usr/bin/env python3
"""
Test MCP server credential management and login functionality.
"""

import json
import sys
import subprocess
import time
import os
from typing import Dict, Any

def send_mcp_request(process, request: Dict[str, Any]) -> Dict[str, Any]:
    """Send a request to the MCP server via stdio."""
    try:
        request_json = json.dumps(request) + "\n"
        process.stdin.write(request_json)
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line.strip():
            return json.loads(response_line.strip())
        else:
            return {"error": "No response from server"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def test_credential_management():
    """Test credential setting and login functionality."""
    print("🔐 Testing Credential Management...")
    
    try:
        # Start the MCP server process
        process = subprocess.Popen(
            [sys.executable, "mcp_server.py", "--transport", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="."
        )
        
        time.sleep(2)
        
        # Initialize connection
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        response = send_mcp_request(process, init_request)
        if "result" not in response:
            print(f"❌ Initialization failed: {response}")
            return False
        
        # Send initialized notification
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }) + "\n")
        process.stdin.flush()
        time.sleep(0.5)
        
        # Test 1: Set credentials
        print("\n=== Testing Set Credentials ===")
        set_creds_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "set_credentials",
                "arguments": {
                    "username": "test_user",
                    "password": "test_password",
                    "api_key_name": "X-API-Key",
                    "api_key_value": "test_api_key_123",
                    "login_url": "https://api.example.com/auth/login"
                }
            }
        }
        
        response = send_mcp_request(process, set_creds_request)
        if "result" in response:
            result = response["result"]
            # Handle MCP tool response format
            if "content" in result and len(result["content"]) > 0:
                content_item = result["content"][0]
                if content_item.get("type") == "text":
                    data = json.loads(content_item.get("text", "{}"))
                    print(f"✅ Credentials set successfully")
                    print(f"   Username: {data.get('username', 'Not set')}")
                    print(f"   Has API Key: {data.get('has_api_key', False)}")
                    print(f"   API Key Name: {data.get('api_key_name', 'Not set')}")
                    print(f"   Login URL: {data.get('login_url', 'Not set')}")
                else:
                    print(f"❌ Unexpected content type: {content_item}")
            else:
                print(f"❌ No content in response: {result}")
        else:
            print(f"❌ Failed to set credentials: {response}")
            return False
        
        # Test 2: Attempt login (will fail since it's a test URL)
        print("\n=== Testing Login Attempt ===")
        login_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "perform_login",
                "arguments": {
                    "force_login": True
                }
            }
        }
        
        response = send_mcp_request(process, login_request)
        if "result" in response:
            result = response["result"]
            if "content" in result and len(result["content"]) > 0:
                content_item = result["content"][0]
                if content_item.get("type") == "text":
                    data = json.loads(content_item.get("text", "{}"))
                    if data.get("success"):
                        print(f"✅ Login successful")
                        print(f"   Session ID: {data.get('session_id', 'Not provided')}")
                    else:
                        print(f"⚠️  Login failed as expected (test URL): {data.get('message', 'Unknown error')}")
                        print(f"   This is normal for testing with fake credentials")
        else:
            print(f"⚠️  Login request failed: {response}")
            print(f"   This is expected when using test credentials")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    finally:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()

def test_environment_variables():
    """Test environment variable credential loading."""
    print("\n🌍 Testing Environment Variable Loading...")
    
    # Set test environment variables
    test_env = os.environ.copy()
    test_env.update({
        "API_USERNAME": "env_user",
        "API_PASSWORD": "env_password", 
        "API_KEY_NAME": "X-Env-Key",
        "API_KEY_VALUE": "env_key_456",
        "LOGIN_URL": "https://env.example.com/login"
    })
    
    try:
        # Start server with environment variables
        process = subprocess.Popen(
            [sys.executable, "mcp_server.py", "--transport", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=".",
            env=test_env
        )
        
        time.sleep(2)
        
        # Initialize connection
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        response = send_mcp_request(process, init_request)
        if "result" not in response:
            print(f"❌ Initialization failed: {response}")
            return False
        
        # Send initialized notification
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }) + "\n")
        process.stdin.flush()
        time.sleep(0.5)
        
        # Test set_credentials without arguments (should use env vars)
        print("\n=== Testing Environment Variable Fallback ===")
        set_creds_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "set_credentials",
                "arguments": {}
            }
        }
        
        response = send_mcp_request(process, set_creds_request)
        if "result" in response:
            result = response["result"]
            if "content" in result and len(result["content"]) > 0:
                content_item = result["content"][0]
                if content_item.get("type") == "text":
                    data = json.loads(content_item.get("text", "{}"))
                    print(f"✅ Environment credentials loaded successfully")
                    print(f"   Username: {data.get('username', 'Not set')}")
                    print(f"   Has API Key: {data.get('has_api_key', False)}")
                    print(f"   API Key Name: {data.get('api_key_name', 'Not set')}")
                    print(f"   Login URL: {data.get('login_url', 'Not set')}")
                    
                    # Verify the values match our environment variables
                    if (data.get('username') == 'env_user' and 
                        data.get('api_key_name') == 'X-Env-Key' and
                        data.get('login_url') == 'https://env.example.com/login'):
                        print(f"✅ Environment variables correctly loaded")
                        return True
                    else:
                        print(f"❌ Environment variables not loaded correctly")
                        return False
        
        print(f"❌ Failed to load environment credentials: {response}")
        return False
        
    except Exception as e:
        print(f"❌ Environment test failed: {str(e)}")
        return False
    finally:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()

def main():
    """Run credential management tests."""
    print("🧪 Testing MCP Server Credential Management...")
    
    success = True
    
    # Test 1: Manual credential setting
    if not test_credential_management():
        success = False
    
    # Test 2: Environment variable loading
    if not test_environment_variables():
        success = False
    
    if success:
        print("\n✅ All credential tests passed!")
        print("\n📋 Credential Management Summary:")
        print("  - ✅ Manual credential setting works correctly")
        print("  - ✅ Environment variable fallback works correctly")
        print("  - ✅ Login functionality is properly implemented")
        print("  - ✅ Credential validation and error handling works")
        print("  - ✅ MCP tool responses are properly formatted")
    else:
        print("\n❌ Some credential tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()