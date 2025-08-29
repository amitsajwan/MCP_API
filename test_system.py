#!/usr/bin/env python3
"""
Test System - Simple Test Script
Tests the MCP API system components.
"""

import asyncio
import json
import sys
from pathlib import Path

from config import config
from mcp_client import MCPClient


async def test_configuration():
    """Test configuration loading."""
    print("🔧 Testing Configuration...")
    
    if not config.validate():
        print("❌ Configuration validation failed")
        return False
    
    print("✅ Configuration is valid")
    print(f"   MCP Server: {config.get_mcp_url()}")
    print(f"   Chatbot: {config.get_chatbot_url()}")
    print(f"   Mock API: {config.get_mock_url()}")
    return True


async def test_mcp_client():
    """Test MCP client functionality."""
    print("\n🔌 Testing MCP Client...")
    
    client = MCPClient()
    
    try:
        # Test tool listing
        tools = await client.list_tools()
        print(f"✅ Found {len(tools)} tools")
        
        if tools:
            print("   Sample tools:")
            for tool in tools[:3]:  # Show first 3 tools
                print(f"     - {tool['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP client test failed: {e}")
        return False
    finally:
        await client.close()


async def test_chatbot_api():
    """Test chatbot API endpoints."""
    print("\n🌐 Testing Chatbot API...")
    
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test status endpoint
            async with session.get(f"{config.get_chatbot_url()}/status") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print("✅ Status endpoint working")
                    print(f"   Status: {data.get('status')}")
                else:
                    print(f"❌ Status endpoint failed: HTTP {resp.status}")
                    return False
            
            # Test tools endpoint
            async with session.get(f"{config.get_chatbot_url()}/tools") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Tools endpoint working ({len(data.get('tools', []))} tools)")
                else:
                    print(f"❌ Tools endpoint failed: HTTP {resp.status}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Chatbot API test failed: {e}")
        return False


async def test_mock_api():
    """Test mock API server."""
    print("\n🎭 Testing Mock API...")
    
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test root endpoint
            async with session.get(f"{config.get_mock_url()}/") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print("✅ Mock API root endpoint working")
                    print(f"   Version: {data.get('version')}")
                else:
                    print(f"❌ Mock API root endpoint failed: HTTP {resp.status}")
                    return False
            
            # Test accounts endpoint
            async with session.get(f"{config.get_mock_url()}/accounts") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Mock API accounts endpoint working ({data.get('total')} accounts)")
                else:
                    print(f"❌ Mock API accounts endpoint failed: HTTP {resp.status}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Mock API test failed: {e}")
        return False


async def test_openapi_specs():
    """Test OpenAPI specifications."""
    print("\n📋 Testing OpenAPI Specifications...")
    
    openapi_dir = Path(config.OPENAPI_DIR)
    if not openapi_dir.exists():
        print(f"❌ OpenAPI directory not found: {openapi_dir}")
        return False
    
    spec_files = list(openapi_dir.glob("*.yaml"))
    if not spec_files:
        print(f"❌ No YAML files found in {openapi_dir}")
        return False
    
    print(f"✅ Found {len(spec_files)} OpenAPI specification(s):")
    for spec_file in spec_files:
        print(f"   - {spec_file.name}")
    
    return True


async def run_all_tests():
    """Run all tests."""
    print("🧪 Running System Tests")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("OpenAPI Specs", test_openapi_specs),
        ("Mock API", test_mock_api),
        ("Chatbot API", test_chatbot_api),
        ("MCP Client", test_mcp_client),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the configuration and running services.")
        return False


def main():
    """Main entry point."""
    try:
        result = asyncio.run(run_all_tests())
        return 0 if result else 1
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
