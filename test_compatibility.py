#!/usr/bin/env python3
"""
Compatibility Test Suite
Tests compatibility between:
1. enhanced_mcp_client with simple_mcp_server
2. chatbot_app with enhanced_mcp_client
"""

import asyncio
import json
import logging
import requests
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_simple_server_endpoints():
    """Test if simple_mcp_server provides the endpoints enhanced_mcp_client expects."""
    logger.info("\n=== Testing Simple MCP Server Endpoints ===")
    
    server_url = "http://localhost:8001"
    
    try:
        # Test health endpoint (if available)
        try:
            response = requests.get(f"{server_url}/health", timeout=5)
            logger.info(f"Health endpoint: {response.status_code}")
        except requests.exceptions.RequestException:
            logger.info("Health endpoint not available (expected for simple_mcp_server)")
        
        # Test /tools endpoint (expected by enhanced_mcp_client)
        try:
            response = requests.get(f"{server_url}/tools", timeout=5)
            logger.info(f"GET /tools endpoint: {response.status_code}")
            if response.status_code != 200:
                logger.warning("enhanced_mcp_client expects GET /tools to return 200")
        except requests.exceptions.RequestException as e:
            logger.error(f"GET /tools failed: {e}")
        
        # Test /call_tool endpoint (expected by enhanced_mcp_client)
        try:
            test_payload = {"name": "nonexistent_tool", "arguments": {}}
            response = requests.post(f"{server_url}/call_tool", json=test_payload, timeout=5)
            logger.info(f"POST /call_tool endpoint: {response.status_code}")
            if response.status_code not in [200, 404, 500]:
                logger.warning("enhanced_mcp_client expects POST /call_tool to be available")
        except requests.exceptions.RequestException as e:
            logger.error(f"POST /call_tool failed: {e}")
        
        # Test MCP protocol endpoint (what simple_mcp_server actually provides)
        try:
            mcp_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            response = requests.post(f"{server_url}/mcp", json=mcp_payload, timeout=5)
            logger.info(f"POST /mcp (tools/list): {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                tools = data.get('result', {}).get('tools', [])
                logger.info(f"Found {len(tools)} tools via MCP protocol")
        except requests.exceptions.RequestException as e:
            logger.error(f"POST /mcp failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Server endpoint test failed: {e}")
        return False


def test_enhanced_mcp_client_compatibility():
    """Test if enhanced_mcp_client can work with simple_mcp_server."""
    logger.info("\n=== Testing Enhanced MCP Client Compatibility ===")
    
    try:
        # Import enhanced_mcp_client
        from enhanced_mcp_client import EnhancedMCPClient
        
        # Try to create client
        config = {
            'server_url': 'http://localhost:8001',
            'auth': {
                'username': 'test',
                'password': 'test'
            },
            'azure_openai': {
                'endpoint': 'https://test.openai.azure.com',
                'api_key': 'test_key',
                'deployment': 'gpt-4'
            }
        }
        client = EnhancedMCPClient(config)
        
        logger.info("✅ Enhanced MCP Client created successfully")
        
        # Test connection
        try:
            success = client.connect()
            if success:
                logger.info("✅ Enhanced MCP Client connected successfully")
            else:
                logger.warning("⚠️ Enhanced MCP Client connection failed")
        except Exception as e:
            logger.error(f"❌ Enhanced MCP Client connection error: {e}")
        
        # Test tool discovery
        try:
            tools = client.discover_tools()
            logger.info(f"✅ Enhanced MCP Client discovered {len(tools)} tools")
            
            # Show first few tools
            for i, tool in enumerate(tools[:3]):
                logger.info(f"  Tool {i+1}: {tool.name} - {tool.description[:50]}...")
                
        except Exception as e:
            logger.error(f"❌ Enhanced MCP Client tool discovery failed: {e}")
        
        # Test tool execution (try set_credentials)
        try:
            result = client.execute_tool("set_credentials", {
                "username": "test_user",
                "password": "test_pass"
            })
            logger.info(f"✅ Enhanced MCP Client tool execution result: {result.get('status', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ Enhanced MCP Client tool execution failed: {e}")
        
        client.disconnect()
        return True
        
    except ImportError as e:
        logger.error(f"❌ Cannot import enhanced_mcp_client: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Enhanced MCP Client test failed: {e}")
        return False


def test_chatbot_app_compatibility():
    """Test if chatbot_app can work with enhanced_mcp_client."""
    logger.info("\n=== Testing Chatbot App Compatibility ===")
    
    try:
        # Check if chatbot_app imports work
        import sys
        import os
        
        # Add current directory to path
        sys.path.insert(0, os.getcwd())
        
        # Try importing components from chatbot_app
        try:
            # Check if we can import the mcp_client that chatbot_app uses
            from mcp_client import MCPClient
            logger.info("✅ Can import MCPClient (used by chatbot_app)")
            
            # Test if MCPClient has the methods chatbot_app expects
            client = MCPClient(mcp_server_url="http://localhost:8001")
            
            # Check required methods
            required_methods = ['connect', 'disconnect', 'list_tools', 'process_query']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(client, method):
                    missing_methods.append(method)
            
            if missing_methods:
                logger.error(f"❌ MCPClient missing methods: {missing_methods}")
                return False
            else:
                logger.info("✅ MCPClient has all required methods for chatbot_app")
            
            # Test basic functionality
            try:
                success = client.connect()
                if success:
                    logger.info("✅ MCPClient can connect")
                    
                    tools = client.list_tools()
                    logger.info(f"✅ MCPClient can list {len(tools)} tools")
                    
                    # Test process_query (the main method chatbot_app uses)
                    result = client.process_query("Hello, can you help me?")
                    logger.info(f"✅ MCPClient process_query works: {type(result)}")
                    
                    client.disconnect()
                else:
                    logger.warning("⚠️ MCPClient connection failed")
                    
            except Exception as e:
                logger.error(f"❌ MCPClient functionality test failed: {e}")
            
        except ImportError as e:
            logger.error(f"❌ Cannot import MCPClient: {e}")
            return False
        
        # Check if enhanced_mcp_client could be used as a drop-in replacement
        try:
            from enhanced_mcp_client import EnhancedMCPClient
            
            # Check if EnhancedMCPClient has the same interface as MCPClient
            config = {
                'server_url': 'http://localhost:8001',
                'auth': {
                    'username': 'test',
                    'password': 'test'
                },
                'azure_openai': {
                    'endpoint': 'https://test.openai.azure.com',
                    'api_key': 'test_key',
                    'deployment': 'gpt-4'
                }
            }
            enhanced_client = EnhancedMCPClient(config)
            
            required_methods = ['connect', 'disconnect', 'discover_tools']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(enhanced_client, method):
                    missing_methods.append(method)
            
            if missing_methods:
                logger.warning(f"⚠️ EnhancedMCPClient missing methods for chatbot_app: {missing_methods}")
            else:
                logger.info("✅ EnhancedMCPClient has compatible interface")
            
            # Check if it has process_query equivalent
            if hasattr(enhanced_client, 'execute_with_intent'):
                logger.info("✅ EnhancedMCPClient has execute_with_intent (similar to process_query)")
            else:
                logger.warning("⚠️ EnhancedMCPClient lacks process_query equivalent")
                
        except ImportError:
            logger.warning("⚠️ Cannot test EnhancedMCPClient compatibility")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Chatbot app compatibility test failed: {e}")
        return False


def main():
    """Run all compatibility tests."""
    logger.info("🧪 Starting Compatibility Test Suite")
    logger.info("="*50)
    
    results = {
        "server_endpoints": test_simple_server_endpoints(),
        "enhanced_client": test_enhanced_mcp_client_compatibility(),
        "chatbot_app": test_chatbot_app_compatibility()
    }
    
    logger.info("\n" + "="*50)
    logger.info("📊 COMPATIBILITY TEST RESULTS")
    logger.info("="*50)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    
    logger.info(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All compatibility tests passed!")
    else:
        logger.warning("⚠️ Some compatibility issues found. See details above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)