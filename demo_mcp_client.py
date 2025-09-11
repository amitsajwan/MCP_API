#!/usr/bin/env python3
"""
MCP Client Demo
Demonstrates how to use the MCP Tool Client with real FastMCP servers.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_demo")

def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_section(title: str):
    """Print a formatted section."""
    print(f"\n{title}")
    print("-" * len(title))

async def demo_chatbot_client():
    """Demo using the FastMCP Chatbot Server."""
    print_header("🤖 FastMCP Chatbot Server Demo")
    
    print("This demo shows how to use the MCP Tool Client with the FastMCP Chatbot Server.")
    print("The chatbot server provides tools for chat, weather, math, time, and more.")
    
    print_section("Available Tools")
    print("The chatbot server provides these tools:")
    tools = [
        ("chat_with_user", "Main chat function that processes user messages"),
        ("get_weather", "Get current weather for a specific city"),
        ("calculate_math", "Calculate mathematical expressions safely"),
        ("get_time", "Get current time in specified timezone"),
        ("search_web", "Search the web for information (simulated)"),
        ("send_email", "Send an email (simulated)"),
        ("create_todo", "Create a new todo item"),
        ("get_news", "Get latest news (simulated)"),
        ("get_conversation_history", "Get conversation history for a user")
    ]
    
    for tool_name, description in tools:
        print(f"  • {tool_name}: {description}")
    
    print_section("Example Usage")
    print("Here's how you would use the client:")
    
    code_example = '''
# Import the client
from mcp_tool_client import MCPToolClient

async def chatbot_example():
    # Connect to the chatbot server
    async with MCPToolClient("fastmcp_chatbot_server.py") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools")
        
        # Chat with the bot
        result = await client.call_tool("chat_with_user", {
            "message": "Hello! Can you help me with the weather?",
            "user_id": "demo_user"
        })
        print("Chat response:", result.result)
        
        # Get weather
        result = await client.call_tool("get_weather", {
            "city": "New York",
            "units": "metric"
        })
        print("Weather:", result.result)
        
        # Calculate math
        result = await client.call_tool("calculate_math", {
            "expression": "2 + 2 * 3"
        })
        print("Math result:", result.result)
        
        # Create a todo
        result = await client.call_tool("create_todo", {
            "title": "Learn MCP",
            "description": "Study Model Context Protocol",
            "priority": "high"
        })
        print("Todo created:", result.result)

# Run the example
asyncio.run(chatbot_example())
'''
    
    print(code_example)
    
    print_section("Interactive Mode")
    print("You can also use the interactive mode:")
    print("  python mcp_tool_client.py --server fastmcp_chatbot_server.py")
    print("\nThis gives you a command-line interface where you can:")
    print("  • list - List all available tools")
    print("  • info <tool_name> - Get detailed info about a tool")
    print("  • call <tool_name> <args> - Call a tool with arguments")
    print("  • search <keyword> - Search for tools by keyword")

async def demo_api_client():
    """Demo using the FastMCP API Server."""
    print_header("🔌 FastMCP API Server Demo")
    
    print("This demo shows how to use the MCP Tool Client with the FastMCP API Server.")
    print("The API server automatically generates tools from OpenAPI specifications.")
    
    print_section("Available Tools")
    print("The API server provides tools for:")
    print("  • Authentication (set_credentials, perform_login)")
    print("  • Cash API operations (getPayments, getCashSummary, etc.)")
    print("  • Securities API operations")
    print("  • Mailbox API operations")
    print("  • CLS API operations")
    
    print_section("Example Usage")
    print("Here's how you would use the client with the API server:")
    
    code_example = '''
# Import the client
from mcp_tool_client import MCPToolClient

async def api_example():
    # Connect to the API server
    async with MCPToolClient("mcp_server_fastmcp.py") as client:
        # Set credentials
        result = await client.call_tool("set_credentials", {
            "username": "your_username",
            "password": "your_password",
            "login_url": "http://localhost:8080/auth/login"
        })
        print("Credentials set:", result.result)
        
        # Perform login
        result = await client.call_tool("perform_login", {})
        print("Login result:", result.result)
        
        # Get pending payments
        result = await client.call_tool("cash_api_getPayments", {
            "status": "pending"
        })
        print("Pending payments:", result.result)
        
        # Get cash summary
        result = await client.call_tool("cash_api_getCashSummary", {
            "include_pending": True
        })
        print("Cash summary:", result.result)

# Run the example
asyncio.run(api_example())
'''
    
    print(code_example)

async def demo_web_interface():
    """Demo the web interface."""
    print_header("🌐 Web Interface Demo")
    
    print("The MCP Tool Client includes a modern web interface for easy tool usage.")
    
    print_section("Features")
    print("The web interface provides:")
    print("  • Visual tool browser with descriptions")
    print("  • Easy tool calling with form interface")
    print("  • Real-time results display")
    print("  • Tool parameter validation")
    print("  • Server switching capabilities")
    
    print_section("Starting the Web Interface")
    print("To start the web interface:")
    print("  python mcp_web_client.py")
    print("  # or")
    print("  python launch_mcp_client.py --mode web")
    print("\nThen open http://localhost:8000 in your browser.")
    
    print_section("Web Interface Features")
    print("1. Tool Browser: Visual grid of available tools")
    print("2. Tool Caller: Form-based tool calling")
    print("3. Real-time Results: Live display of results")
    print("4. Server Management: Switch between servers")

async def demo_advanced_features():
    """Demo advanced features."""
    print_header("⚡ Advanced Features Demo")
    
    print_section("Batch Operations")
    print("Execute multiple tools in sequence:")
    
    code_example = '''
from mcp_tool_client import MCPToolClient, ToolCall

async def batch_example():
    async with MCPToolClient("fastmcp_chatbot_server.py") as client:
        # Create batch of tool calls
        tool_calls = [
            ToolCall("get_time", {"timezone": "UTC"}, "Get UTC time"),
            ToolCall("get_weather", {"city": "London"}, "Get London weather"),
            ToolCall("calculate_math", {"expression": "10 * 5"}, "Calculate 10 * 5"),
            ToolCall("create_todo", {"title": "Batch Test"}, "Create test todo")
        ]
        
        # Execute all tools
        results = await client.execute_tool_plan(tool_calls)
        
        # Process results
        for result in results:
            if result.success:
                print(f"✅ {result.tool_name}: {result.result}")
            else:
                print(f"❌ {result.tool_name}: {result.error}")

asyncio.run(batch_example())
'''
    
    print(code_example)
    
    print_section("Tool Search")
    print("Find tools by keyword:")
    
    search_example = '''
async def search_example():
    async with MCPToolClient("fastmcp_chatbot_server.py") as client:
        # Search for weather-related tools
        weather_tools = client.find_tools_by_keyword("weather")
        print(f"Found {len(weather_tools)} weather tools")
        
        # Search for math-related tools
        math_tools = client.find_tools_by_keyword("math")
        print(f"Found {len(math_tools)} math tools")
        
        # Search for time-related tools
        time_tools = client.find_tools_by_keyword("time")
        print(f"Found {len(time_tools)} time tools")

asyncio.run(search_example())
'''
    
    print(search_example)
    
    print_section("Error Handling")
    print("Comprehensive error handling:")
    print("  • Connection errors")
    print("  • Tool execution errors")
    print("  • Parameter validation")
    print("  • Timeout handling")

async def demo_testing():
    """Demo testing capabilities."""
    print_header("🧪 Testing Demo")
    
    print("The MCP Tool Client includes comprehensive testing capabilities.")
    
    print_section("Test Suite")
    print("Run the full test suite:")
    print("  python test_mcp_client.py")
    print("  # or")
    print("  python launch_mcp_client.py --mode test")
    
    print_section("Test Coverage")
    print("The test suite covers:")
    print("  • Connection testing")
    print("  • Tool listing")
    print("  • Tool search")
    print("  • Individual tool calls")
    print("  • Batch operations")
    print("  • Error handling")
    print("  • Performance testing")
    
    print_section("Mock Testing")
    print("For development without FastMCP installation:")
    print("  python simple_mcp_client_test.py")
    print("\nThis runs a mock test suite that demonstrates the client concept.")

async def main():
    """Main demo function."""
    print("🚀 MCP Tool Client - Comprehensive Demo")
    print("=" * 60)
    print("This demo shows all the capabilities of the MCP Tool Client.")
    print("The client works with any FastMCP server that uses app.tool().")
    
    # Run all demos
    await demo_chatbot_client()
    await demo_api_client()
    await demo_web_interface()
    await demo_advanced_features()
    await demo_testing()
    
    print_header("🎉 Demo Complete!")
    print("The MCP Tool Client is ready to use with your FastMCP servers.")
    print("\nNext steps:")
    print("1. Install FastMCP: pip install fastmcp")
    print("2. Start a server: python fastmcp_chatbot_server.py")
    print("3. Use the client: python mcp_tool_client.py --server fastmcp_chatbot_server.py")
    print("4. Or use the web interface: python mcp_web_client.py")

if __name__ == "__main__":
    asyncio.run(main())