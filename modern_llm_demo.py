"""
Modern LLM Tool Capabilities Demo
================================
Simple demonstration of modern LLM tool usage
"""

import asyncio
import logging
from mcp_service import mcp_service

logging.basicConfig(level=logging.INFO)

async def run_demo():
    """Run modern LLM capabilities demo"""
    print("🚀 Modern LLM Tool Capabilities Demo")
    print("=" * 50)
    
    # Initialize service
    print("1. Initializing service...")
    success = await mcp_service.initialize()
    if not success:
        print("❌ Failed to initialize")
        return
    
    print("✅ Service initialized")
    
    # Demo queries
    demo_queries = [
        "Hello, what tools do you have available?",
        "Check my account balance and recent transactions",
        "Get my financial summary and recommend investments"
    ]
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        result = await mcp_service.process_message(query)
        
        if 'error' in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            print(f"   ✅ Response: {result['response'][:100]}...")
            capabilities = result.get('capabilities', {})
            if capabilities.get('descriptions'):
                print(f"   🎯 Capabilities: {', '.join(capabilities['descriptions'])}")
            print(f"   🔧 Tools used: {capabilities.get('tool_count', 0)}")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    await mcp_service.cleanup()
    print("✅ Demo completed!")

if __name__ == "__main__":
    asyncio.run(run_demo())