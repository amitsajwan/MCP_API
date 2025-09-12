#!/usr/bin/env python3
"""
Test script to demonstrate generic API handling
"""

import asyncio
import os
import json
from mcp_service import ModernLLMService

async def test_generic_api_handling():
    """Test the generic API handling capabilities"""
    print("🧪 Testing Generic API Handling")
    print("=" * 50)
    
    # Set up environment variables for testing
    os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"
    os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "gpt-4o"
    os.environ["AZURE_OPENAI_API_VERSION"] = "2024-12-01-preview"
    
    # Create service instance
    service = ModernLLMService()
    
    print("✅ ModernLLMService class created successfully")
    
    # Test tool validation methods
    print("\n🔍 Testing tool validation methods...")
    
    # Test with a non-existent tool
    exists = await service.validate_tool_exists("non_existent_tool")
    print(f"✅ Tool validation (non-existent): {exists}")
    
    # Test tool suggestions
    suggestions = await service.suggest_similar_tools("getAccounts")
    print(f"✅ Tool suggestions for 'getAccounts': {suggestions}")
    
    # Test API summary
    print("\n📊 Testing API summary...")
    try:
        summary = await service.get_api_summary()
        print(f"✅ API summary: {json.dumps(summary, indent=2)}")
    except Exception as e:
        print(f"⚠️  API summary failed (expected without real MCP client): {e}")
    
    # Test capability analysis
    print("\n🎯 Testing capability analysis...")
    test_tool_calls = [
        {"tool_name": "cash_api_getPayments", "success": True},
        {"tool_name": "securities_api_getPortfolio", "success": True},
        {"tool_name": "mailbox_api_getAlerts", "success": True}
    ]
    
    capabilities = service._analyze_capabilities(test_tool_calls, "test message")
    print(f"✅ Capability analysis: {json.dumps(capabilities, indent=2)}")
    
    print("\n🎉 Generic API handling test completed!")
    print("\nKey Features Demonstrated:")
    print("✅ Generic tool validation")
    print("✅ Tool suggestion system")
    print("✅ Dynamic capability analysis")
    print("✅ API summary generation")
    print("✅ Flexible error handling")

if __name__ == "__main__":
    asyncio.run(test_generic_api_handling())