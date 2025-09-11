#!/usr/bin/env python3
"""
Test MCP Client
Comprehensive tests for the MCP Tool Client with various servers.
"""

import asyncio
import json
import logging
import sys
from typing import List, Dict, Any
from mcp_tool_client import MCPToolClient, ToolCall

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_mcp_client")

class MCPClientTester:
    """Test suite for MCP Tool Client."""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log a test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
        
        if success:
            self.passed += 1
        else:
            self.failed += 1
    
    async def test_connection(self, server_script: str) -> bool:
        """Test basic connection to MCP server."""
        try:
            async with MCPToolClient(server_script) as client:
                if client.connected:
                    self.log_test(f"Connection to {server_script}", True, f"Connected successfully")
                    return True
                else:
                    self.log_test(f"Connection to {server_script}", False, "Failed to connect")
                    return False
        except Exception as e:
            self.log_test(f"Connection to {server_script}", False, str(e))
            return False
    
    async def test_list_tools(self, server_script: str) -> bool:
        """Test listing tools from MCP server."""
        try:
            async with MCPToolClient(server_script) as client:
                tools = await client.list_tools()
                if tools:
                    self.log_test(f"List tools from {server_script}", True, f"Found {len(tools)} tools")
                    return True
                else:
                    self.log_test(f"List tools from {server_script}", False, "No tools found")
                    return False
        except Exception as e:
            self.log_test(f"List tools from {server_script}", False, str(e))
            return False
    
    async def test_tool_search(self, server_script: str) -> bool:
        """Test tool search functionality."""
        try:
            async with MCPToolClient(server_script) as client:
                # Search for common tool keywords
                search_terms = ["chat", "weather", "time", "math", "login", "credentials"]
                found_any = False
                
                for term in search_terms:
                    tools = client.find_tools_by_keyword(term)
                    if tools:
                        found_any = True
                        break
                
                if found_any:
                    self.log_test(f"Tool search in {server_script}", True, f"Found tools matching search terms")
                    return True
                else:
                    self.log_test(f"Tool search in {server_script}", False, "No tools found for any search terms")
                    return False
        except Exception as e:
            self.log_test(f"Tool search in {server_script}", False, str(e))
            return False
    
    async def test_simple_tool_call(self, server_script: str, tool_name: str, args: Dict[str, Any]) -> bool:
        """Test calling a simple tool."""
        try:
            async with MCPToolClient(server_script) as client:
                result = await client.call_tool(tool_name, args)
                if result.success:
                    self.log_test(f"Call {tool_name} in {server_script}", True, f"Tool executed successfully in {result.execution_time:.2f}s")
                    return True
                else:
                    self.log_test(f"Call {tool_name} in {server_script}", False, f"Tool failed: {result.error}")
                    return False
        except Exception as e:
            self.log_test(f"Call {tool_name} in {server_script}", False, str(e))
            return False
    
    async def test_batch_tool_calls(self, server_script: str, tool_calls: List[ToolCall]) -> bool:
        """Test batch tool execution."""
        try:
            async with MCPToolClient(server_script) as client:
                results = await client.execute_tool_plan(tool_calls)
                successful = sum(1 for r in results if r.success)
                total = len(results)
                
                if successful > 0:
                    self.log_test(f"Batch calls in {server_script}", True, f"{successful}/{total} tools executed successfully")
                    return True
                else:
                    self.log_test(f"Batch calls in {server_script}", False, f"All {total} tools failed")
                    return False
        except Exception as e:
            self.log_test(f"Batch calls in {server_script}", False, str(e))
            return False
    
    async def test_chatbot_server(self):
        """Test the FastMCP Chatbot Server."""
        print("\n🤖 Testing FastMCP Chatbot Server")
        print("=" * 40)
        
        server_script = "fastmcp_chatbot_server.py"
        
        # Test connection
        await self.test_connection(server_script)
        
        # Test listing tools
        await self.test_list_tools(server_script)
        
        # Test tool search
        await self.test_tool_search(server_script)
        
        # Test specific tool calls
        await self.test_simple_tool_call(server_script, "chat_with_user", {
            "message": "Hello, this is a test!",
            "user_id": "test_user"
        })
        
        await self.test_simple_tool_call(server_script, "get_weather", {
            "city": "New York",
            "units": "metric"
        })
        
        await self.test_simple_tool_call(server_script, "calculate_math", {
            "expression": "2 + 2 * 3"
        })
        
        await self.test_simple_tool_call(server_script, "get_time", {
            "timezone": "UTC"
        })
        
        # Test batch operations
        batch_calls = [
            ToolCall("get_time", {"timezone": "UTC"}, "Get UTC time"),
            ToolCall("get_weather", {"city": "London", "units": "metric"}, "Get London weather"),
            ToolCall("calculate_math", {"expression": "10 * 5"}, "Calculate 10 * 5"),
            ToolCall("create_todo", {"title": "Test Todo", "description": "Created by test"}, "Create test todo")
        ]
        await self.test_batch_tool_calls(server_script, batch_calls)
    
    async def test_api_server(self):
        """Test the FastMCP API Server."""
        print("\n🔌 Testing FastMCP API Server")
        print("=" * 40)
        
        server_script = "mcp_server_fastmcp.py"
        
        # Test connection
        await self.test_connection(server_script)
        
        # Test listing tools
        await self.test_list_tools(server_script)
        
        # Test tool search
        await self.test_tool_search(server_script)
        
        # Test credential tools
        await self.test_simple_tool_call(server_script, "set_credentials", {
            "username": "test_user",
            "password": "test_password",
            "login_url": "http://localhost:8080/auth/login"
        })
        
        await self.test_simple_tool_call(server_script, "perform_login", {})
    
    async def test_error_handling(self):
        """Test error handling scenarios."""
        print("\n⚠️ Testing Error Handling")
        print("=" * 40)
        
        # Test with non-existent server
        try:
            async with MCPToolClient("non_existent_server.py") as client:
                if not client.connected:
                    self.log_test("Non-existent server", True, "Correctly failed to connect")
                else:
                    self.log_test("Non-existent server", False, "Should have failed to connect")
        except Exception as e:
            self.log_test("Non-existent server", True, f"Correctly raised exception: {type(e).__name__}")
        
        # Test calling non-existent tool
        try:
            async with MCPToolClient("fastmcp_chatbot_server.py") as client:
                result = await client.call_tool("non_existent_tool", {})
                if not result.success:
                    self.log_test("Non-existent tool", True, f"Correctly failed: {result.error}")
                else:
                    self.log_test("Non-existent tool", False, "Should have failed")
        except Exception as e:
            self.log_test("Non-existent tool", True, f"Correctly raised exception: {type(e).__name__}")
    
    async def test_performance(self):
        """Test performance with multiple concurrent calls."""
        print("\n⚡ Testing Performance")
        print("=" * 40)
        
        try:
            async with MCPToolClient("fastmcp_chatbot_server.py") as client:
                # Test concurrent tool calls
                tasks = []
                for i in range(5):
                    task = client.call_tool("get_time", {"timezone": "UTC"})
                    tasks.append(task)
                
                start_time = asyncio.get_event_loop().time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = asyncio.get_event_loop().time()
                
                successful = sum(1 for r in results if isinstance(r, object) and hasattr(r, 'success') and r.success)
                total_time = end_time - start_time
                
                if successful > 0:
                    self.log_test("Concurrent calls", True, f"{successful}/5 calls successful in {total_time:.2f}s")
                else:
                    self.log_test("Concurrent calls", False, "No calls successful")
        except Exception as e:
            self.log_test("Concurrent calls", False, str(e))
    
    def print_summary(self):
        """Print test summary."""
        print("\n📊 Test Summary")
        print("=" * 40)
        print(f"Total tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        
        if self.failed > 0:
            print("\n❌ Failed tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
    
    async def run_all_tests(self):
        """Run all tests."""
        print("🧪 MCP Tool Client Test Suite")
        print("=" * 50)
        
        # Test chatbot server
        await self.test_chatbot_server()
        
        # Test API server
        await self.test_api_server()
        
        # Test error handling
        await self.test_error_handling()
        
        # Test performance
        await self.test_performance()
        
        # Print summary
        self.print_summary()
        
        return self.failed == 0

async def main():
    """Run the test suite."""
    tester = MCPClientTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))