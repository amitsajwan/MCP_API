#!/usr/bin/env python3
"""
Example MCP Client Usage
Demonstrates how to use the MCP Tool Client with various servers.
"""

import asyncio
import json
import logging
from mcp_tool_client import MCPToolClient, create_client, call_tool_simple, list_tools_simple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("example_usage")

async def example_chatbot_client():
    """Example using the FastMCP Chatbot Server."""
    print("🤖 Example: FastMCP Chatbot Server")
    print("=" * 40)
    
    try:
        # Create client for chatbot server
        async with MCPToolClient("fastmcp_chatbot_server.py") as client:
            # List available tools
            print("\n📋 Available tools:")
            tools = await client.list_tools()
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Example 1: Chat with the bot
            print("\n💬 Example 1: Chat with the bot")
            result = await client.call_tool("chat_with_user", {
                "message": "Hello! Can you help me with the weather?",
                "user_id": "example_user"
            })
            
            if result.success:
                print("✅ Chat response:")
                print(json.dumps(result.result, indent=2))
            else:
                print(f"❌ Chat failed: {result.error}")
            
            # Example 2: Get weather
            print("\n🌤️ Example 2: Get weather")
            result = await client.call_tool("get_weather", {
                "city": "New York",
                "units": "metric"
            })
            
            if result.success:
                print("✅ Weather response:")
                print(json.dumps(result.result, indent=2))
            else:
                print(f"❌ Weather failed: {result.error}")
            
            # Example 3: Calculate math
            print("\n🧮 Example 3: Calculate math")
            result = await client.call_tool("calculate_math", {
                "expression": "2 + 2 * 3"
            })
            
            if result.success:
                print("✅ Math result:")
                print(json.dumps(result.result, indent=2))
            else:
                print(f"❌ Math failed: {result.error}")
            
            # Example 4: Create a todo
            print("\n📝 Example 4: Create a todo")
            result = await client.call_tool("create_todo", {
                "title": "Learn MCP",
                "description": "Study Model Context Protocol",
                "priority": "high"
            })
            
            if result.success:
                print("✅ Todo created:")
                print(json.dumps(result.result, indent=2))
            else:
                print(f"❌ Todo creation failed: {result.error}")
    
    except Exception as e:
        logger.error(f"Error in chatbot example: {e}")

async def example_api_client():
    """Example using the FastMCP API Server."""
    print("\n🔌 Example: FastMCP API Server")
    print("=" * 40)
    
    try:
        # Create client for API server
        async with MCPToolClient("mcp_server_fastmcp.py") as client:
            # List available tools
            print("\n📋 Available tools:")
            tools = await client.list_tools()
            for tool in tools[:5]:  # Show first 5 tools
                print(f"  - {tool.name}: {tool.description}")
            
            if len(tools) > 5:
                print(f"  ... and {len(tools) - 5} more tools")
            
            # Example: Set credentials
            print("\n🔐 Example: Set credentials")
            result = await client.call_tool("set_credentials", {
                "username": "test_user",
                "password": "test_password",
                "login_url": "http://localhost:8080/auth/login"
            })
            
            if result.success:
                print("✅ Credentials set:")
                print(json.dumps(result.result, indent=2))
            else:
                print(f"❌ Credential setting failed: {result.error}")
            
            # Example: Perform login
            print("\n🔑 Example: Perform login")
            result = await client.call_tool("perform_login", {})
            
            if result.success:
                print("✅ Login successful:")
                print(json.dumps(result.result, indent=2))
            else:
                print(f"❌ Login failed: {result.error}")
    
    except Exception as e:
        logger.error(f"Error in API example: {e}")

async def example_simple_functions():
    """Example using simple convenience functions."""
    print("\n⚡ Example: Simple Functions")
    print("=" * 40)
    
    try:
        # List tools using simple function
        print("\n📋 Listing tools with simple function:")
        tools = await list_tools_simple("fastmcp_chatbot_server.py")
        for tool in tools[:3]:  # Show first 3 tools
            print(f"  - {tool.name}: {tool.description}")
        
        # Call tool using simple function
        print("\n💬 Calling chat tool with simple function:")
        result = await call_tool_simple(
            "fastmcp_chatbot_server.py",
            "chat_with_user",
            {"message": "Hello from simple function!", "user_id": "simple_user"}
        )
        
        if result.success:
            print("✅ Simple call successful:")
            print(json.dumps(result.result, indent=2))
        else:
            print(f"❌ Simple call failed: {result.error}")
    
    except Exception as e:
        logger.error(f"Error in simple functions example: {e}")

async def example_tool_search():
    """Example of searching for tools."""
    print("\n🔍 Example: Tool Search")
    print("=" * 40)
    
    try:
        async with MCPToolClient("fastmcp_chatbot_server.py") as client:
            # Search for weather-related tools
            print("\n🌤️ Searching for weather tools:")
            weather_tools = client.find_tools_by_keyword("weather")
            for tool in weather_tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Search for math-related tools
            print("\n🧮 Searching for math tools:")
            math_tools = client.find_tools_by_keyword("math")
            for tool in math_tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Search for time-related tools
            print("\n⏰ Searching for time tools:")
            time_tools = client.find_tools_by_keyword("time")
            for tool in time_tools:
                print(f"  - {tool.name}: {tool.description}")
    
    except Exception as e:
        logger.error(f"Error in tool search example: {e}")

async def example_batch_operations():
    """Example of batch tool operations."""
    print("\n📦 Example: Batch Operations")
    print("=" * 40)
    
    try:
        from mcp_tool_client import ToolCall
        
        async with MCPToolClient("fastmcp_chatbot_server.py") as client:
            # Create a batch of tool calls
            tool_calls = [
                ToolCall("get_time", {"timezone": "UTC"}, "Get current UTC time"),
                ToolCall("get_weather", {"city": "London", "units": "metric"}, "Get London weather"),
                ToolCall("calculate_math", {"expression": "10 * 5 + 3"}, "Calculate expression"),
                ToolCall("get_news", {"category": "technology", "limit": 3}, "Get tech news")
            ]
            
            print(f"\n🚀 Executing {len(tool_calls)} tools in batch:")
            
            # Execute all tools
            results = await client.execute_tool_plan(tool_calls)
            
            # Display results
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result.tool_name}")
                if result.success:
                    print(f"   ✅ Success ({result.execution_time:.2f}s)")
                    print(f"   Response: {json.dumps(result.result, indent=4)}")
                else:
                    print(f"   ❌ Failed: {result.error}")
    
    except Exception as e:
        logger.error(f"Error in batch operations example: {e}")

async def main():
    """Run all examples."""
    print("🚀 MCP Tool Client Examples")
    print("=" * 50)
    
    # Run examples
    await example_chatbot_client()
    await example_api_client()
    await example_simple_functions()
    await example_tool_search()
    await example_batch_operations()
    
    print("\n✅ All examples completed!")
    print("\n💡 To use the client interactively, run:")
    print("   python mcp_tool_client.py --server fastmcp_chatbot_server.py")

if __name__ == "__main__":
    asyncio.run(main())