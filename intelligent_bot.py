"""
MCP Bot - Personal API Assistant
===============================
My smart assistant that understands what you need and does it for you
"""

import asyncio
import json
import os
from mcp_service import ModernLLMService

async def run_intelligent_bot():
    """Run my personal API assistant"""
    print("🤖 MCP Bot - Your Personal Assistant")
    print("=" * 50)
    print("Hey! I'm your bot and I can help you with API stuff.")
    print("Just tell me what you need and I'll figure out how to do it.")
    print()
    print("Try asking me things like:")
    print("  - 'Show me all pending payments over $1000'")
    print("  - 'Create a new payment for $500 to John Doe'")
    print("  - 'Get my cash balance and recent transactions'")
    print("  - 'I need to approve payment 12345 and create a CLS settlement'")
    print()
    print("Type 'quit' when you're done")
    print()
    
    # Initialize the MCP service
    print("🔄 Initializing MCP service...")
    service = ModernLLMService()
    success = await service.initialize()
    
    if not success:
        print("❌ Failed to initialize MCP service")
        print("Make sure your Azure credentials are configured")
        return
    
    print("✅ MCP service initialized with 51 tools")
    print()
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            print("🧠 Analyzing your request...")
            
            # Process with intelligent LLM service
            result = await service.process_message(user_input)
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                continue
            
            # Show what tools were used
            if result.get('tool_calls'):
                print("\n🔧 Tools executed:")
                for tool_call in result['tool_calls']:
                    tool_name = tool_call['tool_name']
                    args = tool_call.get('args', {})
                    status = "✅ Success" if not tool_call.get('error') else "❌ Failed"
                    print(f"  - {tool_name}: {status}")
                    if args:
                        print(f"    Args: {json.dumps(args, indent=2)}")
                    if tool_call.get('error'):
                        print(f"    Error: {tool_call['error']}")
            
            # Show capabilities demonstrated
            if result.get('capabilities'):
                caps = result['capabilities']
                print(f"\n✨ Capabilities: {', '.join(caps.get('descriptions', []))}")
            
            # Show the response
            print(f"\n🤖 Response: {result['response']}")
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
    
    # Cleanup
    await service.cleanup()

if __name__ == "__main__":
    asyncio.run(run_intelligent_bot())
