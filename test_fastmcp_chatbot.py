#!/usr/bin/env python3
"""
FastMCP Chatbot Test Suite
Comprehensive tests for the FastMCP chatbot system.
"""

import asyncio
import json
import logging
import sys
import time
import subprocess
from typing import Dict, Any, List
from pathlib import Path

# Import our modules
from fastmcp_chatbot_client import FastMCPChatbotClient
from fastmcp_config import FastMCPConfig, setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger("test_suite")

class FastMCPChatbotTester:
    """Test suite for the FastMCP chatbot system."""
    
    def __init__(self):
        self.config = FastMCPConfig()
        self.client: FastMCPChatbotClient = None
        self.test_results: List[Dict[str, Any]] = []
        self.server_process = None
        
    async def setup(self) -> bool:
        """Setup the test environment."""
        try:
            logger.info("🔧 Setting up test environment...")
            
            # Create client
            self.client = FastMCPChatbotClient()
            
            # Start server for testing
            logger.info("🚀 Starting FastMCP server for testing...")
            self.server_process = subprocess.Popen(
                [sys.executable, "fastmcp_chatbot_server.py", "--transport", "stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to start
            await asyncio.sleep(2)
            
            # Connect client
            if not await self.client.connect():
                logger.error("❌ Failed to connect to server")
                return False
            
            logger.info("✅ Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup test environment."""
        try:
            if self.client:
                await self.client.disconnect()
            
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            
            logger.info("🧹 Test environment cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def record_test(self, test_name: str, success: bool, message: str = "", duration: float = 0.0):
        """Record a test result."""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "duration": duration,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message} ({duration:.2f}s)")
    
    async def test_connection(self) -> bool:
        """Test basic connection to server."""
        start_time = time.time()
        try:
            if not self.client or not self.client.connected:
                self.record_test("connection", False, "Client not connected", time.time() - start_time)
                return False
            
            # Test basic connectivity
            tools = await self.client.list_tools()
            if tools:
                self.record_test("connection", True, f"Connected with {len(tools)} tools", time.time() - start_time)
                return True
            else:
                self.record_test("connection", False, "No tools available", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("connection", False, str(e), time.time() - start_time)
            return False
    
    async def test_chat_functionality(self) -> bool:
        """Test basic chat functionality."""
        start_time = time.time()
        try:
            # Test simple chat
            response = await self.client.chat("Hello, how are you?")
            
            if response and len(response) > 0:
                self.record_test("chat_basic", True, f"Received response: {response[:50]}...", time.time() - start_time)
                return True
            else:
                self.record_test("chat_basic", False, "No response received", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("chat_basic", False, str(e), time.time() - start_time)
            return False
    
    async def test_weather_tool(self) -> bool:
        """Test weather tool functionality."""
        start_time = time.time()
        try:
            response = await self.client.get_weather("New York", "metric")
            
            if "New York" in response and "temperature" in response.lower():
                self.record_test("weather_tool", True, f"Weather data received: {response[:50]}...", time.time() - start_time)
                return True
            else:
                self.record_test("weather_tool", False, f"Unexpected response: {response}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("weather_tool", False, str(e), time.time() - start_time)
            return False
    
    async def test_math_tool(self) -> bool:
        """Test math tool functionality."""
        start_time = time.time()
        try:
            response = await self.client.calculate_math("15 * 23 + 45")
            
            if "390" in response or "result" in response.lower():
                self.record_test("math_tool", True, f"Math calculation successful: {response[:50]}...", time.time() - start_time)
                return True
            else:
                self.record_test("math_tool", False, f"Unexpected response: {response}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("math_tool", False, str(e), time.time() - start_time)
            return False
    
    async def test_time_tool(self) -> bool:
        """Test time tool functionality."""
        start_time = time.time()
        try:
            response = await self.client.get_time("UTC")
            
            if "time" in response.lower() or "UTC" in response:
                self.record_test("time_tool", True, f"Time data received: {response[:50]}...", time.time() - start_time)
                return True
            else:
                self.record_test("time_tool", False, f"Unexpected response: {response}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("time_tool", False, str(e), time.time() - start_time)
            return False
    
    async def test_todo_tool(self) -> bool:
        """Test todo tool functionality."""
        start_time = time.time()
        try:
            response = await self.client.create_todo("Test Todo", "This is a test todo item", "high")
            
            if "todo" in response.lower() and "created" in response.lower():
                self.record_test("todo_tool", True, f"Todo created successfully: {response[:50]}...", time.time() - start_time)
                return True
            else:
                self.record_test("todo_tool", False, f"Unexpected response: {response}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("todo_tool", False, str(e), time.time() - start_time)
            return False
    
    async def test_news_tool(self) -> bool:
        """Test news tool functionality."""
        start_time = time.time()
        try:
            response = await self.client.get_news("technology", 3)
            
            if "news" in response.lower() or "articles" in response.lower():
                self.record_test("news_tool", True, f"News data received: {response[:50]}...", time.time() - start_time)
                return True
            else:
                self.record_test("news_tool", False, f"Unexpected response: {response}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("news_tool", False, str(e), time.time() - start_time)
            return False
    
    async def test_web_search_tool(self) -> bool:
        """Test web search tool functionality."""
        start_time = time.time()
        try:
            response = await self.client.search_web("FastMCP chatbot", 2)
            
            if "search" in response.lower() or "results" in response.lower():
                self.record_test("web_search_tool", True, f"Search results received: {response[:50]}...", time.time() - start_time)
                return True
            else:
                self.record_test("web_search_tool", False, f"Unexpected response: {response}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("web_search_tool", False, str(e), time.time() - start_time)
            return False
    
    async def test_conversation_history(self) -> bool:
        """Test conversation history functionality."""
        start_time = time.time()
        try:
            # Send a few messages first
            await self.client.chat("Test message 1")
            await self.client.chat("Test message 2")
            
            # Get conversation history
            history = await self.client.get_conversation_history("default", 5)
            
            if len(history) >= 2:
                self.record_test("conversation_history", True, f"Retrieved {len(history)} messages", time.time() - start_time)
                return True
            else:
                self.record_test("conversation_history", False, f"Expected at least 2 messages, got {len(history)}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("conversation_history", False, str(e), time.time() - start_time)
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling with invalid inputs."""
        start_time = time.time()
        try:
            # Test with invalid math expression
            response = await self.client.calculate_math("invalid math expression with symbols @#$")
            
            if "error" in response.lower() or "invalid" in response.lower():
                self.record_test("error_handling", True, "Error handling working correctly", time.time() - start_time)
                return True
            else:
                self.record_test("error_handling", False, f"Expected error, got: {response}", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("error_handling", False, str(e), time.time() - start_time)
            return False
    
    async def test_tool_listing(self) -> bool:
        """Test tool listing functionality."""
        start_time = time.time()
        try:
            tools = self.client.get_available_tools()
            
            if tools and len(tools) > 0:
                self.record_test("tool_listing", True, f"Found {len(tools)} tools: {', '.join(tools[:3])}...", time.time() - start_time)
                return True
            else:
                self.record_test("tool_listing", False, "No tools found", time.time() - start_time)
                return False
                
        except Exception as e:
            self.record_test("tool_listing", False, str(e), time.time() - start_time)
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all tests."""
        logger.info("🧪 Starting FastMCP Chatbot Test Suite")
        logger.info("=" * 50)
        
        # Setup
        if not await self.setup():
            logger.error("❌ Test setup failed")
            return False
        
        try:
            # Run tests
            tests = [
                self.test_connection,
                self.test_chat_functionality,
                self.test_weather_tool,
                self.test_math_tool,
                self.test_time_tool,
                self.test_todo_tool,
                self.test_news_tool,
                self.test_web_search_tool,
                self.test_conversation_history,
                self.test_error_handling,
                self.test_tool_listing
            ]
            
            for test in tests:
                try:
                    await test()
                except Exception as e:
                    logger.error(f"Test {test.__name__} failed with exception: {e}")
                    self.record_test(test.__name__, False, f"Exception: {str(e)}", 0.0)
            
            # Generate report
            self.generate_report()
            
            # Check overall success
            passed = sum(1 for result in self.test_results if result["success"])
            total = len(self.test_results)
            
            logger.info("=" * 50)
            logger.info(f"🏁 Test Suite Complete: {passed}/{total} tests passed")
            
            return passed == total
            
        finally:
            await self.cleanup()
    
    def generate_report(self):
        """Generate a test report."""
        logger.info("\n📊 Test Report")
        logger.info("-" * 30)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {total - passed}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        logger.info("\nDetailed Results:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            logger.info(f"  {status} {result['test_name']}: {result['message']} ({result['duration']:.2f}s)")
        
        # Save report to file
        report_file = "test_report.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        logger.info(f"\n📄 Detailed report saved to: {report_file}")

async def main():
    """Main test runner."""
    tester = FastMCPChatbotTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())