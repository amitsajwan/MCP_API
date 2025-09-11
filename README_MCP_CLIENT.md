# MCP Tool Client

A comprehensive client for using MCP (Model Context Protocol) tools that have been registered with `app.tool()` in FastMCP servers.

## Features

- 🔌 **Easy Connection**: Connect to any FastMCP server with stdio transport
- 🛠️ **Tool Discovery**: Automatically discover and list available tools
- 🚀 **Tool Execution**: Call tools with arguments and get structured results
- 🔍 **Tool Search**: Find tools by keyword in name or description
- 📦 **Batch Operations**: Execute multiple tools in sequence
- 🌐 **Web Interface**: Modern web UI for interactive tool usage
- ⚡ **Async Support**: Full async/await support for high performance
- 🧪 **Testing**: Comprehensive test suite
- 📚 **Examples**: Multiple usage examples and patterns

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Basic Usage

```python
import asyncio
from mcp_tool_client import MCPToolClient

async def main():
    # Connect to a FastMCP server
    async with MCPToolClient("fastmcp_chatbot_server.py") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools")
        
        # Call a tool
        result = await client.call_tool("chat_with_user", {
            "message": "Hello!",
            "user_id": "user123"
        })
        
        if result.success:
            print("Tool result:", result.result)
        else:
            print("Tool failed:", result.error)

asyncio.run(main())
```

### 3. Interactive Mode

```bash
python mcp_tool_client.py --server fastmcp_chatbot_server.py
```

### 4. Web Interface

```bash
python mcp_web_client.py
# Open http://localhost:8000 in your browser
```

## Available Scripts

### Core Client

- **`mcp_tool_client.py`**: Main client implementation
- **`mcp_web_client.py`**: Web-based interface
- **`launch_mcp_client.py`**: Easy launcher with multiple modes

### Examples and Tests

- **`example_mcp_client_usage.py`**: Comprehensive usage examples
- **`test_mcp_client.py`**: Test suite for validation

## Usage Modes

### 1. Interactive Mode

Start an interactive command-line interface:

```bash
python launch_mcp_client.py --mode interactive --server fastmcp_chatbot_server.py
```

Available commands:
- `list` - List all available tools
- `info <tool_name>` - Get detailed info about a tool
- `call <tool_name> <args>` - Call a tool with arguments
- `search <keyword>` - Search for tools by keyword
- `help` - Show help
- `quit` - Exit

### 2. Web Mode

Start a web-based interface:

```bash
python launch_mcp_client.py --mode web --server fastmcp_chatbot_server.py
```

Features:
- Visual tool browser
- Easy tool calling with form interface
- Real-time results display
- Tool parameter validation

### 3. Programmatic Usage

```python
from mcp_tool_client import MCPToolClient, ToolCall

async def example():
    async with MCPToolClient("fastmcp_chatbot_server.py") as client:
        # List tools
        tools = await client.list_tools()
        
        # Search for tools
        weather_tools = client.find_tools_by_keyword("weather")
        
        # Call a single tool
        result = await client.call_tool("get_weather", {
            "city": "New York",
            "units": "metric"
        })
        
        # Execute multiple tools
        tool_calls = [
            ToolCall("get_time", {"timezone": "UTC"}),
            ToolCall("get_weather", {"city": "London"}),
            ToolCall("calculate_math", {"expression": "2 + 2"})
        ]
        results = await client.execute_tool_plan(tool_calls)
```

### 4. Simple Functions

For quick one-off operations:

```python
from mcp_tool_client import call_tool_simple, list_tools_simple

# List tools
tools = await list_tools_simple("fastmcp_chatbot_server.py")

# Call a tool
result = await call_tool_simple(
    "fastmcp_chatbot_server.py",
    "chat_with_user",
    {"message": "Hello!", "user_id": "user123"}
)
```

## API Reference

### MCPToolClient

Main client class for interacting with MCP servers.

#### Constructor

```python
MCPToolClient(server_script: str = None, server_args: List[str] = None)
```

- `server_script`: Path to the server script to run
- `server_args`: Additional arguments to pass to the server

#### Methods

##### `async connect() -> bool`
Connect to the MCP server.

##### `async disconnect()`
Disconnect from the MCP server.

##### `async list_tools() -> List[ToolInfo]`
Get list of available tools.

##### `async call_tool(tool_name: str, arguments: Dict[str, Any] = None) -> ToolResult`
Call a tool on the MCP server.

##### `async execute_tool_plan(tool_calls: List[ToolCall]) -> List[ToolResult]`
Execute multiple tools in sequence.

##### `get_tool_by_name(tool_name: str) -> Optional[ToolInfo]`
Get tool information by name.

##### `find_tools_by_keyword(keyword: str) -> List[ToolInfo]`
Find tools by keyword in name or description.

##### `print_tools_summary()`
Print a summary of available tools.

##### `async interactive_mode()`
Start interactive command-line mode.

### Data Classes

#### ToolInfo

Information about an available tool.

```python
@dataclass
class ToolInfo:
    name: str
    description: str
    parameters: Dict[str, Any]
    required_params: List[str]
    optional_params: List[str]
```

#### ToolCall

Represents a tool call to be executed.

```python
@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    reason: Optional[str] = None
```

#### ToolResult

Represents the result of a tool execution.

```python
@dataclass
class ToolResult:
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    response_size: int = 0
```

## Supported Servers

The client works with any FastMCP server that registers tools using `app.tool()`. Tested with:

- **FastMCP Chatbot Server** (`fastmcp_chatbot_server.py`)
- **FastMCP API Server** (`mcp_server_fastmcp.py`)
- **FastMCP API Server v2** (`mcp_server_fastmcp2.py`)

## Examples

### Chatbot Server Example

```python
async with MCPToolClient("fastmcp_chatbot_server.py") as client:
    # Chat with the bot
    result = await client.call_tool("chat_with_user", {
        "message": "What's the weather like?",
        "user_id": "user123"
    })
    
    # Get weather
    result = await client.call_tool("get_weather", {
        "city": "New York",
        "units": "metric"
    })
    
    # Calculate math
    result = await client.call_tool("calculate_math", {
        "expression": "2 + 2 * 3"
    })
    
    # Create a todo
    result = await client.call_tool("create_todo", {
        "title": "Learn MCP",
        "description": "Study Model Context Protocol",
        "priority": "high"
    })
```

### API Server Example

```python
async with MCPToolClient("mcp_server_fastmcp.py") as client:
    # Set credentials
    result = await client.call_tool("set_credentials", {
        "username": "myuser",
        "password": "mypassword",
        "login_url": "http://localhost:8080/auth/login"
    })
    
    # Perform login
    result = await client.call_tool("perform_login", {})
    
    # Call API endpoints (tools are auto-generated from OpenAPI specs)
    result = await client.call_tool("cash_api_getPayments", {
        "status": "pending"
    })
```

## Testing

Run the comprehensive test suite:

```bash
python test_mcp_client.py
```

Or use the launcher:

```bash
python launch_mcp_client.py --mode test
```

## Web Interface

The web interface provides a modern, user-friendly way to interact with MCP tools:

1. **Tool Browser**: Visual grid of available tools with descriptions
2. **Tool Caller**: Easy form-based tool calling with parameter validation
3. **Real-time Results**: Live display of tool execution results
4. **Server Management**: Switch between different MCP servers

Start the web interface:

```bash
python launch_mcp_client.py --mode web
```

Then open http://localhost:8000 in your browser.

## Error Handling

The client provides comprehensive error handling:

- **Connection Errors**: Graceful handling of server connection failures
- **Tool Errors**: Detailed error messages for tool execution failures
- **Validation Errors**: Parameter validation before tool calls
- **Timeout Handling**: Configurable timeouts for long-running operations

## Performance

- **Async/Await**: Full async support for high concurrency
- **Connection Pooling**: Efficient connection management
- **Batch Operations**: Execute multiple tools efficiently
- **Response Caching**: Optional caching of tool results

## Configuration

The client can be configured through:

1. **Constructor Parameters**: Direct configuration in code
2. **Environment Variables**: System-wide configuration
3. **Configuration Files**: JSON-based configuration files

## Troubleshooting

### Common Issues

1. **Connection Failed**: Ensure the server script exists and is executable
2. **No Tools Found**: Check that the server is running and has registered tools
3. **Tool Call Failed**: Verify tool name and arguments match the server's schema
4. **Import Errors**: Ensure all dependencies are installed

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Server Debugging

Check server logs for detailed error information:

```bash
python fastmcp_chatbot_server.py --transport stdio
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For questions and support:

1. Check the examples in `example_mcp_client_usage.py`
2. Run the test suite to verify your setup
3. Check server logs for detailed error information
4. Open an issue with detailed error logs and reproduction steps