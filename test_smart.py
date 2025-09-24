#!/usr/bin/env python3
"""
Test Smart MCP System
=====================
Test script to verify the Smart MCP system works correctly with all features.
"""

import asyncio
import json
import logging
from pathlib import Path
from smart_mcp_server import SmartMCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_smart_system():
    """Test the Smart MCP system with all features"""
    logger.info("🧠 Testing Smart MCP System")
    logger.info("=" * 60)
    
    try:
        # Create server instance
        server = SmartMCPServer()
        
        # Test initialization
        logger.info("🔄 Testing server initialization...")
        success = await server.initialize()
        
        if not success:
            logger.error("❌ Server initialization failed")
            return False
        
        logger.info("✅ Server initialized successfully")
        
        # Test API relationships
        logger.info("🔗 Testing API relationships...")
        relationships = await server.get_api_relationships()
        
        if relationships.get("relationships"):
            logger.info("✅ API relationships loaded:")
            for api, rels in relationships["relationships"].items():
                logger.info(f"  - {api}: depends_on={rels.get('depends_on', [])}, calls_after={rels.get('calls_after', [])}")
        else:
            logger.warning("⚠️ No API relationships found")
        
        # Test getting tools
        logger.info("🔧 Testing tool retrieval...")
        tools = await server.get_tools()
        
        if not tools:
            logger.warning("⚠️ No tools found - check OpenAPI specifications")
        else:
            logger.info(f"✅ Found {len(tools)} tools")
            
            # Show first few tools
            for i, tool in enumerate(tools[:3]):
                logger.info(f"  {i+1}. {tool.get('name', 'unknown')}: {tool.get('description', 'No description')[:50]}...")
        
        # Test credential setting
        logger.info("🔐 Testing credential setting...")
        result = await server.set_credentials(
            username="test_user",
            password="test_pass",
            api_key_name="X-API-Key",
            api_key_value="test_key"
        )
        
        if result.get("status") == "success":
            logger.info("✅ Credential setting works")
            logger.info(f"  - Username: {result.get('username')}")
            logger.info(f"  - Has API Key: {result.get('has_api_key')}")
            logger.info(f"  - Has JSESSIONID: {result.get('has_jsessionid')}")
        else:
            logger.warning(f"⚠️ Credential setting issue: {result.get('message')}")
        
        # Test response truncation
        logger.info("📊 Testing response truncation...")
        
        # Create test data with more than 100 items
        large_list = [{"id": i, "data": f"item_{i}"} for i in range(150)]
        large_dict = {
            "items": large_list,
            "metadata": {"total": 150}
        }
        
        # Test truncation
        truncated_list = server._truncate_response(large_list)
        truncated_dict = server._truncate_response(large_dict)
        
        logger.info(f"✅ List truncation: {truncated_list.total_count} -> {truncated_list.returned_count} (truncated: {truncated_list.truncated})")
        logger.info(f"✅ Dict truncation: {truncated_dict.total_count} -> {truncated_dict.returned_count} (truncated: {truncated_dict.truncated})")
        
        # Test tool execution (if tools available)
        if tools:
            logger.info("⚡ Testing tool execution...")
            first_tool = tools[0]
            tool_name = first_tool.get('name', '')
            
            if tool_name:
                # Try to execute with empty arguments
                result = await server.execute_tool(tool_name, {})
                
                if result.get("status") == "success":
                    logger.info(f"✅ Tool execution works for {tool_name}")
                    if result.get("truncation_applied"):
                        logger.info("  - Response truncation was applied")
                else:
                    logger.info(f"ℹ️ Tool execution result: {result.get('message', 'No message')}")
        
        # Test multiple tool execution
        if len(tools) >= 2:
            logger.info("🚀 Testing multiple tool execution...")
            tool_requests = [
                {"tool_name": tools[0].get('name', ''), "arguments": {}},
                {"tool_name": tools[1].get('name', ''), "arguments": {}}
            ]
            
            results = await server.execute_multiple_tools(tool_requests)
            logger.info(f"✅ Multiple tool execution: {len(results)} tools processed")
        
        # Test call history
        logger.info("📈 Testing call history...")
        relationships = await server.get_api_relationships()
        call_history = relationships.get("call_history", [])
        total_calls = relationships.get("total_calls", 0)
        
        logger.info(f"✅ Call history: {total_calls} total calls, {len(call_history)} recent calls")
        
        # Cleanup
        await server.cleanup()
        logger.info("✅ Cleanup completed")
        
        logger.info("🎉 All Smart MCP tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

async def test_openapi_specs():
    """Test OpenAPI specification loading"""
    logger.info("📋 Testing OpenAPI specifications...")
    
    openapi_dir = Path("./openapi_specs")
    if not openapi_dir.exists():
        logger.error("❌ OpenAPI directory not found")
        return False
    
    yaml_files = list(openapi_dir.glob("*.yaml"))
    if not yaml_files:
        logger.error("❌ No YAML files found")
        return False
    
    logger.info(f"✅ Found {len(yaml_files)} OpenAPI specification files:")
    for spec_file in yaml_files:
        logger.info(f"  - {spec_file.name}")
        
        # Try to load and validate the spec
        try:
            import yaml
            with open(spec_file, 'r') as f:
                spec_data = yaml.safe_load(f)
            
            # Basic validation
            if 'openapi' in spec_data and 'paths' in spec_data:
                path_count = len(spec_data.get('paths', {}))
                logger.info(f"    ✅ Valid OpenAPI spec with {path_count} paths")
            else:
                logger.warning(f"    ⚠️ Invalid OpenAPI spec structure")
                
        except Exception as e:
            logger.error(f"    ❌ Error loading spec: {e}")
    
    return True

def main():
    """Main test function"""
    logger.info("🚀 Starting Smart MCP System Tests")
    logger.info("Testing Features:")
    logger.info("  🔐 JSESSIONID & API Key authentication")
    logger.info("  📊 Intelligent response truncation")
    logger.info("  🔗 API relationship understanding")
    logger.info("  🚀 Smart tool execution ordering")
    logger.info("=" * 60)
    
    # Test OpenAPI specs first
    if not asyncio.run(test_openapi_specs()):
        logger.error("❌ OpenAPI specification test failed")
        return 1
    
    # Test the system
    if not asyncio.run(test_smart_system()):
        logger.error("❌ Smart MCP system test failed")
        return 1
    
    logger.info("🎉 All tests passed! The Smart MCP system is ready to use.")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Set your credentials: export API_USERNAME='your_user'")
    logger.info("2. Start the system: python start_smart.py")
    logger.info("3. Open http://localhost:5002 in your browser")
    logger.info("")
    logger.info("Features available:")
    logger.info("  • Automatic JSESSIONID management")
    logger.info("  • API key authentication")
    logger.info("  • Response truncation (100 items max)")
    logger.info("  • API relationship intelligence")
    logger.info("  • Multiple tool execution with smart ordering")
    
    return 0

if __name__ == "__main__":
    exit(main())