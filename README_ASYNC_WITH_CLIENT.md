# FastMCP Client Usage Guide

## Using `async with client` Pattern

The FastMCP clients now support the `async with client` pattern for automatic connection and disconnection management.

### 1. FastMCP Client (mcp_client_fastmcp.py)

```python
import asyncio
from mcp_client_fastmcp import FastMCPClientWrapper

async def main():
    # Use async context manager - automatically connects and disconnects
    async with FastMCPClientWrapper() as client:
        print("✅ Client connected!")
        
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {len(tools)}")
        
        # Process a query
        result = await client.process_query("Show me my pending payments")
        print(f"Result: {result['summary']}")
    
    # Client automatically disconnects here

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. FastMCP Chatbot Client (fastmcp_chatbot_client.py)

```python
import asyncio
from fastmcp_chatbot_client import FastMCPChatbotClient

async def main():
    # Use async context manager - automatically connects and disconnects
    async with FastMCPChatbotClient() as client:
        print("✅ Chatbot client connected!")
        
        # List available tools
        tools = client.get_available_tools()
        print(f"Available tools: {tools}")
        
        # Send a chat message
        response = await client.chat("Hello, how are you?")
        print(f"Response: {response}")
    
    # Client automatically disconnects here

if __name__ == "__main__":
    asyncio.run(main())
```

## Do I Need to Start the MCP Server Separately?

**No, you do NOT need to start the MCP server separately!** 

The clients automatically handle server startup and shutdown:

### How It Works:

1. **Automatic Server Management**: When you use `async with client`, the client automatically:
   - Starts the MCP server process in the background
   - Connects to it via stdio transport
   - Manages the connection lifecycle
   - Automatically shuts down the server when done

2. **Server Process**: The client spawns a subprocess running the server script:
   - For `FastMCPClientWrapper`: runs `mcp_server_fastmcp.py --transport stdio`
   - For `FastMCPChatbotClient`: runs `fastmcp_chatbot_server.py --transport stdio`

3. **Cleanup**: When the `async with` block exits, the client automatically:
   - Disconnects from the server
   - Terminates the server process
   - Cleans up resources

### Manual Server Management (Optional)

If you prefer to manage the server manually, you can still do so:

```python
# Manual approach (not recommended)
client = FastMCPClientWrapper()
await client.connect()
# ... use client ...
await client.disconnect()
```

But the `async with` pattern is recommended for better resource management.

## Examples

### Basic Usage Example

```python
#!/usr/bin/env python3
import asyncio
from mcp_client_fastmcp import FastMCPClientWrapper

async def main():
    async with FastMCPClientWrapper() as client:
        # Client is automatically connected
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools")
        
        # Use any tool
        result = await client.call_tool("some_tool", {"param": "value"})
        print(f"Tool result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Error Handling

```python
async def main():
    try:
        async with FastMCPClientWrapper() as client:
            # Your code here
            pass
    except Exception as e:
        print(f"Error: {e}")
        # Client is automatically cleaned up even if an error occurs
```

## Benefits of `async with client`

1. **Automatic Resource Management**: No need to manually call `connect()` and `disconnect()`
2. **Error Safety**: Resources are cleaned up even if exceptions occur
3. **Cleaner Code**: Less boilerplate code
4. **Server Lifecycle**: Server is automatically started and stopped
5. **Connection Management**: Connection is automatically established and closed

## Running the Examples

```bash
# Run the basic FastMCP client example
python mcp_client_fastmcp.py

# Run the chatbot client example
python fastmcp_chatbot_client.py

# Run the comprehensive example
python example_async_with_client.py
```

## Configuration

The clients use configuration from `config.py` or environment variables:

- `MCP_SERVER_SCRIPT`: Server script to run (default: "mcp_server_fastmcp.py")
- `MCP_SERVER_ARGS`: Arguments to pass to server (default: ["--transport", "stdio"])
- `LOG_LEVEL`: Logging level (default: "INFO")

## Troubleshooting

### Common Issues:

1. **"Client not connected"**: This error should not occur with `async with client` as it automatically connects
2. **Server startup fails**: Check that the server script exists and is executable
3. **Connection timeout**: Ensure no other process is using the same resources

### Debug Mode:

Set `LOG_LEVEL=DEBUG` in your environment or config to see detailed connection logs.

## Summary

- ✅ Use `async with client` for automatic connection management
- ✅ No need to start MCP server separately
- ✅ Server is automatically managed by the client
- ✅ Resources are automatically cleaned up
- ✅ Error-safe resource management