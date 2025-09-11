#!/usr/bin/env python3
"""
Simple MCP Client Test
A basic test that demonstrates the MCP client concept without requiring FastMCP installation.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple_mcp_test")

@dataclass
class MockToolInfo:
    """Mock tool information."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_params: List[str]
    optional_params: List[str]

@dataclass
class MockToolResult:
    """Mock tool result."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    response_size: int = 0

class MockMCPClient:
    """Mock MCP client for demonstration purposes."""
    
    def __init__(self, server_script: str = None):
        self.server_script = server_script or "mock_server.py"
        self.connected = False
        self.available_tools = []
        
        logger.info(f"Initialized Mock MCP Client for server: {self.server_script}")
    
    async def connect(self) -> bool:
        """Mock connection."""
        self.connected = True
        await self._load_mock_tools()
        logger.info(f"✅ Mock connected to {self.server_script} with {len(self.available_tools)} tools")
        return True
    
    async def disconnect(self):
        """Mock disconnection."""
        self.connected = False
        logger.info("Mock disconnected from MCP server")
    
    async def _load_mock_tools(self):
        """Load mock tools."""
        self.available_tools = [
            MockToolInfo(
                name="chat_with_user",
                description="Chat with the user",
                parameters={
                    "message": {"type": "string", "description": "User message", "required": True},
                    "user_id": {"type": "string", "description": "User ID", "required": False}
                },
                required_params=["message"],
                optional_params=["user_id"]
            ),
            MockToolInfo(
                name="get_weather",
                description="Get weather information for a city",
                parameters={
                    "city": {"type": "string", "description": "City name", "required": True},
                    "units": {"type": "string", "description": "Temperature units", "required": False}
                },
                required_params=["city"],
                optional_params=["units"]
            ),
            MockToolInfo(
                name="calculate_math",
                description="Calculate a mathematical expression",
                parameters={
                    "expression": {"type": "string", "description": "Math expression", "required": True}
                },
                required_params=["expression"],
                optional_params=[]
            ),
            MockToolInfo(
                name="get_time",
                description="Get current time in specified timezone",
                parameters={
                    "timezone": {"type": "string", "description": "Timezone", "required": False}
                },
                required_params=[],
                optional_params=["timezone"]
            ),
            MockToolInfo(
                name="create_todo",
                description="Create a new todo item",
                parameters={
                    "title": {"type": "string", "description": "Todo title", "required": True},
                    "description": {"type": "string", "description": "Todo description", "required": False},
                    "priority": {"type": "string", "description": "Priority level", "required": False}
                },
                required_params=["title"],
                optional_params=["description", "priority"]
            )
        ]
    
    async def list_tools(self) -> List[MockToolInfo]:
        """Get list of available tools."""
        if not self.connected:
            await self.connect()
        return self.available_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> MockToolResult:
        """Mock tool call."""
        if arguments is None:
            arguments = {}
        
        logger.info(f"Mock calling tool: {tool_name} with arguments: {arguments}")
        
        # Mock tool implementations
        if tool_name == "chat_with_user":
            message = arguments.get("message", "")
            user_id = arguments.get("user_id", "anonymous")
            result = {
                "status": "success",
                "message": f"Hello {user_id}! You said: '{message}'. How can I help you?",
                "user_id": user_id,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        elif tool_name == "get_weather":
            city = arguments.get("city", "Unknown")
            units = arguments.get("units", "metric")
            result = {
                "status": "success",
                "city": city,
                "temperature": 22,
                "condition": "sunny",
                "units": units,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        elif tool_name == "calculate_math":
            expression = arguments.get("expression", "0")
            try:
                # Simple safe evaluation (in real implementation, use proper math parser)
                allowed_chars = set('0123456789+-*/.() ')
                if all(c in allowed_chars for c in expression):
                    calculated_result = eval(expression)
                    result = {
                        "status": "success",
                        "expression": expression,
                        "result": calculated_result,
                        "timestamp": "2024-01-01T12:00:00Z"
                    }
                else:
                    result = {
                        "status": "error",
                        "message": "Invalid characters in expression"
                    }
            except Exception as e:
                result = {
                    "status": "error",
                    "message": f"Math error: {str(e)}"
                }
        elif tool_name == "get_time":
            timezone = arguments.get("timezone", "UTC")
            result = {
                "status": "success",
                "timezone": timezone,
                "time": "2024-01-01T12:00:00Z",
                "formatted": "2024-01-01 12:00:00 UTC"
            }
        elif tool_name == "create_todo":
            title = arguments.get("title", "Untitled")
            description = arguments.get("description", "")
            priority = arguments.get("priority", "medium")
            result = {
                "status": "success",
                "todo": {
                    "id": f"todo_{hash(title) % 10000}",
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "status": "pending",
                    "created_at": "2024-01-01T12:00:00Z"
                }
            }
        else:
            result = {
                "status": "error",
                "message": f"Unknown tool: {tool_name}"
            }
        
        return MockToolResult(
            tool_name=tool_name,
            success=result.get("status") == "success",
            result=result,
            error=result.get("message") if result.get("status") == "error" else None,
            execution_time=0.1,
            response_size=len(json.dumps(result))
        )
    
    def find_tools_by_keyword(self, keyword: str) -> List[MockToolInfo]:
        """Find tools by keyword."""
        keyword_lower = keyword.lower()
        matching_tools = []
        
        for tool in self.available_tools:
            if (keyword_lower in tool.name.lower() or 
                keyword_lower in tool.description.lower()):
                matching_tools.append(tool)
        
        return matching_tools
    
    def print_tools_summary(self):
        """Print tools summary."""
        if not self.available_tools:
            print("No tools available")
            return
        
        print(f"\n📋 Available Tools ({len(self.available_tools)}):")
        print("=" * 50)
        
        for tool in self.available_tools:
            print(f"\n🔧 {tool.name}")
            print(f"   Description: {tool.description}")
            print(f"   Required: {', '.join(tool.required_params) or 'None'}")
            print(f"   Optional: {', '.join(tool.optional_params) or 'None'}")

async def test_mock_client():
    """Test the mock MCP client."""
    print("🧪 Testing Mock MCP Client")
    print("=" * 40)
    
    client = MockMCPClient("mock_server.py")
    
    try:
        # Test connection
        print("\n1. Testing connection...")
        success = await client.connect()
        print(f"   Connection: {'✅ Success' if success else '❌ Failed'}")
        
        # Test listing tools
        print("\n2. Testing tool listing...")
        tools = await client.list_tools()
        print(f"   Found {len(tools)} tools")
        
        # Test tool search
        print("\n3. Testing tool search...")
        weather_tools = client.find_tools_by_keyword("weather")
        print(f"   Weather tools: {len(weather_tools)}")
        
        math_tools = client.find_tools_by_keyword("math")
        print(f"   Math tools: {len(math_tools)}")
        
        # Test individual tool calls
        print("\n4. Testing individual tool calls...")
        
        # Chat tool
        result = await client.call_tool("chat_with_user", {
            "message": "Hello, this is a test!",
            "user_id": "test_user"
        })
        print(f"   Chat tool: {'✅ Success' if result.success else '❌ Failed'}")
        if result.success:
            print(f"      Response: {result.result.get('message', 'No message')}")
        
        # Weather tool
        result = await client.call_tool("get_weather", {
            "city": "New York",
            "units": "metric"
        })
        print(f"   Weather tool: {'✅ Success' if result.success else '❌ Failed'}")
        if result.success:
            print(f"      Temperature: {result.result.get('temperature', 'N/A')}°C")
        
        # Math tool
        result = await client.call_tool("calculate_math", {
            "expression": "2 + 2 * 3"
        })
        print(f"   Math tool: {'✅ Success' if result.success else '❌ Failed'}")
        if result.success:
            print(f"      Result: {result.result.get('result', 'N/A')}")
        
        # Time tool
        result = await client.call_tool("get_time", {
            "timezone": "UTC"
        })
        print(f"   Time tool: {'✅ Success' if result.success else '❌ Failed'}")
        if result.success:
            print(f"      Time: {result.result.get('formatted', 'N/A')}")
        
        # Todo tool
        result = await client.call_tool("create_todo", {
            "title": "Test Todo",
            "description": "Created by test",
            "priority": "high"
        })
        print(f"   Todo tool: {'✅ Success' if result.success else '❌ Failed'}")
        if result.success:
            print(f"      Todo ID: {result.result.get('todo', {}).get('id', 'N/A')}")
        
        # Test error handling
        print("\n5. Testing error handling...")
        result = await client.call_tool("non_existent_tool", {})
        print(f"   Non-existent tool: {'✅ Correctly failed' if not result.success else '❌ Should have failed'}")
        
        # Test invalid math expression
        result = await client.call_tool("calculate_math", {
            "expression": "2 + import os"
        })
        print(f"   Invalid math: {'✅ Correctly failed' if not result.success else '❌ Should have failed'}")
        
        # Print tools summary
        print("\n6. Tools summary:")
        client.print_tools_summary()
        
        print("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    
    finally:
        await client.disconnect()

async def main():
    """Main test function."""
    print("🚀 MCP Tool Client - Mock Test Suite")
    print("=" * 50)
    print("This test demonstrates the MCP client concept using mock tools.")
    print("In a real environment, this would connect to actual FastMCP servers.")
    print()
    
    success = await test_mock_client()
    
    if success:
        print("\n🎉 Mock test suite passed!")
        print("\n💡 To use with real FastMCP servers:")
        print("   1. Install FastMCP: pip install fastmcp")
        print("   2. Run: python mcp_tool_client.py --server your_server.py")
        return 0
    else:
        print("\n💥 Mock test suite failed!")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))