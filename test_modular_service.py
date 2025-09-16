#!/usr/bin/env python3
"""
Test Modular MCP Service
========================
Test the modular MCP service implementation to ensure all components work together.
"""

import asyncio
import json
import logging
from modular_mcp_service import create_modular_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_modular_service():
    """Test the modular MCP service"""
    print("🧪 Testing Modular MCP Service")
    print("=" * 50)
    
    try:
        # Create service with mock components
        print("🔄 Creating modular service...")
        service = await create_modular_service(use_mock=True)
        print("✅ Service created successfully")
        
        # Test 1: Basic message processing
        print("\n📝 Test 1: Basic message processing")
        result1 = await service.process_message(
            "Hello, can you help me?",
            session_id="test_session_1"
        )
        
        print(f"Response: {result1['response']}")
        print(f"Success: {result1['success']}")
        print(f"Tool calls: {len(result1['tool_calls'])}")
        
        # Test 2: Message with tool usage
        print("\n📝 Test 2: Message with tool usage")
        result2 = await service.process_message(
            "Show me all pending payments over $1000",
            session_id="test_session_1"
        )
        
        print(f"Response: {result2['response']}")
        print(f"Tool calls: {len(result2['tool_calls'])}")
        print(f"Capabilities: {result2['capabilities']['descriptions']}")
        
        # Test 3: Multiple tool calls
        print("\n📝 Test 3: Multiple tool calls")
        result3 = await service.process_message(
            "Get my portfolio and create a payment for $500",
            session_id="test_session_1"
        )
        
        print(f"Response: {result3['response']}")
        print(f"Tool calls: {len(result3['tool_calls'])}")
        for i, tool_call in enumerate(result3['tool_calls'], 1):
            print(f"  Tool {i}: {tool_call['tool_name']} - {'Success' if tool_call['success'] else 'Failed'}")
        
        # Test 4: Conversation management
        print("\n📝 Test 4: Conversation management")
        summary = await service.get_conversation_summary("test_session_1")
        print(f"Conversation summary: {json.dumps(summary, indent=2)}")
        
        # Test 5: Capability analysis
        print("\n📝 Test 5: Capability analysis")
        analysis = await service.get_capability_analysis("test_session_1")
        print(f"Session analysis: {json.dumps(analysis, indent=2)}")
        
        # Test 6: Tool usage stats
        print("\n📝 Test 6: Tool usage statistics")
        stats = await service.get_tool_usage_stats()
        print(f"Tool usage stats: {json.dumps(stats, indent=2)}")
        
        # Test 7: Multiple sessions
        print("\n📝 Test 7: Multiple sessions")
        result4 = await service.process_message(
            "What tools are available?",
            session_id="test_session_2"
        )
        print(f"Response in new session: {result4['response']}")
        
        # Test 8: Clear conversation
        print("\n📝 Test 8: Clear conversation")
        await service.clear_conversation("test_session_1")
        summary_after_clear = await service.get_conversation_summary("test_session_1")
        print(f"Conversation after clear: {summary_after_clear['message_count']} messages")
        
        print("\n✅ All tests completed successfully!")
        
        # Cleanup
        await service.cleanup()
        print("🧹 Cleanup completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed with exception")

async def test_individual_components():
    """Test individual components separately"""
    print("\n🔧 Testing Individual Components")
    print("=" * 50)
    
    try:
        # Test ToolOrchestrator
        print("\n📝 Testing ToolOrchestrator...")
        from tool_orchestrator import ToolOrchestrator
        from mcp_tool_executor import MockToolExecutor
        
        executor = MockToolExecutor()
        orchestrator = ToolOrchestrator(executor)
        
        # Mock tool calls
        tool_calls = [
            {
                "id": "call_1",
                "function": {
                    "name": "get_payments",
                    "arguments": '{"status": "pending"}'
                }
            },
            {
                "id": "call_2", 
                "function": {
                    "name": "get_portfolio",
                    "arguments": '{"account_id": "ACC123"}'
                }
            }
        ]
        
        results = await orchestrator.execute_tool_calls(tool_calls, "parallel")
        print(f"Orchestrator executed {len(results)} tools")
        for result in results:
            print(f"  - {result.tool_name}: {'Success' if result.success else 'Failed'}")
        
        # Test ConversationManager
        print("\n📝 Testing ConversationManager...")
        from conversation_manager import ConversationManager
        
        conv_manager = ConversationManager()
        conv_manager.start_conversation("test_session")
        
        conv_manager.add_message("test_session", "user", "Hello")
        conv_manager.add_message("test_session", "assistant", "Hi there!")
        
        history = conv_manager.get_conversation_history("test_session")
        print(f"Conversation has {len(history)} messages")
        
        # Test CapabilityAnalyzer
        print("\n📝 Testing CapabilityAnalyzer...")
        from capability_analyzer import CapabilityAnalyzer
        
        analyzer = CapabilityAnalyzer()
        
        # Mock tool results
        tool_results = [
            {
                "tool_call_id": "call_1",
                "tool_name": "get_payments",
                "success": True,
                "execution_time": 0.5,
                "result": {"payments": []}
            }
        ]
        
        capabilities = analyzer.analyze_tool_execution(
            tool_results, "Show me payments", "test_session"
        )
        print(f"Detected capabilities: {capabilities['descriptions']}")
        
        print("\n✅ Individual component tests completed!")
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        logger.exception("Component test failed with exception")

if __name__ == "__main__":
    print("🚀 Starting Modular MCP Service Tests")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_modular_service())
    asyncio.run(test_individual_components())
    
    print("\n🎉 All tests completed!")