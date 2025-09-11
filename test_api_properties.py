#!/usr/bin/env python3
"""
Test script to verify API properties are added to MCP tools
"""

import asyncio
import json
import logging
from mcp_client_proper_working import ProperMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_api_properties")

async def test_api_properties():
    """Test that API properties are correctly added to tools."""
    print("🧪 Testing API Properties in MCP Tools")
    print("=" * 50)
    
    # Create MCP client
    client = ProperMCPClient()
    
    try:
        # Connect to MCP server
        print("🔗 Connecting to MCP server...")
        if not await client.connect():
            print("❌ Failed to connect to MCP server")
            return
        
        print("✅ Connected to MCP server")
        
        # List tools
        print("\n📋 Listing available tools...")
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools")
        
        # Check if tools have API properties
        print("\n🔍 Checking for API properties...")
        tools_with_api_props = 0
        
        for tool in tools:
            tool_name = tool.name
            print(f"\n🔧 Tool: {tool_name}")
            print(f"   Description: {tool.description}")
            
            # Check if tool has api_properties
            if hasattr(tool, 'api_properties'):
                tools_with_api_props += 1
                api_props = tool.api_properties
                print(f"   ✅ Has API properties:")
                print(f"      Method: {api_props.get('method', 'N/A')}")
                print(f"      Path: {api_props.get('path', 'N/A')}")
                print(f"      Category: {api_props.get('category', 'N/A')}")
                print(f"      Tags: {api_props.get('tags', [])}")
                print(f"      Parameters: {api_props.get('parameters_count', 0)}")
            else:
                print(f"   ❌ No API properties found")
            
            # Show input schema
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                schema = tool.inputSchema
                if 'properties' in schema:
                    print(f"   📝 Parameters: {len(schema['properties'])}")
                    for param_name, param_info in list(schema['properties'].items())[:3]:
                        param_type = param_info.get('type', 'any')
                        print(f"      - {param_name}: {param_type}")
                    if len(schema['properties']) > 3:
                        print(f"      ... and {len(schema['properties']) - 3} more")
        
        print(f"\n📊 Summary:")
        print(f"   Total tools: {len(tools)}")
        print(f"   Tools with API properties: {tools_with_api_props}")
        print(f"   Coverage: {tools_with_api_props/len(tools)*100:.1f}%" if tools else "   Coverage: N/A")
        
        # Test Azure 4o planning with enhanced tools
        if tools_with_api_props > 0:
            print(f"\n🤖 Testing Azure 4o planning with enhanced tools...")
            try:
                # Convert tools to dict format for Azure client
                available_tools = []
                for tool in tools:
                    tool_dict = {
                        'name': tool.name,
                        'description': tool.description,
                        'inputSchema': tool.inputSchema
                    }
                    # Add API properties if available
                    if hasattr(tool, 'api_properties'):
                        tool_dict['api_properties'] = tool.api_properties
                    available_tools.append(tool_dict)
                
                # Test Azure 4o planning
                from azure_openai_client import azure_client
                tool_calls = await azure_client.create_tool_plan("Show me my pending payments", available_tools)
                
                if tool_calls:
                    print(f"✅ Azure 4o created {len(tool_calls)} tool calls using enhanced tool descriptions")
                    for i, tool_call in enumerate(tool_calls, 1):
                        print(f"   {i}. {tool_call.tool_name}")
                        print(f"      Reason: {tool_call.reason}")
                else:
                    print("❌ Azure 4o returned no tool calls")
                    
            except Exception as e:
                print(f"❌ Azure 4o test failed: {e}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")
    
    finally:
        # Clean up
        await client.disconnect()
        print("\n👋 Test completed")

if __name__ == "__main__":
    asyncio.run(test_api_properties())