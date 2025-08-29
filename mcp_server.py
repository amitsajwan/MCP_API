#!/usr/bin/env python3
"""
MCP Server - Real MCP Protocol Implementation
Proper MCP server that follows the official MCP specification:
- Uses MCP protocol for tool registration and calling
- Loads OpenAPI specs and exposes them as MCP tools
- Handles authentication automatically
- Pure tool provider following MCP standards
"""

import os
import json
import yaml
import base64
import re
import logging
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import requests
from dataclasses import dataclass

# MCP Protocol imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Import config or create default
try:
    from config import config
except ImportError:
    # Create default config if not available
    class DefaultConfig:
        LOG_LEVEL = "INFO"
        OPENAPI_DIR = "./openapi_specs"
        REQUEST_TIMEOUT = 30
        MOCK_ALL = False
        MOCK_API_BASE_URL = "http://localhost:8080"
        DEFAULT_LOGIN_URL = "http://localhost:8080/auth/login"
        MCP_HOST = "localhost"
        MCP_PORT = 8080
        
        def validate(self):
            return True
    
    config = DefaultConfig()


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")


@dataclass
class APISpec:
    """API specification container."""
    name: str
    spec: Dict[str, Any]
    base_url: str
    file_path: Optional[str] = None


@dataclass
class APITool:
    """API tool representation."""
    name: str
    description: str
    method: str
    path: str
    parameters: Dict[str, Any]
    spec_name: str
    tags: List[str]
    summary: Optional[str] = None
    operation_id: Optional[str] = None


class MCPServer:
    """Real MCP Server implementation using official MCP protocol."""
    
    def __init__(self):
        self.server = Server("openapi-mcp-server")
        self.api_specs: Dict[str, APISpec] = {}
        self.api_tools: Dict[str, APITool] = {}
        self.sessions: Dict[str, requests.Session] = {}
        
        # Authentication state
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.api_key_name: Optional[str] = None
        self.api_key_value: Optional[str] = None
        self.login_url: Optional[str] = None
        
        # Initialize
        self._load_api_specs()
        self._register_mcp_tools()
    
    def _load_api_specs(self):
        """Load OpenAPI specifications from directory."""
        openapi_dir = Path(config.OPENAPI_DIR)
        if not openapi_dir.exists():
            logger.warning(f"OpenAPI directory not found: {openapi_dir}")
            return
        
        for spec_file in openapi_dir.glob("*.yaml"):
            try:
                with open(spec_file, 'r') as f:
                    spec_data = yaml.safe_load(f)
                
                spec_name = spec_file.stem
                base_url = self._get_base_url(spec_data, spec_name)
                
                api_spec = APISpec(
                    name=spec_name,
                    spec=spec_data,
                    base_url=base_url,
                    file_path=str(spec_file)
                )
                
                self.api_specs[spec_name] = api_spec
                
                # Register tools for this spec
                self._register_spec_tools(spec_name, api_spec)
                
                logger.info(f"Loaded API spec: {spec_name} -> {base_url}")
                
            except Exception as e:
                logger.error(f"Failed to load spec {spec_file}: {e}")
    
    def _get_base_url(self, spec_data: Dict[str, Any], spec_name: str) -> str:
        """Get base URL for API specification."""
        # Check for environment override
        env_key = f"FORCE_BASE_URL_{spec_name.upper()}"
        if os.getenv(env_key):
            return os.getenv(env_key)
        
        # Check for global override
        if os.getenv("FORCE_BASE_URL"):
            return os.getenv("FORCE_BASE_URL")
        
        # Use mock if configured
        if config.MOCK_ALL:
            return config.MOCK_API_BASE_URL
        
        # Extract from spec
        servers = spec_data.get('servers', [])
        if servers:
            return servers[0]['url']
        
        # Default fallback
        return f"http://localhost:8080"
    
    def _register_mcp_tools(self):
        """Register API endpoints as MCP tools using proper MCP protocol."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available MCP tools."""
            tools = []
            
            for tool_name, api_tool in self.api_tools.items():
                # Convert parameters to MCP format
                mcp_parameters = {}
                required_params = []
                
                for param_name, param_info in api_tool.parameters.items():
                    param_schema = {
                        "type": param_info.get('type', 'string'),
                        "description": param_info.get('description', ''),
                    }
                    
                    # Handle enum values if present
                    if 'enum' in param_info:
                        param_schema['enum'] = param_info['enum']
                    
                    # Handle format if present
                    if 'format' in param_info:
                        param_schema['format'] = param_info['format']
                    
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
            
            return tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Call an MCP tool by name."""
            if name not in self.api_tools:
                return [TextContent(type="text", text=f"Tool not found: {name}")]
            
            try:
                # Execute the tool in a separate thread to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._execute_tool, name, arguments)
                
                if result.get("status") == "success":
                    response_text = json.dumps(result.get("data", result), indent=2)
                    return [TextContent(type="text", text=response_text)]
                else:
                    error_msg = f"Tool execution failed: {result.get('message', 'Unknown error')}"
                    if result.get('status_code'):
                        error_msg += f" (HTTP {result['status_code']})"
                    return [TextContent(type="text", text=error_msg)]
                    
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _register_spec_tools(self, spec_name: str, api_spec: APISpec):
        """Register tools for a specific API specification."""
        paths = api_spec.spec.get('paths', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    self._register_mcp_tool(spec_name, method, path, operation, api_spec.base_url)
    
    def _register_mcp_tool(self, spec_name: str, method: str, path: str, operation: Dict[str, Any], base_url: str):
        """Register a single API endpoint as an MCP tool."""
        operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').strip('_')}")
        tool_name = f"{spec_name}_{operation_id}"
        
        # Clean up tool name to ensure it's valid
        tool_name = re.sub(r'[^a-zA-Z0-9_]', '_', tool_name)
        
        # Build description
        summary = operation.get('summary', '')
        description = operation.get('description', '')
        tags = operation.get('tags', [])
        
        tool_description = f"{summary}".strip()
        if description:
            tool_description += f"\n{description}".strip()
        if tags:
            tool_description += f"\nTags: {', '.join(tags)}"
        
        # Ensure description is not empty
        if not tool_description:
            tool_description = f"{method.upper()} {path}"
        
        # Build parameters
        parameters = self._extract_parameters(operation)
        
        # Create tool
        api_tool = APITool(
            name=tool_name,
            description=tool_description,
            method=method.upper(),
            path=path,
            parameters=parameters,
            spec_name=spec_name,
            tags=tags,
            summary=summary,
            operation_id=operation_id
        )
        
        self.api_tools[tool_name] = api_tool
        
        logger.debug(f"Registered MCP tool: {tool_name}")
    
    def _extract_parameters(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from OpenAPI operation."""
        parameters = {}
        
        # Path parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'path':
                param_name = param['name']
                param_schema = param.get('schema', {})
                parameters[param_name] = {
                    'type': param_schema.get('type', 'string'),
                    'description': param.get('description', ''),
                    'required': param.get('required', True)
                }
                
                # Add enum if present
                if 'enum' in param_schema:
                    parameters[param_name]['enum'] = param_schema['enum']
        
        # Query parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'query':
                param_name = param['name']
                param_schema = param.get('schema', {})
                parameters[param_name] = {
                    'type': param_schema.get('type', 'string'),
                    'description': param.get('description', ''),
                    'required': param.get('required', False)
                }
                
                # Add enum if present
                if 'enum' in param_schema:
                    parameters[param_name]['enum'] = param_schema['enum']
        
        # Header parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'header':
                param_name = param['name']
                param_schema = param.get('schema', {})
                parameters[f"header_{param_name}"] = {
                    'type': param_schema.get('type', 'string'),
                    'description': f"Header: {param.get('description', '')}",
                    'required': param.get('required', False)
                }
        
        # Request body
        request_body = operation.get('requestBody')
        if request_body:
            content = request_body.get('content', {})
            if 'application/json' in content:
                parameters['body'] = {
                    'type': 'object',
                    'description': request_body.get('description', 'Request body data'),
                    'required': request_body.get('required', False)
                }
        
        return parameters
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an API tool."""
        tool = self.api_tools[tool_name]
        spec = self.api_specs[tool.spec_name]
        
        # Ensure authentication
        if not self._ensure_authenticated():
            return {"status": "error", "message": "Authentication failed"}
        
        # Build request URL
        url = f"{spec.base_url.rstrip('/')}{tool.path}"
        
        # Replace path parameters
        for param_name, value in arguments.items():
            if param_name in tool.parameters and tool.parameters[param_name].get('type') != 'object':
                placeholder = f"{{{param_name}}}"
                if placeholder in url:
                    url = url.replace(placeholder, str(value))
        
        # Prepare request
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Add API key if configured
        if self.api_key_name and self.api_key_value:
            headers[self.api_key_name] = self.api_key_value
        
        # Add custom headers
        for param_name, value in arguments.items():
            if param_name.startswith('header_'):
                header_name = param_name[7:]  # Remove 'header_' prefix
                headers[header_name] = str(value)
        
        # Get session
        session = self.sessions.get(tool.spec_name)
        if not session:
            session = requests.Session()
            self.sessions[tool.spec_name] = session
        
        # Prepare request data
        request_data = None
        query_params = {}
        
        for param_name, value in arguments.items():
            if param_name == 'body':
                request_data = value
            elif param_name in tool.parameters and not param_name.startswith('header_'):
                param_info = tool.parameters[param_name]
                if param_info.get('type') != 'object':
                    # Only add to query params if it's not a path parameter
                    placeholder = f"{{{param_name}}}"
                    if placeholder not in tool.path:
                        query_params[param_name] = value
        
        # Make request
        try:
            logger.info(f"Making {tool.method} request to {url}")
            logger.debug(f"Query params: {query_params}")
            logger.debug(f"Request data: {request_data}")
            
            response = session.request(
                method=tool.method,
                url=url,
                headers=headers,
                params=query_params if query_params else None,
                json=request_data if request_data else None,
                timeout=config.REQUEST_TIMEOUT,
                verify=False
            )
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                result = response.json()
            except json.JSONDecodeError:
                result = response.text
            
            return {
                "status": "success",
                "data": result,
                "status_code": response.status_code,
                "headers": dict(response.headers)
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            status_code = None
            
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                try:
                    error_detail = e.response.json()
                    error_msg = f"{error_msg}: {error_detail}"
                except:
                    error_msg = f"{error_msg}: {e.response.text}"
            
            logger.error(f"API request failed: {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "status_code": status_code
            }
    
    def set_credentials(self, username: str, password: str, 
                       api_key_name: Optional[str] = None, api_key_value: Optional[str] = None,
                       login_url: Optional[str] = None):
        """Set authentication credentials."""
        self.username = username
        self.password = password
        self.api_key_name = api_key_name
        self.api_key_value = api_key_value
        self.login_url = login_url or config.DEFAULT_LOGIN_URL
        logger.info("Credentials set for authentication")
    
    def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid authentication session."""
        if self._has_valid_session():
            return True
        
        if not self.username or not self.password:
            logger.warning("No credentials set for authentication")
            return False
        
        return self._perform_login()
    
    def _has_valid_session(self) -> bool:
        """Check if we have a valid session."""
        for session in self.sessions.values():
            jsessionid = session.cookies.get("JSESSIONID")
            if jsessionid and jsessionid != "dummy_session_id":
                return True
        return False
    
    def _perform_login(self) -> bool:
        """Perform authentication login."""
        try:
            session = requests.Session()
            
            headers = {
                "Authorization": self._get_basic_auth_header(self.username, self.password),
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            
            if self.api_key_name and self.api_key_value:
                headers[self.api_key_name] = self.api_key_value
            
            response = session.post(self.login_url, headers=headers, verify=False)
            response.raise_for_status()
            
            # Extract JSESSIONID
            token = None
            if "set-cookie" in response.headers:
                match = re.search(r'JSESSIONID=([^;]+)', response.headers["set-cookie"])
                if match:
                    token = match.group(1)
            
            if token:
                logger.info("✅ Authentication successful")
                # Set session for all specs
                for spec_name in self.api_specs.keys():
                    self.sessions[spec_name] = session
                return True
            else:
                logger.error("No JSESSIONID found in login response")
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def _get_basic_auth_header(self, username: str, password: str) -> str:
        """Generate Basic Auth header."""
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    async def run(self):
        """Run the MCP server using stdio transport."""
        logger.info("Starting MCP server with stdio transport")
        logger.info(f"Loaded {len(self.api_specs)} API specifications")
        logger.info(f"Registered {len(self.api_tools)} MCP tools")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="openapi-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="OpenAPI MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    parser.add_argument("--host", default=config.MCP_HOST)
    parser.add_argument("--port", type=int, default=config.MCP_PORT)
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    parser.add_argument("--api-key-name", help="API key header name")
    parser.add_argument("--api-key-value", help="API key value")
    parser.add_argument("--login-url", help="Login URL for authentication")
    
    args = parser.parse_args()
    
    # Validate configuration
    if not config.validate():
        return 1
    
    # Create and configure server
    server = MCPServer()
    
    # Set credentials if provided
    if args.username and args.password:
        server.set_credentials(
            username=args.username,
            password=args.password,
            api_key_name=args.api_key_name,
            api_key_value=args.api_key_value,
            login_url=args.login_url
        )
    
    if args.transport == "stdio":
        try:
            asyncio.run(server.run())
        except KeyboardInterrupt:
            logger.info("Server shutdown by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            return 1
    else:
        # HTTP transport (for backward compatibility)
        logger.warning("HTTP transport is deprecated. Use stdio for proper MCP protocol.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())