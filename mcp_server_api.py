#!/usr/bin/env python3
"""
OpenAPI MCP Server

- Loads OpenAPI specs from a directory (./openapi_specs by default)
- Generates MCP "tools" for endpoints
- Exposes a small FastAPI HTTP surface for introspection (used by the HTTP client)
- Uses FastMCP for the MCP tool host (stdio/http transport when run)
"""

import os
import glob
import json
import logging
import secrets
import argparse
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass

import yaml
import requests
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from openapi_spec_validator import validate_spec
from fastapi import FastAPI, HTTPException

# load environment variables if present
from dotenv import load_dotenv
load_dotenv()

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openapi_mcp_server")


@dataclass
class APISpec:
    """Represents a loaded OpenAPI specification."""
    name: str
    spec: Dict[str, Any]
    base_url: str
    file_path: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    priority: int = 1


class APITool(BaseModel):
    """Represents a single API endpoint exposed as a tool."""
    name: str
    description: str
    method: str
    path: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    operation_id: Optional[str] = None
    spec_name: str = ""


class OpenAPIMCPServer:
    """
    Main server class that loads OpenAPI specs and generates MCP tools.
    """
    def __init__(self, openapi_dir: str = "./openapi_specs"):
        self.mcp = FastMCP(name="OpenAPI MCP Server")
        self.openapi_dir = openapi_dir
        self.api_specs: Dict[str, APISpec] = {}
        self.api_tools: Dict[str, APITool] = {}
        self.sessions: Dict[str, requests.Session] = {}
        self.config: Optional[Dict[str, Any]] = None

        os.makedirs(self.openapi_dir, exist_ok=True)

        # register core management tools
        self._register_core_tools()

        # attempt auto-load
        self._auto_load_openapi_specs()

    def _auto_load_openapi_specs(self):
        """Scans the spec directory and loads all valid OpenAPI files."""
        logger.info("Scanning for OpenAPI specs in %s", self.openapi_dir)
        patterns = ["*.yaml", "*.yml", "*.json"]
        openapi_files = []
        for pattern in patterns:
            openapi_files.extend(glob.glob(os.path.join(self.openapi_dir, pattern)))
            openapi_files.extend(glob.glob(os.path.join(self.openapi_dir, "**", pattern), recursive=True))

        if not openapi_files:
            logger.warning("No OpenAPI files found in %s", self.openapi_dir)
            return

        loaded = 0
        for file_path in openapi_files:
            try:
                spec_name = Path(file_path).stem
                with open(file_path, "r", encoding="utf-8") as f:
                    if file_path.endswith(".json"):
                        spec = json.load(f)
                    else:
                        spec = yaml.safe_load(f)

                # Validate (will raise if invalid)
                validate_spec(spec)

                base_url = self._extract_base_url(spec)
                api_spec = APISpec(name=spec_name, spec=spec, base_url=base_url, file_path=file_path)
                session = requests.Session()

                self.api_specs[spec_name] = api_spec
                self.sessions[spec_name] = session

                created = self._generate_tools_from_spec(api_spec)
                loaded += 1
                logger.info("Loaded spec %s (%d tools)", spec_name, created)
            except yaml.YAMLError as e:
                logger.error("Failed to parse YAML file '%s': %s", file_path, e)
            except Exception as e:
                logger.error("Failed to load '%s': %s", file_path, e)

        logger.info("Finished loading specs. total specs=%d total_tools=%d", len(self.api_specs), len(self.api_tools))

    def _extract_base_url(self, spec: Dict[str, Any]) -> str:
        """Extracts the base URL from the OpenAPI spec."""
        if "servers" in spec and spec["servers"]:
            first = spec["servers"][0]
            if isinstance(first, dict) and "url" in first:
                return first["url"]
        # swagger v2
        if "host" in spec:
            scheme = "https" if "schemes" in spec and "https" in spec["schemes"] else "http"
            base_path = spec.get("basePath", "")
            return f"{scheme}://{spec['host']}{base_path}"
        
        logger.warning("No server URL found in spec, falling back to http://localhost:8080")
        return "http://localhost:8080"

    def _register_core_tools(self):
        """Registers the built-in management tools with FastMCP."""
        @self.mcp.tool(description="Log in and store configuration for API calls.")
        def login(
            username: Optional[str] = Field(default=None, description="username"),
            password: Optional[str] = Field(default=None, description="password"),
            base_url: Optional[str] = Field(default=None, description="base url"),
            environment: Optional[str] = Field(default="DEV", description="environment"),
            spec_name: Optional[str] = Field(default=None, description="specific spec to apply auth to")
        ):
            try:
                if username and password:
                    self.config = {
                        "username": username,
                        "password": password,
                        "base_url": base_url,
                        "environment": environment,
                        "spec_name": spec_name
                    }
                    auth = (username, password)
                    headers = {"Content-Type": "application/json", "Accept": "application/json"}
                    
                    if spec_name and spec_name in self.sessions:
                        self.sessions[spec_name].auth = auth
                        self.sessions[spec_name].headers.update(headers)
                    else:
                        for s in self.sessions.values():
                            s.auth = auth
                            s.headers.update(headers)

                cookies = {
                    "session_id": f"session_{environment}_{secrets.token_hex(16)}",
                    "auth_token": f"auth_{environment}_{secrets.token_hex(16)}"
                }
                return {"status": "success", "message": "login stored", "cookies": cookies, "environment": environment}
            except Exception as e:
                logger.exception("login failed")
                return {"status": "error", "message": str(e)}

        @self.mcp.tool(description="Reload OpenAPI specifications from disk.")
        def reload_openapi_specs():
            try:
                self.api_specs.clear()
                self.api_tools.clear()
                if not self.config:
                    self.sessions.clear()
                self._auto_load_openapi_specs()
                return {"status": "success", "message": "reloaded", "specs_loaded": len(self.api_specs), "tools_created": len(self.api_tools)}
            except Exception as e:
                logger.exception("reload failed")
                return {"status": "error", "message": str(e)}

        @self.mcp.tool(description="List loaded OpenAPI specifications.")
        def list_loaded_specs():
            specs_info = []
            for name, spec in self.api_specs.items():
                tools_count = len([t for t in self.api_tools.values() if t.spec_name == name])
                specs_info.append({
                    "name": name,
                    "base_url": spec.base_url,
                    "file_path": spec.file_path,
                    "endpoints_count": tools_count,
                    "title": spec.spec.get("info", {}).get("title", ""),
                    "version": spec.spec.get("info", {}).get("version", "")
                })
            return {"specifications": specs_info, "total_specs": len(specs_info), "total_endpoints": len(self.api_tools)}

        @self.mcp.tool(description="List all available API endpoints (tools).")
        def list_api_endpoints():
            endpoints = {}
            for tool_name, tool in self.api_tools.items():
                spec_name = tool.spec_name
                endpoints.setdefault(spec_name, []).append({
                    "name": tool_name,
                    "method": tool.method,
                    "path": tool.path,
                    "summary": tool.summary,
                    "description": tool.description
                })
            return {"endpoints_by_spec": endpoints, "total_endpoints": len(self.api_tools)}

        @self.mcp.tool(description="Search for API endpoints by keyword.")
        def search_endpoints(query: str = Field(description="Search query"), spec_name: Optional[str] = None):
            q = query.lower()
            matches = []
            for tool_name, tool in self.api_tools.items():
                if spec_name and tool.spec_name != spec_name:
                    continue
                searchable = f"{tool.name} {tool.description} {tool.summary} {' '.join(tool.tags)} {tool.path}".lower()
                if q in searchable:
                    matches.append({
                        "name": tool_name,
                        "spec": tool.spec_name,
                        "method": tool.method,
                        "path": tool.path,
                        "summary": tool.summary
                    })
            return {"query": query, "matches": matches, "count": len(matches)}

        @self.mcp.tool(description="Execute a configured API endpoint.")
        def execute_endpoint(endpoint_name: str = Field(description="The name of the endpoint tool to execute"), parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the endpoint call")):
            try:
                if endpoint_name not in self.api_tools:
                    return {"status": "error", "message": f"Endpoint {endpoint_name} not found", "available": list(self.api_tools.keys())[:20]}
                
                tool = self.api_tools[endpoint_name]
                spec = self.api_specs[tool.spec_name]
                session = self.sessions[tool.spec_name]
                url = f"{spec.base_url.rstrip('/')}{tool.path}"

                query_params = {}
                header_params = {}
                body_data = {}

                for name, value in parameters.items():
                    param_info = tool.parameters.get(name)
                    if not param_info:
                        logger.warning("Unknown parameter '%s' for endpoint '%s'. It will be ignored.", name, endpoint_name)
                        continue

                    location = param_info.get("location")
                    if location == "path":
                        url = url.replace(f"{{{name}}}", str(value))
                    elif location == "query":
                        query_params[name] = value
                    elif location == "header":
                        header_params[name] = str(value)
                    elif location == "body":
                        body_data[name] = value

                logger.info("Executing %s %s", tool.method, url)
                
                request_kwargs = {
                    "params": query_params,
                    "headers": header_params,
                }
                
                if tool.method in ("POST", "PUT", "PATCH") and body_data:
                    request_kwargs["json"] = body_data

                resp = session.request(tool.method, url, **request_kwargs)
                resp.raise_for_status()

                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    data = {"text": resp.text}

                return {"status": "success", "endpoint": endpoint_name, "method": tool.method, "url": resp.url, "status_code": resp.status_code, "response": data}
            
            except requests.exceptions.RequestException as re:
                logger.exception("API request failed for endpoint: %s", endpoint_name)
                # Try to include response body in error if available
                error_response = None
                if re.response is not None:
                    try:
                        error_response = re.response.json()
                    except json.JSONDecodeError:
                        error_response = re.response.text
                return {"status": "error", "message": str(re), "response": error_response}
            except Exception as e:
                logger.exception("execute_endpoint failed")
                return {"status": "error", "message": str(e)}

    def _generate_tools_from_spec(self, api_spec: APISpec) -> int:
        """Generates tool definitions from a parsed OpenAPI spec."""
        spec = api_spec.spec
        tools_created = 0
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue
                
                operation_id = details.get("operationId")
                if operation_id:
                    tool_name = f"{api_spec.name}_{operation_id}"
                else:
                    clean = path.strip("/").replace("/", "_").replace("{", "").replace("}", "").replace("-", "_")
                    tool_name = f"{api_spec.name}_{method.lower()}_{clean or 'root'}"

                base_name = tool_name
                i = 1
                while tool_name in self.api_tools:
                    tool_name = f"{base_name}_{i}"
                    i += 1

                summary = details.get("summary", "")
                description = details.get("description", "")
                tags = details.get("tags", [])
                full_desc = (summary + " - " + description).strip(" - ") or f"{method.upper()} {path}"

                parameters = {}
                for param in details.get("parameters", []):
                    pname = param.get("name")
                    if not pname: continue
                    schema = param.get("schema", {})
                    parameters[pname] = {
                        "type": schema.get("type", "string"),
                        "description": param.get("description", ""),
                        "required": param.get("required", False),
                        "location": param.get("in", "query")
                    }

                if "requestBody" in details:
                    rb = details["requestBody"]
                    content = rb.get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})
                        if schema.get("type") == "object" and "properties" in schema:
                            for prop, prop_schema in schema.get("properties", {}).items():
                                parameters[prop] = {
                                    "type": prop_schema.get("type", "string"),
                                    "description": prop_schema.get("description", ""),
                                    "required": prop in schema.get("required", []),
                                    "location": "body"
                                }

                api_tool = APITool(
                    name=tool_name,
                    description=full_desc,
                    method=method.upper(),
                    path=path,
                    parameters=parameters,
                    tags=tags,
                    summary=summary,
                    operation_id=operation_id,
                    spec_name=api_spec.name
                )

                self.api_tools[tool_name] = api_tool
                tools_created += 1

        return tools_created

    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
        """Starts the FastMCP server with the configured transport."""
        logger.info("Starting OpenAPI MCP Server - specs=%d tools=%d", len(self.api_specs), len(self.api_tools))
        self.mcp.run(transport=transport, host=host, port=port)


# --- FastAPI Introspection Server ---

app = FastAPI(title="OpenAPI MCP Server (HTTP introspection)")

# Create server instance
OPENAPI_DIR = os.getenv("OPENAPI_DIR", "./openapi_specs")
server = OpenAPIMCPServer(openapi_dir=OPENAPI_DIR)


@app.get("/")
async def root():
    return {"message": "OpenAPI MCP Server is running", "specs_loaded": len(server.api_specs)}


@app.get("/specs")
async def list_specs():
    return {"specifications": list(server.api_specs.keys()), "count": len(server.api_specs)}


@app.get("/endpoints")
async def list_endpoints():
    return {"endpoints": list(server.api_tools.keys()), "count": len(server.api_tools)}

@app.get("/tools")
async def list_tools():
    """Lists the core MCP tools, not the dynamically generated API tools."""
    return {
        "tools": [
            {
                "name": name,
                "description": tool.description,
                "input_schema": tool.input_model.schema() if hasattr(tool, "input_model") else {}
            }
            for name, tool in server.mcp.tools.items()
        ]
    }


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, body: dict):
    """Calls a core MCP tool by name."""
    if tool_name not in server.mcp.tools:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")
    tool = server.mcp.tools[tool_name]
    args = body.get("arguments", {})
    result = await tool.run(**args)
    return {"content": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OpenAPI MCP Server. Runs the MCP server to expose OpenAPI specs as tools. "
                    "The FastAPI introspection server can be run separately using an ASGI server like uvicorn.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "http"],
        help="The transport protocol for the MCP server.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="The host to bind to for HTTP transport.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="The port to bind to for HTTP transport.",
    )
    args = parser.parse_args()
    
    # Note: To run the FastAPI introspection server, use:
    # uvicorn openapi_mcp_server:app --host <host> --port <port>
    
    server.run(transport=args.transport, host=args.host, port=args.port)
