#!/usr/bin/env python3
"""
Example: Using FastMCP Client with async context manager
This demonstrates the proper way to use the client with 'async with client' pattern.
"""

import asyncio
import logging
from mcp_client_fastmcp import FastMCPClientWrapper
from fastmcp_chatbot_client import FastMCPChatbotClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("example")

async def example_fastmcp_client():
    """Example using FastMCP client with async context manager."""
    print("🔧 Example: FastMCP Client with async context manager")
    print("=" * 60)
    
    try:
        # Use async context manager - this automatically connects and disconnects
        async with FastMCPClientWrapper() as client:
            print("✅ Client connected successfully!")
            
            # List available tools
            tools = await client.list_tools()
            print(f"📋 Available tools: {len(tools)}")
            for tool in tools[:3]:  # Show first 3 tools
                print(f"  - {tool.get('name', 'Unknown')}")
            
            # Test a simple query
            result = await client.process_query("Show me my pending payments")
            print(f"📊 Query result: {result.get('status', 'unknown')}")
            if result.get('summary'):
                print(f"Summary: {result['summary'][:100]}...")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(f"❌ Error: {e}")

async def example_chatbot_client():
    """Example using FastMCP Chatbot client with async context manager."""
    print("\n🤖 Example: FastMCP Chatbot Client with async context manager")
    print("=" * 60)
    
    try:
        # Use async context manager - this automatically connects and disconnects
        async with FastMCPChatbotClient() as client:
            print("✅ Chatbot client connected successfully!")
            
            # List available tools
            tools = client.get_available_tools()
            print(f"📋 Available tools: {len(tools)}")
            for tool in tools[:3]:  # Show first 3 tools
                print(f"  - {tool}")
            
            # Test a simple chat
            response = await client.chat("Hello, how are you?")
            print(f"💬 Chat response: {response[:100]}...")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(f"❌ Error: {e}")

async def main():
    """Main example function."""
    print("🚀 FastMCP Client Examples with async context manager")
    print("=" * 60)
    
    # Example 1: FastMCP Client
    await example_fastmcp_client()
    
    # Example 2: Chatbot Client
    await example_chatbot_client()
    
    print("\n✅ Examples completed!")

if __name__ == "__main__":
    asyncio.run(main())