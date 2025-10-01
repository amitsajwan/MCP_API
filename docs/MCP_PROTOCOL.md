# 🔌 MCP Protocol Implementation

## Using FastMCP with OpenAPI

This system uses **FastMCP** (https://gofastmcp.com/integrations/openapi) to automatically convert OpenAPI specifications into MCP tools.

## MCP Server (mcp_server_fastmcp.py)

### Loads OpenAPI Specs
```python
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

# Create MCP server
mcp = FastMCP("API Orchestration Server")

# Load OpenAPI spec
with open("openapi_specs/cash_api.yaml") as f:
    spec = yaml.safe_load(f)

# Convert to MCP tools using FastMCP
mcp_tools = FastMCP.from_openapi(
    openapi_spec=spec,
    client=httpx.AsyncClient(base_url=spec['servers'][0]['url']),
    name="cash_api",
    route_maps=[...]  # Configure tool types
)

# Expose via MCP protocol
mcp.run(transport="stdio")
```

### Route Mapping Strategy
- GET with path params → ResourceTemplate
- GET without params → Resource
- POST/PUT/DELETE → Tool

## MCP Client (MCPClientConnector)

### Connects via stdio
```python
# Start MCP server process
server_process = subprocess.Popen(
    ["python", "mcp_server_fastmcp.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE
)

# Connect via MCP protocol
from mcp.client.stdio import stdio_client
session = await stdio_client(
    server_process.stdin,
    server_process.stdout
)
```

### Discovers Tools
```python
# List all tools via MCP protocol
tools_response = await session.list_tools()

# Tools from ALL loaded OpenAPI specs
tools = [
    {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.inputSchema
    }
    for tool in tools_response.tools
]
```

### Executes Tools
```python
# Execute tool via MCP protocol
result = await session.call_tool(
    "get_cash_accounts",
    {"user_id": "123"}
)

# Server makes actual API call
# Returns result via MCP protocol
```

## Protocol Flow

```
1. Client starts MCP Server
    ↓
2. Server loads OpenAPI specs (cash, securities, mailbox, cls)
    ↓
3. Server exposes tools via MCP protocol
    ↓
4. Client calls list_tools()
    ↓
5. Server returns ALL tools from ALL specs
    ↓
6. Client has complete tool registry
    ↓
7. User query arrives
    ↓
8. LLM selects tools from discovered registry
    ↓
9. Client calls call_tool() for each tool
    ↓
10. Server executes actual API calls
    ↓
11. Results returned to client
    ↓
12. Client caches, summarizes, processes
```

## Benefits of FastMCP

✅ **Automatic conversion** - OpenAPI → MCP tools
✅ **No manual coding** - FastMCP handles everything
✅ **Standard protocol** - Official MCP implementation
✅ **Route mapping** - Intelligent tool categorization
✅ **Validation** - Schema validation built-in

---

**Using FastMCP 2.0+ with OpenAPI integration**
