"""
Intelligent Bot Demo (No Azure Required)
=======================================
Demo version that shows tool execution without requiring Azure credentials
"""

import asyncio
import json
import os
from mcp_client import MCPClient, PythonStdioTransport, list_and_prepare_tools, safe_truncate

async def run_demo_bot():
    """Run the demo bot that shows tool execution"""
    print("🧠 Intelligent MCP Bot (Demo Mode)")
    print("=" * 50)
    print("I can understand your requirements and execute tools!")
    print("Note: This is demo mode - no Azure LLM, but I can show tool execution")
    print()
    print("Examples:")
    print("  - 'Show me all pending payments over $1000'")
    print("  - 'Create a new payment for $500 to John Doe'")
    print("  - 'Get my cash balance and recent transactions'")
    print()
    print("Type 'quit' to exit")
    print()
    
    # Initialize MCP connection
    print("🔄 Initializing MCP connection...")
    try:
        # Parse command: "python mcp_server_fastmcp2.py --transport stdio"
        cmd_parts = "python mcp_server_fastmcp2.py --transport stdio".split()
        script_path = cmd_parts[1]  # mcp_server_fastmcp2.py
        args = cmd_parts[2:]  # ['--transport', 'stdio']
        transport = PythonStdioTransport(script_path, args=args)
        mcp_client = MCPClient(transport)
        
        async with mcp_client:
            tools = await list_and_prepare_tools(mcp_client)
            print(f"✅ MCP connection initialized with {len(tools)} tools")
            print()
            
            # Show available tools
            print("🔧 Available tools:")
            for i, tool in enumerate(tools[:10], 1):  # Show first 10
                tool_name = tool['function']['name']
                tool_desc = tool['function']['description']
                print(f"  {i}. {tool_name}: {tool_desc}")
            if len(tools) > 10:
                print(f"  ... and {len(tools) - 10} more tools")
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
                    
                    # Simulate intelligent tool selection based on keywords
                    selected_tools = []
                    
                    # Simple keyword-based tool selection
                    if any(word in user_input.lower() for word in ['payment', 'pay', 'transaction']):
                        selected_tools = [tool for tool in tools if 'payment' in tool['function']['name'].lower()]
                    elif any(word in user_input.lower() for word in ['balance', 'cash', 'account']):
                        selected_tools = [tool for tool in tools if 'balance' in tool['function']['name'].lower() or 'cash' in tool['function']['name'].lower()]
                    elif any(word in user_input.lower() for word in ['cls', 'settlement']):
                        selected_tools = [tool for tool in tools if 'cls' in tool['function']['name'].lower()]
                    elif any(word in user_input.lower() for word in ['mailbox', 'message', 'email']):
                        selected_tools = [tool for tool in tools if 'mailbox' in tool['function']['name'].lower()]
                    
                    if not selected_tools:
                        selected_tools = tools[:3]  # Default to first 3 tools
                    
                    print(f"\n🔧 Selected {len(selected_tools)} relevant tools:")
                    for tool in selected_tools[:3]:  # Show first 3
                        print(f"  - {tool['function']['name']}: {tool['function']['description']}")
                    
                    # Simulate tool execution
                    print("\n🤖 Simulating tool execution...")
                    for tool in selected_tools[:2]:  # Execute first 2
                        tool_name = tool['function']['name']
                        print(f"  ✅ Executing {tool_name}...")
                        
                        # Simulate some tool calls
                        if 'get' in tool_name.lower():
                            print(f"    📊 Retrieved data: {{'status': 'success', 'count': 5}}")
                        elif 'create' in tool_name.lower():
                            print(f"    ✨ Created resource: {{'id': '12345', 'status': 'created'}}")
                        elif 'update' in tool_name.lower():
                            print(f"    🔄 Updated resource: {{'id': '12345', 'status': 'updated'}}")
                        else:
                            print(f"    📋 Processed: {{'result': 'completed'}}")
                    
                    # Show capabilities demonstrated
                    capabilities = [
                        "🧠 Intelligent Tool Selection",
                        "🔗 Tool Chaining",
                        "🔄 Adaptive Usage"
                    ]
                    print(f"\n✨ Capabilities: {', '.join(capabilities)}")
                    
                    # Simulate intelligent response
                    print(f"\n🤖 Response: I've analyzed your request and executed the relevant tools. ")
                    print("In a real implementation, I would use Azure GPT-4o to understand your request")
                    print("and intelligently select and execute the appropriate tools to fulfill your needs.")
                    print("-" * 50)
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    print()
                    
    except Exception as e:
        print(f"❌ Failed to initialize MCP connection: {e}")
        print("Make sure mcp_server_fastmcp2.py is working")

if __name__ == "__main__":
    asyncio.run(run_demo_bot())
