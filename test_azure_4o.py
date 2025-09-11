#!/usr/bin/env python3
"""
Test script for Azure 4o integration
"""

import asyncio
import logging
from azure_openai_client import azure_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_azure_4o")

async def test_azure_4o():
    """Test Azure 4o integration."""
    print("🧪 Testing Azure 4o Integration")
    print("=" * 40)
    
    # Test data
    user_query = "Show me my pending payments and cash summary"
    available_tools = [
        {
            "name": "cash_api_getPayments",
            "description": "Get payments with optional status filter",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Payment status filter (pending, completed, etc.)"
                    }
                }
            }
        },
        {
            "name": "cash_api_getCashSummary",
            "description": "Get cash summary including balances and pending approvals",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "include_pending": {
                        "type": "boolean",
                        "description": "Whether to include pending approvals"
                    }
                }
            }
        }
    ]
    
    try:
        print(f"📝 User Query: {user_query}")
        print(f"🔧 Available Tools: {len(available_tools)}")
        
        # Test Azure 4o planning
        print("\n🤖 Testing Azure 4o tool planning...")
        tool_calls = await azure_client.create_tool_plan(user_query, available_tools)
        
        if tool_calls:
            print(f"✅ Azure 4o created {len(tool_calls)} tool calls:")
            for i, tool_call in enumerate(tool_calls, 1):
                print(f"  {i}. {tool_call.tool_name}")
                print(f"     Arguments: {tool_call.arguments}")
                print(f"     Reason: {tool_call.reason}")
        else:
            print("❌ No tool calls created")
        
        # Test chat completion
        print("\n💬 Testing Azure 4o chat completion...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        response = await azure_client.chat_completion(messages, max_tokens=100)
        if response and "choices" in response:
            content = response["choices"][0]["message"]["content"]
            print(f"✅ Chat completion successful: {content[:100]}...")
        else:
            print("❌ Chat completion failed")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")
    
    finally:
        # Clean up
        await azure_client.close()
        print("\n👋 Test completed")

if __name__ == "__main__":
    asyncio.run(test_azure_4o())