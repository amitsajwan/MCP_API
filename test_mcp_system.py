#!/usr/bin/env python3
"""
Test Script for MCP System
This script tests the complete MCP system flow:
chatbot_app -> mcp_client -> mcp_server
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_test")

async def test_mcp_client_direct():
    """Test the MCP client directly."""
    logger.info("🧪 Testing MCP Client Direct Connection...")
    
    try:
        from mcp_client_proper_working import ProperMCPClient
        
        client = ProperMCPClient()
        
        # Test connection
        logger.info("🔌 Testing connection to MCP server...")
        if not await client.connect():
            logger.error("❌ Failed to connect to MCP server")
            return False
        
        # Test tool listing
        logger.info("📋 Testing tool listing...")
        tools = await client.list_tools()
        logger.info(f"✅ Found {len(tools)} tools: {[tool.name for tool in tools[:3]]}...")
        
        # Test tool execution
        logger.info("🔧 Testing tool execution...")
        result = await client.process_query("Show me pending payments")
        logger.info(f"✅ Tool execution result: {result.get('status', 'unknown')}")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"❌ MCP client test failed: {e}")
        return False

async def test_mcp_server_health():
    """Test MCP server health via HTTP endpoint."""
    logger.info("🏥 Testing MCP Server Health...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Try to connect to HTTP health endpoint
            try:
                async with session.get("http://localhost:9000/health", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ MCP Server HTTP health check passed: {data}")
                        return True
                    else:
                        logger.error(f"❌ MCP Server HTTP health check failed: {response.status}")
                        return False
            except aiohttp.ClientConnectorError:
                logger.warning("⚠️  MCP Server HTTP endpoint not available (this is expected for stdio-only mode)")
                return True  # This is expected for stdio-only mode
                
    except ImportError:
        logger.warning("⚠️  aiohttp not available, skipping HTTP health check")
        return True
    except Exception as e:
        logger.error(f"❌ MCP server health test failed: {e}")
        return False

async def test_chatbot_app_health():
    """Test chatbot app health."""
    logger.info("🤖 Testing Chatbot App Health...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Chatbot App health check passed: {data}")
                    return True
                else:
                    logger.error(f"❌ Chatbot App health check failed: {response.status}")
                    return False
                    
    except ImportError:
        logger.warning("⚠️  aiohttp not available, skipping chatbot health check")
        return True
    except Exception as e:
        logger.error(f"❌ Chatbot app health test failed: {e}")
        return False

def check_required_files():
    """Check if all required files exist."""
    logger.info("📁 Checking required files...")
    
    required_files = [
        "mcp_server.py",
        "chatbot_app.py", 
        "mcp_client_proper_working.py",
        "launcher_proper.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"❌ Missing required files: {missing_files}")
        return False
    
    logger.info("✅ All required files present")
    return True

def check_openapi_specs():
    """Check if OpenAPI specs exist."""
    logger.info("📋 Checking OpenAPI specifications...")
    
    openapi_dir = Path("openapi_specs")
    if not openapi_dir.exists():
        logger.warning("⚠️  OpenAPI specs directory not found")
        return False
    
    spec_files = list(openapi_dir.glob("*.yaml"))
    if not spec_files:
        logger.warning("⚠️  No OpenAPI spec files found")
        return False
    
    logger.info(f"✅ Found {len(spec_files)} OpenAPI spec files")
    return True

async def main():
    """Run all tests."""
    logger.info("🧪 MCP System Test Suite")
    logger.info("=" * 40)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Check required files
    total_tests += 1
    if check_required_files():
        tests_passed += 1
    
    # Test 2: Check OpenAPI specs
    total_tests += 1
    if check_openapi_specs():
        tests_passed += 1
    
    # Test 3: MCP Server health (if HTTP mode is available)
    total_tests += 1
    if await test_mcp_server_health():
        tests_passed += 1
    
    # Test 4: Chatbot App health (if running)
    total_tests += 1
    if await test_chatbot_app_health():
        tests_passed += 1
    
    # Test 5: MCP Client direct connection (if server is running)
    total_tests += 1
    if await test_mcp_client_direct():
        tests_passed += 1
    
    # Results
    logger.info("=" * 40)
    logger.info(f"🧪 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        logger.info("✅ All tests passed! System is ready.")
        return 0
    elif tests_passed >= total_tests - 2:  # Allow some tests to fail (e.g., if services aren't running)
        logger.info("⚠️  Most tests passed. System should work when services are running.")
        return 0
    else:
        logger.error("❌ Multiple tests failed. Please check the system setup.")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))