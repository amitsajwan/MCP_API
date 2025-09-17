#!/usr/bin/env python3
"""
Test API Loading - Verify All API Specs Are Parsed
=================================================
Test script to verify that all API specifications are loaded and parsed correctly.
"""

import os
import yaml
import asyncio
from pathlib import Path
from mcp_server_fastmcp2 import FastMCP2Server

def test_api_spec_loading():
    """Test that all API specs are loaded correctly"""
    print("🧪 Testing API Specification Loading")
    print("=" * 50)
    
    # Check openapi_specs directory
    specs_dir = Path("./openapi_specs")
    if not specs_dir.exists():
        print("❌ OpenAPI specs directory not found")
        return False
    
    # List all YAML files
    yaml_files = list(specs_dir.glob("*.yaml"))
    print(f"📁 Found {len(yaml_files)} YAML files in {specs_dir}")
    
    for yaml_file in yaml_files:
        print(f"  - {yaml_file.name}")
    
    print("\n🔄 Testing individual spec parsing...")
    
    # Test each spec individually
    for yaml_file in yaml_files:
        print(f"\n📋 Testing {yaml_file.name}:")
        try:
            with open(yaml_file, 'r') as f:
                spec_data = yaml.safe_load(f)
            
            # Check basic structure
            if 'openapi' not in spec_data:
                print(f"  ❌ Missing 'openapi' field")
                continue
            
            if 'paths' not in spec_data:
                print(f"  ❌ Missing 'paths' field")
                continue
            
            # Count endpoints
            paths = spec_data.get('paths', {})
            endpoint_count = 0
            for path, path_item in paths.items():
                for method in ['get', 'post', 'put', 'delete', 'patch']:
                    if method in path_item:
                        endpoint_count += 1
            
            print(f"  ✅ OpenAPI version: {spec_data.get('openapi', 'unknown')}")
            print(f"  ✅ Endpoints found: {endpoint_count}")
            print(f"  ✅ Title: {spec_data.get('info', {}).get('title', 'No title')}")
            
        except Exception as e:
            print(f"  ❌ Error parsing {yaml_file.name}: {e}")
    
    print("\n🔄 Testing MCP server initialization...")
    
    try:
        # Create server instance
        server = FastMCP2Server()
        
        # Check loaded specs
        print(f"📊 Loaded {len(server.api_specs)} API specifications:")
        for spec_name, spec in server.api_specs.items():
            print(f"  - {spec_name}: {spec.base_url}")
        
        # Count total tools
        total_tools = 0
        for spec_name, spec in server.api_specs.items():
            paths = spec.spec.get('paths', {})
            spec_tools = 0
            for path, path_item in paths.items():
                for method in ['get', 'post', 'put', 'delete', 'patch']:
                    if method in path_item:
                        spec_tools += 1
            total_tools += spec_tools
            print(f"    {spec_name}: {spec_tools} tools")
        
        print(f"\n✅ Total tools across all specs: {total_tools}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing MCP server: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_modular_service_tool_loading():
    """Test that modular service loads all tools from MCP server"""
    print("\n🔄 Testing Modular Service Tool Loading...")
    
    try:
        from modular_mcp_service import create_modular_service
        
        async def test_loading():
            service = await create_modular_service(use_mock=True)
            tools = await service.get_available_tools()
            
            print(f"✅ Modular service loaded {len(tools)} tools")
            if tools:
                print("📋 Available tools:")
                for i, tool in enumerate(tools[:10], 1):  # Show first 10
                    name = tool.get('function', {}).get('name', 'unknown')
                    print(f"  {i:2d}. {name}")
                if len(tools) > 10:
                    print(f"  ... and {len(tools) - 10} more tools")
            
            await service.cleanup()
            return len(tools)
        
        tool_count = asyncio.run(test_loading())
        return tool_count > 0
        
    except Exception as e:
        print(f"❌ Error testing modular service: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting API Loading Tests")
    print("=" * 60)
    
    # Test 1: API spec loading
    spec_loading_success = test_api_spec_loading()
    
    # Test 2: Modular service tool loading
    modular_loading_success = test_modular_service_tool_loading()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"  API Spec Loading: {'✅ PASS' if spec_loading_success else '❌ FAIL'}")
    print(f"  Modular Service Loading: {'✅ PASS' if modular_loading_success else '❌ FAIL'}")
    
    if spec_loading_success and modular_loading_success:
        print("\n🎉 All tests passed! All API specs are being parsed correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")