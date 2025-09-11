#!/usr/bin/env python3
"""
Simple Example: Async Context Manager Pattern
This demonstrates the async context manager pattern that should be used with the FastMCP clients.
"""

import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple_example")

class SimpleAsyncClient:
    """Simple example of an async client with context manager support."""
    
    def __init__(self, name: str = "SimpleClient"):
        self.name = name
        self.connected = False
        self.data = []
    
    async def __aenter__(self):
        """Async context manager entry - automatically connects."""
        print(f"🔗 Connecting {self.name}...")
        await asyncio.sleep(0.1)  # Simulate connection time
        self.connected = True
        print(f"✅ {self.name} connected successfully!")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - automatically disconnects."""
        print(f"🔌 Disconnecting {self.name}...")
        await asyncio.sleep(0.1)  # Simulate disconnection time
        self.connected = False
        print(f"👋 {self.name} disconnected!")
    
    async def do_something(self, task: str):
        """Simulate doing some work."""
        if not self.connected:
            raise Exception("Client not connected!")
        
        print(f"🔄 {self.name} working on: {task}")
        await asyncio.sleep(0.2)  # Simulate work
        self.data.append(task)
        return f"Completed: {task}"

async def example_with_context_manager():
    """Example using async context manager."""
    print("🚀 Example: Using async context manager")
    print("=" * 50)
    
    try:
        # Use async context manager - automatically connects and disconnects
        async with SimpleAsyncClient("MyClient") as client:
            print("✅ Client is ready to use!")
            
            # Do some work
            result1 = await client.do_something("Task 1")
            print(f"Result: {result1}")
            
            result2 = await client.do_something("Task 2")
            print(f"Result: {result2}")
            
            print(f"📊 Client processed {len(client.data)} tasks")
        
        print("✅ Context manager automatically cleaned up!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def example_without_context_manager():
    """Example without context manager (manual management)."""
    print("\n🚀 Example: Manual connection management")
    print("=" * 50)
    
    client = SimpleAsyncClient("ManualClient")
    
    try:
        # Manual connection
        await client.__aenter__()
        print("✅ Manually connected!")
        
        # Do some work
        result = await client.do_something("Manual Task")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Manual disconnection
        await client.__aexit__(None, None, None)
        print("✅ Manually disconnected!")

async def example_error_handling():
    """Example showing error handling with context manager."""
    print("\n🚀 Example: Error handling with context manager")
    print("=" * 50)
    
    try:
        async with SimpleAsyncClient("ErrorClient") as client:
            print("✅ Client connected!")
            
            # This will cause an error
            await client.do_something("Normal task")
            
            # Simulate an error
            raise Exception("Something went wrong!")
            
    except Exception as e:
        print(f"❌ Caught error: {e}")
        print("✅ Context manager still cleaned up automatically!")

async def main():
    """Main example function."""
    print("📚 Async Context Manager Examples")
    print("=" * 60)
    print("This demonstrates the pattern you should use with FastMCP clients:")
    print("  async with FastMCPClientWrapper() as client:")
    print("      # Use client here")
    print("  # Client automatically disconnects")
    print()
    
    # Run examples
    await example_with_context_manager()
    await example_without_context_manager()
    await example_error_handling()
    
    print("\n🎉 All examples completed!")
    print("\n💡 Key Benefits of async with client:")
    print("  ✅ Automatic connection/disconnection")
    print("  ✅ Error-safe resource cleanup")
    print("  ✅ Cleaner, more readable code")
    print("  ✅ No need to remember to disconnect")

if __name__ == "__main__":
    asyncio.run(main())