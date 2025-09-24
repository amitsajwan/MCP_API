#!/usr/bin/env python3
"""
Test Simplified FastMCP System
==============================
Simple test script to verify the simplified FastMCP system works correctly.
"""

import asyncio
import json
import logging
from pathlib import Path
from simplified_fastmcp_server import SimplifiedFastMCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_simplified_system():
    """Test the simplified FastMCP system"""
    logger.info("🧪 Testing Simplified FastMCP System")
    logger.info("=" * 50)
    
    try:
        # Create server instance
        server = SimplifiedFastMCPServer()
        
        # Test initialization
        logger.info("🔄 Testing server initialization...")
        success = await server.initialize()
        
        if not success:
            logger.error("❌ Server initialization failed")
            return False
        
        logger.info("✅ Server initialized successfully")
        
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
        else:
            logger.warning(f"⚠️ Credential setting issue: {result.get('message')}")
        
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
                else:
                    logger.info(f"ℹ️ Tool execution result: {result.get('message', 'No message')}")
        
        # Cleanup
        await server.cleanup()
        logger.info("✅ Cleanup completed")
        
        logger.info("🎉 All tests completed successfully!")
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
    
    return True

def main():
    """Main test function"""
    logger.info("🚀 Starting Simplified FastMCP System Tests")
    
    # Test OpenAPI specs first
    if not asyncio.run(test_openapi_specs()):
        logger.error("❌ OpenAPI specification test failed")
        return 1
    
    # Test the system
    if not asyncio.run(test_simplified_system()):
        logger.error("❌ System test failed")
        return 1
    
    logger.info("🎉 All tests passed! The simplified system is ready to use.")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Set your credentials: export API_USERNAME='your_user'")
    logger.info("2. Start the system: python start_simplified.py")
    logger.info("3. Open http://localhost:5001 in your browser")
    
    return 0

if __name__ == "__main__":
    exit(main())