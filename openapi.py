import yaml
import json
import requests
from mcp.server.fastmcp import FastMCP

# Load the OpenAPI YAML
with open("openapi.yaml", "r") as f:
    spec = yaml.safe_load(f)

mcp = FastMCP("OpenAPI Tools Server")

# Loop through paths to create MCP tools dynamically
for path, methods in spec.get("paths", {}).items():
    for method, details in methods.items():
        tool_name = f"{method.upper()}_{path.strip('/').replace('/', '_')}"
        summary = details.get("summary", f"{method.upper()} {path}")

        params = {}
        for param in details.get("parameters", []):
            params[param["name"]] = {
                "type": "string",  # simplification — can be expanded
                "description": param.get("description", ""),
            }

        @mcp.tool(name=tool_name, description=summary)
        def api_tool(**kwargs):
            url = spec["servers"][0]["url"] + path
            resp = requests.request(method.upper(), url, params=kwargs)
            return resp.json()

print(f"✅ Loaded {len(mcp.tools)} tools from OpenAPI spec")
mcp.run()
