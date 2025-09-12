# MCP OpenAPI Server

An MCP (Model Context Protocol) server that automatically generates tools from OpenAPI specifications, allowing MCP clients to interact with REST APIs seamlessly.

## Features

- **Automatic Tool Generation**: Parses OpenAPI specs and creates MCP tools for each operation
- **Schema Validation**: Validates input parameters against OpenAPI schemas
- **Error Handling**: Comprehensive error handling with proper HTTP status codes
- **Type Safety**: Supports all OpenAPI data types and validation rules
- **Real API Calls**: Makes actual HTTP requests to the specified API endpoints

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Start the MCP Server

```bash
python mcp_openapi_server.py <openapi-spec.yaml>
```

Example:
```bash
python mcp_openapi_server.py keylink-updated-api.yaml
```

### 2. Use as MCP Client

```python
import asyncio
from mcp.client import Client
from mcp.client.stdio import stdio_client

async def main():
    async with stdio_client("python", ["mcp_openapi_server.py", "keylink-updated-api.yaml"]) as (read, write):
        client = Client("my-client")
        await client.initialize(read, write)
        
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools.tools]}")
        
        # Call a tool
        result = await client.call_tool(
            name="getAccounts",
            arguments={"category": "EDO_TRANSACTION"}
        )
        print(f"Result: {result.content[0].text}")

asyncio.run(main())
```

### 3. Run Example Client

```bash
python example_client.py
```

## How It Works

1. **Parse OpenAPI Spec**: The server loads and parses the OpenAPI specification
2. **Generate Tools**: For each operation in the spec, it creates an MCP tool
3. **Handle Requests**: When a tool is called, it makes the corresponding HTTP request
4. **Return Results**: Returns the API response as MCP tool results

## Supported OpenAPI Features

- ✅ All HTTP methods (GET, POST, PUT, DELETE, etc.)
- ✅ Path parameters
- ✅ Query parameters
- ✅ Request/response schemas
- ✅ Parameter validation (required, type, enum)
- ✅ Error responses
- ✅ Schema references ($ref)
- ✅ Multiple servers

## Example: KeyLink API

For the KeyLink API specification provided:

### Generated Tools

1. **getAccounts**
   - **Input**: `category` (string, required, enum values)
   - **Output**: List of accounts with full schema validation
   - **Error Handling**: 400 (validation), 403 (forbidden)

### Usage

```python
# Call getAccounts with different categories
result = await client.call_tool(
    name="getAccounts",
    arguments={"category": "EDO_TRANSACTION"}
)

# The tool will:
# 1. Validate the category parameter
# 2. Make GET request to /api/accounts?category=EDO_TRANSACTION
# 3. Return the response as structured data
```

## Error Handling

The server handles various error scenarios:

- **Invalid Parameters**: Returns validation errors
- **API Errors**: Returns HTTP status codes and error messages
- **Network Errors**: Returns connection/timeout errors
- **Schema Errors**: Returns parsing/validation errors

## Configuration

The server automatically uses:
- **Base URL**: From the OpenAPI spec's `servers` section
- **Content-Type**: `application/json`
- **Accept**: `application/json`

## Development

To extend the server:

1. **Add Custom Headers**: Modify the HTTP client configuration
2. **Add Authentication**: Implement auth schemes in the request handler
3. **Add Caching**: Implement response caching
4. **Add Logging**: Enhance logging for debugging

## License

MIT License - see LICENSE file for details.