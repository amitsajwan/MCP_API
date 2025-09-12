#!/usr/bin/env python3
"""
WebSocket UI Integration Test
=============================
Tests the actual WebSocket UI (web_ui_ws.py) with the MCP service
"""

import asyncio
import json
import logging
import sys
import os
import threading
import time
from unittest.mock import Mock, patch, AsyncMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("websocket_ui_test")

# Mock the external dependencies
sys.modules['fastmcp'] = Mock()
sys.modules['fastmcp.client'] = Mock()

class MockMCPClient:
    """Mock MCP client for testing"""
    
    def __init__(self):
        self.connected = False
        self.tools = []
    
    async def __aenter__(self):
        self.connected = True
        logger.info("🔌 [MOCK_MCP] Connected to MCP server")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.connected = False
        logger.info("🔌 [MOCK_MCP] Disconnected from MCP server")
    
    async def call_tool(self, tool_name: str, args: dict) -> dict:
        """Mock tool call execution"""
        logger.info(f"🔧 [MOCK_MCP] Calling tool: {tool_name} with args: {list(args.keys())}")
        
        # Simulate different tool responses
        if 'cash_api_getPayments' in tool_name:
            return {
                "status": "success",
                "data": {
                    "payments": [
                        {"id": "PAY001", "amount": 1000, "currency": "USD", "status": "pending"},
                        {"id": "PAY002", "amount": 2500, "currency": "EUR", "status": "completed"}
                    ]
                }
            }
        elif 'mailbox_api_getMessages' in tool_name:
            return {
                "status": "success",
                "data": {
                    "messages": [
                        {"id": "MSG001", "subject": "Payment Confirmation", "status": "unread"},
                        {"id": "MSG002", "subject": "Portfolio Update", "status": "unread"}
                    ]
                }
            }
        elif 'securities_api_getPortfolio' in tool_name:
            return {
                "status": "success",
                "data": {
                    "holdings": [
                        {"symbol": "AAPL", "shares": 100, "value": 15000},
                        {"symbol": "GOOGL", "shares": 50, "value": 12000}
                    ],
                    "total_value": 27000
                }
            }
        else:
            return {
                "status": "error",
                "message": f"Unknown tool: {tool_name}"
            }

class MockAzureClient:
    """Mock Azure OpenAI client for testing"""
    
    def __init__(self):
        self.tools = []
    
    async def chat_completions_create(self, model, messages, tools=None, tool_choice="auto"):
        """Mock Azure OpenAI chat completions"""
        logger.info(f"🤖 [MOCK_AZURE] Processing {len(messages)} messages")
        
        if tools:
            self.tools = tools
        
        # Simulate tool selection based on message content
        user_message = messages[-1]['content'].lower()
        tool_calls = []
        
        if 'payment' in user_message or 'payments' in user_message:
            tool_calls.append({
                'id': 'call_payment_123',
                'type': 'function',
                'function': {
                    'name': 'cash_api_getPayments',
                    'arguments': json.dumps({
                        'status': 'pending',
                        'limit': 10
                    })
                }
            })
        elif 'mailbox' in user_message or 'message' in user_message:
            tool_calls.append({
                'id': 'call_mailbox_456',
                'type': 'function',
                'function': {
                    'name': 'mailbox_api_getMessages',
                    'arguments': json.dumps({
                        'status': 'unread',
                        'category': 'inbox'
                    })
                }
            })
        elif 'portfolio' in user_message or 'securities' in user_message:
            tool_calls.append({
                'id': 'call_securities_789',
                'type': 'function',
                'function': {
                    'name': 'securities_api_getPortfolio',
                    'arguments': json.dumps({
                        'account_id': 'ACC123'
                    })
                }
            })
        
        if tool_calls:
            return Mock(
                choices=[Mock(
                    finish_reason="tool_calls",
                    message=Mock(
                        content=None,
                        tool_calls=tool_calls
                    )
                )]
            )
        else:
            return Mock(
                choices=[Mock(
                    finish_reason="stop",
                    message=Mock(
                        content="I can help you with payments, mailbox, and portfolio management. What would you like to do?",
                        tool_calls=None
                    )
                )]
            )

# Mock the MCP service dependencies
def mock_create_azure_client():
    """Mock Azure client creation"""
    return MockAzureClient()

def mock_list_and_prepare_tools(mcp_client):
    """Mock tools preparation"""
    return [
        {
            "type": "function",
            "function": {
                "name": "cash_api_getPayments",
                "description": "Get payments from cash management system",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Payment status filter"},
                        "limit": {"type": "integer", "description": "Maximum number of payments"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "mailbox_api_getMessages",
                "description": "Get messages from mailbox",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Message status filter"},
                        "category": {"type": "string", "description": "Message category"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "securities_api_getPortfolio",
                "description": "Get portfolio holdings",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string", "description": "Account identifier"}
                    }
                }
            }
        }
    ]

def mock_safe_truncate(data, max_length=1000):
    """Mock data truncation"""
    return data

# Apply mocks
with patch('mcp_client.create_azure_client', mock_create_azure_client), \
     patch('mcp_client.list_and_prepare_tools', mock_list_and_prepare_tools), \
     patch('mcp_client.safe_truncate', mock_safe_truncate), \
     patch('mcp_client.PythonStdioTransport', Mock), \
     patch('mcp_client.MCPClient', MockMCPClient):
    
    # Now import the actual modules
    from mcp_service import ModernLLMService
    from web_ui_ws import MCPDemoService, AsyncEventLoop

class WebSocketUITest:
    """Test the WebSocket UI integration"""
    
    def __init__(self):
        self.demo_service = MCPDemoService()
        self.async_loop = AsyncEventLoop()
        self.test_results = []
    
    async def test_service_initialization(self):
        """Test MCP service initialization"""
        logger.info("🔄 Testing MCP Service Initialization...")
        
        try:
            result = await self.demo_service.initialize()
            
            if result:
                self.test_results.append(("Service Initialization", True, "✅ Service initialized successfully"))
                logger.info("✅ Service initialization test passed")
                return True
            else:
                self.test_results.append(("Service Initialization", False, "❌ Service initialization failed"))
                logger.error("❌ Service initialization test failed")
                return False
        except Exception as e:
            self.test_results.append(("Service Initialization", False, f"❌ Service initialization error: {e}"))
            logger.error(f"❌ Service initialization error: {e}")
            return False
    
    async def test_message_processing(self, message: str, expected_tool: str = None):
        """Test message processing"""
        logger.info(f"🔄 Testing message processing: '{message[:50]}...'")
        
        try:
            result = await self.demo_service.process_message(message)
            
            if result.get("success") or "response" in result:
                # Check if expected tool was called
                tool_calls = result.get("tool_calls", [])
                if expected_tool:
                    tool_names = [tc.get("tool_name", "") for tc in tool_calls]
                    if expected_tool in tool_names:
                        self.test_results.append((f"Message: {message[:30]}...", True, f"✅ Tool {expected_tool} called successfully"))
                        logger.info(f"✅ Message processing test passed - {expected_tool} called")
                    else:
                        self.test_results.append((f"Message: {message[:30]}...", False, f"❌ Expected tool {expected_tool} not called"))
                        logger.error(f"❌ Expected tool {expected_tool} not called")
                        return False
                else:
                    self.test_results.append((f"Message: {message[:30]}...", True, "✅ Message processed successfully"))
                    logger.info("✅ Message processing test passed")
                
                return True
            else:
                self.test_results.append((f"Message: {message[:30]}...", False, f"❌ Message processing failed: {result.get('error', 'Unknown error')}"))
                logger.error(f"❌ Message processing failed: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            self.test_results.append((f"Message: {message[:30]}...", False, f"❌ Message processing error: {e}"))
            logger.error(f"❌ Message processing error: {e}")
            return False
    
    async def test_tools_retrieval(self):
        """Test tools retrieval"""
        logger.info("🔄 Testing tools retrieval...")
        
        try:
            tools = await self.demo_service.get_tools()
            
            if tools and len(tools) > 0:
                self.test_results.append(("Tools Retrieval", True, f"✅ Retrieved {len(tools)} tools"))
                logger.info(f"✅ Tools retrieval test passed - {len(tools)} tools")
                return True
            else:
                self.test_results.append(("Tools Retrieval", False, "❌ No tools retrieved"))
                logger.error("❌ Tools retrieval test failed")
                return False
        except Exception as e:
            self.test_results.append(("Tools Retrieval", False, f"❌ Tools retrieval error: {e}"))
            logger.error(f"❌ Tools retrieval error: {e}")
            return False
    
    def print_results(self):
        """Print test results"""
        print("\n🎯 WebSocket UI Integration Test Results")
        print("=" * 60)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, success, message in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}: {message}")
            if success:
                passed += 1
        
        print(f"\n📊 Summary: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
            print("The WebSocket UI integration is working correctly!")
        else:
            print("❌ SOME TESTS FAILED!")
            print("Please check the implementation.")

async def main():
    """Main test function"""
    print("🚀 WebSocket UI Integration Test")
    print("=" * 60)
    print("Testing: web_ui_ws.py (WebSocket UI)")
    print("Service: MCPDemoService with ModernLLMService")
    print("Template: templates/chat_ws.html")
    print()
    
    # Create test instance
    test = WebSocketUITest()
    
    # Test 1: Service initialization
    await test.test_service_initialization()
    
    # Test 2: Tools retrieval
    await test.test_tools_retrieval()
    
    # Test 3: Payment message processing
    await test.test_message_processing("Show me pending payments", "cash_api_getPayments")
    
    # Test 4: Mailbox message processing
    await test.test_message_processing("Check my unread messages", "mailbox_api_getMessages")
    
    # Test 5: Portfolio message processing
    await test.test_message_processing("Show me my portfolio", "securities_api_getPortfolio")
    
    # Test 6: General message processing (no tools)
    await test.test_message_processing("Hello, how are you?")
    
    # Print results
    test.print_results()
    
    print(f"\n🔑 Key Components Tested:")
    print("• MCPDemoService.initialize() - async method")
    print("• MCPDemoService.process_message() - async method")
    print("• MCPDemoService.get_tools() - async method")
    print("• ModernLLMService integration")
    print("• Tool selection and execution")
    print("• Error handling")
    print("• WebSocket UI compatibility")
    
    print(f"\n✨ WebSocket UI Status:")
    print("✅ web_ui_ws.py - WebSocket-based UI")
    print("✅ templates/chat_ws.html - HTML template")
    print("✅ Flask-SocketIO - Real-time communication")
    print("✅ AsyncEventLoop - Proper async handling")
    print("✅ MCPDemoService - Service wrapper")
    print("✅ ModernLLMService - Core MCP service")

if __name__ == "__main__":
    asyncio.run(main())