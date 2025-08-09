import json
import requests
from mcp.server.fastmcp import FastMCP
from pathlib import Path

mcp = FastMCP("OpenAPI MCP Server")

# Load OpenAPI spec
spec_path = Path("spec.json")
with open(spec_path) as f:
    spec = json.load(f)

# Parse and register tools dynamically
for path, methods in spec["paths"].items():
    for method, details in methods.items():
        tool_name = f"{method.upper()}_{path.strip('/').replace('/', '_') or 'root'}"
        summary = details.get("summary", "")
        parameters = details.get("parameters", [])

        # Build MCP parameters
        mcp_params = {}
        for param in parameters:
            name = param["name"]
            schema_type = param.get("schema", {}).get("type", "string")
            mcp_params[name] = {
                "type": schema_type,
                "description": param.get("description", "")
            }

        @mcp.tool(name=tool_name, description=summary, parameters=mcp_params)
        def dynamic_tool(**kwargs):
            url = f"http://localhost:5000{path}"  # Change to real API base URL
            resp = requests.request(method, url, params=kwargs)
            return resp.json()

mcp.run()
