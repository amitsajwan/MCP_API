#!/usr/bin/env python3
"""
Simple MCP Server - Streamlined Implementation
Focuses on core functionality:
- OpenAPI tool registration
- Authentication (login/set_credentials)
- Clean, minimal implementation
"""

import os
import json
import yaml
import logging
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from dataclasses import dataclass

# MCP Protocol imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# HTTP server imports
try:
    from aiohttp import web
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_mcp_server")


@dataclass
class APISpec:
    """API specification container."""
    name: str
    spec: Dict[str, Any]
    base_url: str


@dataclass
class APITool:
    """API tool representation."""
    name: str
    description: str
    method: str
    path: str
    parameters: Dict[str, Any]
    spec_name: str


class SimpleMCPServer:
    """Simple MCP Server implementation."""
    
    def __init__(self, openapi_dir: str = "./openapi_specs"):
        logger.info("🚀 Initializing Simple MCP Server...")
        self.server = Server("simple-openapi-mcp-server")
        self.api_specs: Dict[str, APISpec] = {}
        self.api_tools: Dict[str, APITool] = {}
        self.openapi_dir = openapi_dir
        
        # Authentication state
        self.username: Optional[str] = os.getenv('API_USERNAME')
        self.password: Optional[str] = os.getenv('API_PASSWORD')
        self.api_key_name: Optional[str] = os.getenv('API_KEY_NAME')
        self.api_key_value: Optional[str] = os.getenv('API_KEY_VALUE')
        self.login_url: Optional[str] = os.getenv('LOGIN_URL', 'http://localhost:8080/auth/login')
        self.session_id: Optional[str] = None
        
        # Initialize
        self._load_api_specs()
        self._register_mcp_tools()
        
        logger.info(f"✅ Simple MCP Server initialized with {len(self.api_tools)} tools from {len(self.api_specs)} API specs")
        
        if self.username:
            logger.info(f"🔐 Credentials loaded from environment for user: {self.username}")
        else:
            logger.info("🔓 No credentials found - use set_credentials tool")
    
    def _load_api_specs(self):
        """Load OpenAPI specifications from directory."""
        openapi_dir = Path(self.openapi_dir)
        if not openapi_dir.exists():
            logger.warning(f"OpenAPI directory not found: {openapi_dir}")
            return
        
        for spec_file in openapi_dir.glob("*.yaml"):
            try:
                with open(spec_file, 'r') as f:
                    spec_data = yaml.safe_load(f)
                
                spec_name = spec_file.stem
                base_url = self._get_base_url(spec_data)
                
                api_spec = APISpec(
                    name=spec_name,
                    spec=spec_data,
                    base_url=base_url
                )
                
                self.api_specs[spec_name] = api_spec
                self._register_spec_tools(spec_name, api_spec)
                
                logger.info(f"Loaded API spec: {spec_name} -> {base_url}")
                
            except Exception as e:
                logger.error(f"Failed to load spec {spec_file}: {e}")
    
    def _get_base_url(self, spec_data: Dict[str, Any]) -> str:
        """Get base URL for API specification."""
        # Check for environment override
        if os.getenv("FORCE_BASE_URL"):
            return os.getenv("FORCE_BASE_URL")
        
        # Extract from spec
        servers = spec_data.get('servers', [])
        if servers:
            return servers[0]['url']
        
        # Default fallback
        return "http://localhost:8080"
    
    def _register_mcp_tools(self):
        """Register API endpoints as MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available MCP tools."""
            tools = []
            
            # Add API tools
            for tool_name, api_tool in self.api_tools.items():
                mcp_parameters = {}
                required_params = []
                
                for param_name, param_info in api_tool.parameters.items():
                    param_schema = {
                        "type": param_info.get('type', 'string'),
                        "description": param_info.get('description', ''),
                    }
                    
                    # Add common schema properties
                    for prop in ['enum', 'format', 'minimum', 'maximum', 'example', 'default']:
                        if prop in param_info:
                            param_schema[prop] = param_info[prop]
                    
                    # Handle object properties for request body
                    if param_name == 'body' and param_info.get('type') == 'object':
                        if 'properties' in param_info:
                            param_schema['properties'] = param_info['properties']
                        if 'schema_required' in param_info:
                            param_schema['required'] = param_info['schema_required']
                    
                    mcp_parameters[param_name] = param_schema
                    
                    if param_info.get('required', False):
                        required_params.append(param_name)
                
                tool = Tool(
                    name=tool_name,
                    description=api_tool.description,
                    inputSchema={
                        "type": "object",
                        "properties": mcp_parameters,
                        "required": required_params,
                        "additionalProperties": False
                    }
                )
                tools.append(tool)
            
            # Add authentication tools
            tools.extend([
                Tool(
                    name="set_credentials",
                    description="Set authentication credentials for API access.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "username": {
                                "type": "string",
                                "description": "Username for authentication"
                            },
                            "password": {
                                "type": "string",
                                "description": "Password for authentication"
                            },
                            "api_key_name": {
                                "type": "string",
                                "description": "API key header name"
                            },
                            "api_key_value": {
                                "type": "string",
                                "description": "API key value"
                            },
                            "login_url": {
                                "type": "string",
                                "description": "Login URL"
                            }
                        },
                        "required": [],
                        "additionalProperties": False
                    }
                ),
                Tool(
                    name="perform_login",
                    description="Perform login using stored credentials.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "force_login": {
                                "type": "boolean",
                                "description": "Force login even if already authenticated",
                                "default": False
                            }
                        },
                        "required": [],
                        "additionalProperties": False
                    }
                )
            ])
            
            return tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Call an MCP tool by name."""
            logger.info(f"🔧 Executing tool: {name}")
            
            # Handle authentication tools
            if name == "set_credentials":
                return await self._handle_set_credentials(arguments)
            elif name == "perform_login":
                return await self._handle_perform_login(arguments)
            
            # Handle API tools
            if name not in self.api_tools:
                return [TextContent(type="text", text=f"Tool not found: {name}")]
            
            try:
                result = await self._execute_api_tool(name, arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _handle_set_credentials(self, arguments: dict) -> List[TextContent]:
        """Handle set_credentials tool."""
        try:
            self.username = arguments.get("username") or self.username
            self.password = arguments.get("password") or self.password
            self.api_key_name = arguments.get("api_key_name") or self.api_key_name
            self.api_key_value = arguments.get("api_key_value") or self.api_key_value
            self.login_url = arguments.get("login_url") or self.login_url
            
            if not self.username or not self.password:
                return [TextContent(type="text", text=json.dumps({
                    "status": "error",
                    "message": "Username and password are required"
                }, indent=2))]
            
            response = {
                "status": "success",
                "message": "Credentials stored successfully",
                "username": self.username,
                "login_url": self.login_url,
                "has_api_key": bool(self.api_key_name and self.api_key_value)
            }
            
            logger.info(f"✅ Credentials stored for user: {self.username}")
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
            
        except Exception as e:
            logger.error(f"Error setting credentials: {e}")
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2))]
    
    async def _handle_perform_login(self, arguments: dict) -> List[TextContent]:
        """Handle perform_login tool."""
        try:
            force_login = arguments.get("force_login", False)
            
            if not force_login and self.session_id:
                return [TextContent(type="text", text=json.dumps({
                    "status": "success",
                    "message": "Already authenticated",
                    "session_id": self.session_id
                }, indent=2))]
            
            if not self.username or not self.password:
                return [TextContent(type="text", text=json.dumps({
                    "status": "error",
                    "message": "No credentials available. Call set_credentials first."
                }, indent=2))]
            
            # Perform login
            success = await self._perform_login()
            
            if success:
                response = {
                    "status": "success",
                    "message": "Login successful",
                    "session_id": self.session_id,
                    "username": self.username
                }
                logger.info("✅ Login successful")
            else:
                response = {
                    "status": "error",
                    "message": "Login failed - check credentials and login URL"
                }
                logger.error("❌ Login failed")
            
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
            
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2))]
    
    async def _perform_login(self) -> bool:
        """Perform login and store session."""
        try:
            login_data = {
                "username": self.username,
                "password": self.password
            }
            
            response = requests.post(self.login_url, json=login_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                self.session_id = result.get('sessionId') or result.get('session_id') or result.get('token')
                return bool(self.session_id)
            
            return False
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    async def _execute_api_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute an API tool."""
        api_tool = self.api_tools[tool_name]
        
        # Build URL
        url = f"{self.api_specs[api_tool.spec_name].base_url}{api_tool.path}"
        
        # Replace path parameters
        for param_name, param_value in arguments.items():
            if f"{{{param_name}}}" in url:
                url = url.replace(f"{{{param_name}}}", str(param_value))
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        
        # Add authentication
        if self.session_id:
            headers["Authorization"] = f"Bearer {self.session_id}"
        elif self.api_key_name and self.api_key_value:
            headers[self.api_key_name] = self.api_key_value
        
        # Prepare request data
        request_data = None
        if "body" in arguments:
            request_data = arguments["body"]
        
        # Make request
        response = requests.request(
            method=api_tool.method,
            url=url,
            headers=headers,
            json=request_data,
            timeout=30
        )
        
        # Return result
        if response.status_code < 400:
            try:
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "data": response.json()
                }
            except:
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "data": response.text
                }
        else:
            return {
                "status": "error",
                "status_code": response.status_code,
                "message": response.text
            }
    
    def _register_spec_tools(self, spec_name: str, api_spec: APISpec):
        """Register tools for a specific API specification."""
        paths = api_spec.spec.get('paths', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    self._register_api_tool(spec_name, method, path, operation)
    
    def _register_api_tool(self, spec_name: str, method: str, path: str, operation: Dict[str, Any]):
        """Register a single API endpoint as a tool."""
        operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').strip('_')}")
        tool_name = f"{spec_name}_{operation_id}"
        
        # Build description
        summary = operation.get('summary', '')
        description = operation.get('description', '')
        
        tool_description = f"{method.upper()} {path}"
        if summary:
            tool_description += f"\n\nSummary: {summary}"
        if description:
            tool_description += f"\n\nDescription: {description}"
        
        # Extract parameters
        parameters = self._extract_parameters(operation)
        
        # Create tool
        api_tool = APITool(
            name=tool_name,
            description=tool_description,
            method=method.upper(),
            path=path,
            parameters=parameters,
            spec_name=spec_name
        )
        
        self.api_tools[tool_name] = api_tool
        logger.debug(f"🔧 Registered tool: {tool_name}")
    
    def _extract_parameters(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from OpenAPI operation."""
        parameters = {}
        
        # Path and query parameters
        for param in operation.get('parameters', []):
            param_name = param['name']
            param_schema = param.get('schema', {})
            
            param_def = {
                'type': param_schema.get('type', 'string'),
                'description': param.get('description', ''),
                'required': param.get('required', param.get('in') == 'path')
            }
            
            # Add schema properties
            for prop in ['enum', 'format', 'minimum', 'maximum', 'example', 'default']:
                if prop in param_schema:
                    param_def[prop] = param_schema[prop]
            
            parameters[param_name] = param_def
        
        # Request body
        request_body = operation.get('requestBody')
        if request_body:
            content = request_body.get('content', {})
            if 'application/json' in content:
                schema = content['application/json'].get('schema', {})
                
                body_param = {
                    'type': 'object',
                    'description': request_body.get('description', 'Request body'),
                    'required': request_body.get('required', False)
                }
                
                if 'properties' in schema:
                    body_param['properties'] = schema['properties']
                if 'required' in schema:
                    body_param['schema_required'] = schema['required']
                
                parameters['body'] = body_param
        
        return parameters
    
    async def run_stdio(self):
        """Run server with stdio transport."""
        logger.info("🚀 Starting Simple MCP Server with stdio transport...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="simple-openapi-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities()
                )
            )
    
    async def run_http(self, host: str = "localhost", port: int = 8000):
        """Run server with HTTP transport."""
        if not HTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available for HTTP transport")
        
        logger.info(f"🚀 Starting Simple MCP Server with HTTP transport on {host}:{port}...")
        
        app = web.Application()
        
        async def handle_mcp_request(request):
            """Handle MCP requests over HTTP."""
            try:
                data = await request.json()
                method = data.get('method')
                params = data.get('params', {})
                
                if method == 'tools/list':
                    # Get tools using the registered handler
                    tools = []
                    for tool_name, api_tool in self.api_tools.items():
                        mcp_parameters = {}
                        required_params = []
                        
                        for param_name, param_info in api_tool.parameters.items():
                            param_schema = {
                                "type": param_info.get('type', 'string'),
                                "description": param_info.get('description', ''),
                            }
                            
                            # Add common schema properties
                            for prop in ['enum', 'format', 'minimum', 'maximum', 'example', 'default']:
                                if prop in param_info:
                                    param_schema[prop] = param_info[prop]
                            
                            # Handle object properties for request body
                            if param_name == 'body' and param_info.get('type') == 'object':
                                if 'properties' in param_info:
                                    param_schema['properties'] = param_info['properties']
                                if 'schema_required' in param_info:
                                    param_schema['required'] = param_info['schema_required']
                            
                            mcp_parameters[param_name] = param_schema
                            
                            if param_info.get('required', False):
                                required_params.append(param_name)
                        
                        tool_dict = {
                            "name": tool_name,
                            "description": api_tool.description,
                            "inputSchema": {
                                "type": "object",
                                "properties": mcp_parameters,
                                "required": required_params,
                                "additionalProperties": False
                            }
                        }
                        tools.append(tool_dict)
                    
                    # Add authentication tools
                    auth_tools = [
                        {
                            "name": "set_credentials",
                            "description": "Set authentication credentials for API access.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "username": {"type": "string", "description": "Username for authentication"},
                                    "password": {"type": "string", "description": "Password for authentication"},
                                    "api_key_name": {"type": "string", "description": "API key header name"},
                                    "api_key_value": {"type": "string", "description": "API key value"},
                                    "login_url": {"type": "string", "description": "Login URL"}
                                },
                                "required": [],
                                "additionalProperties": False
                            }
                        },
                        {
                            "name": "perform_login",
                            "description": "Perform login using stored credentials.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "force_login": {"type": "boolean", "description": "Force login even if already authenticated", "default": False}
                                },
                                "required": [],
                                "additionalProperties": False
                            }
                        }
                    ]
                    tools.extend(auth_tools)
                    
                    return web.json_response({
                        'jsonrpc': '2.0',
                        'id': data.get('id'),
                        'result': {'tools': tools}
                    })
                    
                elif method == 'tools/call':
                    name = params.get('name')
                    arguments = params.get('arguments', {})
                    
                    # Handle authentication tools
                    if name == "set_credentials":
                        result = await self._handle_set_credentials(arguments)
                    elif name == "perform_login":
                        result = await self._handle_perform_login(arguments)
                    else:
                        # Handle API tools
                        if name not in self.api_tools:
                            result = [{'type': 'text', 'text': f'Tool not found: {name}'}]
                        else:
                            try:
                                api_result = await self._execute_api_tool(name, arguments)
                                result = [{'type': 'text', 'text': json.dumps(api_result, indent=2)}]
                            except Exception as e:
                                result = [{'type': 'text', 'text': f'Error: {str(e)}'}]
                    
                    # Convert TextContent objects to dicts if needed
                    content = []
                    for item in result:
                        if hasattr(item, 'model_dump'):
                            content.append(item.model_dump())
                        elif isinstance(item, dict):
                            content.append(item)
                        else:
                            content.append({'type': 'text', 'text': str(item)})
                    
                    return web.json_response({
                        'jsonrpc': '2.0',
                        'id': data.get('id'),
                        'result': {'content': content}
                    })
                    
                else:
                    return web.json_response({
                        'jsonrpc': '2.0',
                        'id': data.get('id'),
                        'error': {'code': -32601, 'message': 'Method not found'}
                    }, status=404)
                    
            except Exception as e:
                logger.error(f"HTTP request error: {e}")
                return web.json_response({
                    'jsonrpc': '2.0',
                    'id': data.get('id', None),
                    'error': {'code': -32603, 'message': str(e)}
                }, status=500)
        
        app.router.add_post('/mcp', handle_mcp_request)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"✅ Simple MCP Server running on http://{host}:{port}/mcp")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            await runner.cleanup()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Simple MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                       help="Transport method (default: stdio)")
    parser.add_argument("--host", default="localhost", help="HTTP host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    parser.add_argument("--openapi-dir", default="./openapi_specs", help="OpenAPI specs directory")
    
    args = parser.parse_args()
    
    server = SimpleMCPServer(openapi_dir=args.openapi_dir)
    
    if args.transport == "stdio":
        await server.run_stdio()
    else:
        await server.run_http(args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())