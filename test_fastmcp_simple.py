#!/usr/bin/env python3
"""
Simple FastMCP 2.0 Test
"""

import asyncio
from fastmcp import FastMCP, Client

async def test_fastmcp():
    print("Testing FastMCP 2.0...")
    
    # Create a simple FastMCP server
    app = FastMCP("test-server")
    
    @app.tool()
    async def hello(name: str = "World") -> str:
        """Say hello to someone."""
        return f"Hello, {name}!"
    
    # Test the server directly
    print("Testing server directly...")
    result = await app.call_tool("hello", {"name": "FastMCP"})
    print(f"Direct call result: {result}")
    
    print("✅ FastMCP 2.0 test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_fastmcp())