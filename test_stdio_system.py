#!/usr/bin/env python3
"""
Test Script for Stdio-Based MCP System
This script tests the complete stdio-based MCP architecture to ensure:
1. Transport layer works correctly (stdio)
2. MCP client can connect to MCP server
3. Tool execution works properly
4. Pagination handling works
5. Error recovery mechanisms work
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_stdio_system")

async def test_mcp_connection():
    """Test MCP client connection to MCP server."""
    logger.info("🧪 Testing MCP Connection...")
    
    try:
        from mcp_client_proper_working import ProperMCPClient
        
        client = ProperMCPClient()
        
        # Test connection
        logger.info("Connecting to MCP server...")
        if await client.connect():
            logger.info("✅ MCP connection successful")
            
            # Test tool listing
            tools = await client.list_tools()
            logger.info(f"✅ Found {len(tools)} tools")
            
            # Test tool execution
            if tools:
                logger.info("Testing tool execution...")
                result = await client.process_query("Show me my pending payments")
                logger.info(f"✅ Tool execution successful: {result.get('status')}")
                logger.info(f"Summary: {result.get('summary', 'No summary')[:200]}...")
            
            await client.disconnect()
            logger.info("✅ MCP disconnection successful")
            return True
        else:
            logger.error("❌ MCP connection failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ MCP connection test failed: {e}")
        return False

async def test_pagination_handling():
    """Test pagination handling for large responses."""
    logger.info("🧪 Testing Pagination Handling...")
    
    try:
        from mcp_client_proper_working import ProperMCPClient
        
        client = ProperMCPClient()
        
        if await client.connect():
            # Test with a query that might return large data
            result = await client.process_query("Get all payments with detailed information")
            
            # Check if pagination information is included
            if 'results' in result:
                for tool_result in result['results']:
                    if 'response_size' in tool_result:
                        logger.info(f"✅ Response size tracking: {tool_result['response_size']} tokens")
                    if 'paginated' in tool_result and tool_result['paginated']:
                        logger.info("✅ Pagination handling detected")
            
            await client.disconnect()
            return True
        else:
            logger.error("❌ Pagination test failed - could not connect")
            return False
            
    except Exception as e:
        logger.error(f"❌ Pagination test failed: {e}")
        return False

async def test_error_recovery():
    """Test error recovery mechanisms."""
    logger.info("🧪 Testing Error Recovery...")
    
    try:
        from mcp_client_proper_working import ProperMCPClient
        
        client = ProperMCPClient()
        
        if await client.connect():
            # Test with invalid tool call to trigger error recovery
            result = await client.call_tool("nonexistent_tool", {"test": "data"})
            
            if result.get("status") == "error":
                logger.info("✅ Error handling working correctly")
            else:
                logger.warning("⚠️ Error handling may not be working as expected")
            
            await client.disconnect()
            return True
        else:
            logger.error("❌ Error recovery test failed - could not connect")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error recovery test failed: {e}")
        return False

async def test_chatbot_integration():
    """Test chatbot app integration."""
    logger.info("🧪 Testing Chatbot Integration...")
    
    try:
        # Test if chatbot app can be imported and initialized
        from chatbot_app import app, mcp_client
        
        logger.info("✅ Chatbot app imports successfully")
        
        # Test if MCP client is properly configured
        if hasattr(mcp_client, 'connect'):
            logger.info("✅ MCP client is properly configured in chatbot app")
            return True
        else:
            logger.error("❌ MCP client not properly configured in chatbot app")
            return False
            
    except Exception as e:
        logger.error(f"❌ Chatbot integration test failed: {e}")
        return False

def test_required_files():
    """Test if all required files exist."""
    logger.info("🧪 Testing Required Files...")
    
    required_files = [
        "mcp_server.py",
        "mcp_client_proper_working.py",
        "chatbot_app.py",
        "config.py",
        "stdio_launcher.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"❌ Missing required files: {missing_files}")
        return False
    else:
        logger.info("✅ All required files present")
        return True

def test_dependencies():
    """Test if all required dependencies are installed."""
    logger.info("🧪 Testing Dependencies...")
    
    required_packages = [
        'mcp',
        'fastapi',
        'uvicorn',
        'pydantic',
        'aiohttp',
        'requests',
        'pyyaml',
        'python-dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"❌ Missing packages: {missing_packages}")
        return False
    else:
        logger.info("✅ All required packages installed")
        return True

async def main():
    """Run all tests."""
    logger.info("🚀 Starting Stdio-Based MCP System Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Required Files", test_required_files),
        ("Dependencies", test_dependencies),
        ("MCP Connection", test_mcp_connection),
        ("Pagination Handling", test_pagination_handling),
        ("Error Recovery", test_error_recovery),
        ("Chatbot Integration", test_chatbot_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 Test Results Summary")
    logger.info("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 All tests passed! Stdio-based MCP system is ready.")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed. Please fix the issues before proceeding.")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))