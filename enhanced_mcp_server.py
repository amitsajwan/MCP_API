#!/usr/bin/env python3
"""
MCP Server - Enhanced Version with Critical Fixes
Minor but important improvements:
- Better error handling for missing OpenAPI specs
- Graceful handling of YAML parsing errors
- Improved logging and debugging
- Better exception handling in tool execution
- Fixed potential issues with empty specs directory
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
from mcp.server.lowlevel import NotificationOptions
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
    """Enhanced MCP Server implementation with better error handling."""
    
    def __init__(self):
        logger.info("🚀 Initializing MCP Server...")
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
        
        # Initialize with better error handling
        try:
            logger.info("📂 Loading API specifications...")
            self._load_api_specs()
            logger.info("🔧 Registering MCP tools...")
            self._register_mcp_tools()
            
            if self.api_tools:
                logger.info(f"✅ MCP Server initialized with {len(self.api_tools)} tools from {len(self.api_specs)} API specs")
            else:
                logger.warning("⚠️ MCP Server initialized with no API tools - only authentication tools available")
                
        except Exception as e:
            logger.error(f"❌ Error during server initialization: {e}")
            logger.info("Server will continue with minimal functionality (authentication only)")
    
    def _load_api_specs(self):
        """Load OpenAPI specifications from directory with better error handling."""
        openapi_dir = Path(config.OPENAPI_DIR)
        
        if not openapi_dir.exists():
            logger.warning(f"📂 OpenAPI directory not found: {openapi_dir}")
            logger.info("Creating OpenAPI specs directory...")
            try:
                openapi_dir.mkdir(parents=True, exist_ok=True)
                
                # Create a sample spec to help users get started
                sample_spec_content = """
openapi: 3.0.0
info:
  title: Sample API
  version: 1.0.0
  description: Sample API specification for testing
servers:
  - url: http://localhost:8080
    description: Local development server
paths:
  /health:
    get:
      summary: Health check endpoint
      description: Check if the API is running
      responses:
        '200':
          description: API is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: "healthy"
  /info:
    get:
      summary: Get API information
      description: Get basic information about the API
      responses:
        '200':
          description: API information
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  version:
                    type: string
"""
                sample_file = openapi_dir / "sample.yaml"
                with open(sample_file, 'w') as f:
                    f.write(sample_spec_content.strip())
                logger.info(f"✅ Created sample OpenAPI spec: {sample_file}")
                
            except Exception as e:
                logger.error(f"Failed to create OpenAPI directory: {e}")
                return
        
        # Look for YAML and JSON files
        spec_files = list(openapi_dir.glob("*.yaml")) + list(openapi_dir.glob("*.yml")) + list(openapi_dir.glob("*.json"))
        
        if not spec_files:
            logger.warning(f"📂 No OpenAPI specification files found in {openapi_dir}")
            logger.info("Add .yaml, .yml, or .json OpenAPI specs to this directory")
            return
        
        logger.info(f"Found {len(spec_files)} specification file(s)")
        
        for spec_file in spec_files:
            try:
                logger.debug(f"Loading spec file: {spec_file}")
                
                with open(spec_file, 'r', encoding='utf-8') as f:
                    if spec_file.suffix.lower() == '.json':
                        spec_data = json.load(f)
                    else:
                        spec_data = yaml.safe_load(f)
                
                if not spec_data:
                    logger.warning(f"⚠️ Empty or invalid spec file: {spec_file}")
                    continue
                
                # Validate basic structure
                if 'openapi' not in spec_data and 'swagger' not in spec_data:
                    logger.warning(f"⚠️ Invalid OpenAPI spec (missing openapi/swagger field): {spec_file}")
                    continue
                
                if 'paths' not in spec_data or not spec_data['paths']:
                    logger.warning(f"⚠️ No paths found in spec: {spec_file}")
                    continue
                
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
                tools_registered = self._register_spec_tools(spec_name, api_spec)
                
                logger.info(f"✅ Loaded API spec: {spec_name} -> {base_url} ({tools_registered} tools)")
                
            except yaml.YAMLError as e:
                logger.error(f"❌ YAML parsing error in {spec_file}: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parsing error in {spec_file}: {e}")
            except Exception as e:
                logger.error(f"❌ Failed to load spec {spec_file}: {e}")
    
    def _get_base_url(self, spec_data: Dict[str, Any], spec_name: str) -> str:
        """Get base URL for API specification."""
        # Check for environment override
        env_key = f"FORCE_BASE_URL_{spec_name.upper()}"
        if os.getenv(env_key):
            logger.debug(f"Using environment override for {spec_name}: {os.getenv(env_key)}")
            return os.getenv(env_key)
        
        # Check for global override
        if os.getenv("FORCE_BASE_URL"):
            logger.debug(f"Using global environment override: {os.getenv('FORCE_BASE_URL')}")
            return os.getenv("FORCE_BASE_URL")
        
        # Use mock if configured
        if getattr(config, 'MOCK_ALL', False):
            logger.debug(f"Using mock URL for {spec_name}: {config.MOCK_API_BASE_URL}")
            return config.MOCK_API_BASE_URL
        
        # Extract from spec
        servers = spec_data.get('servers', [])
        if servers and isinstance(servers[0], dict) and 'url' in servers[0]:
            url = servers[0]['url']
            logger.debug(f"Using spec server URL for {spec_name}: {url}")
            return url
        
        # Default fallback
        fallback_url = "http://localhost:8080"
        logger.debug(f"Using fallback URL for {spec_name}: {fallback_url}")
        return fallback_url
    
    def _register_mcp_tools(self):
        """Register API endpoints as MCP tools using proper MCP protocol."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available MCP tools."""
            tools = []
            
            # Add API tools
            for tool_name, api_tool in self.api_tools.items():
                try:
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
                    
                except Exception as e:
                    logger.error(f"Error creating tool {tool_name}: {e}")
            
            # Add authentication tools
            tools.append(Tool(
                name="set_credentials",
                description="Set authentication credentials for API access",
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
                            "description": "API key header name (optional)"
                        },
                        "api_key_value": {
                            "type": "string",
                            "description": "API key value (optional)"
                        },
                        "login_url": {
                            "type": "string",
                            "description": "Login URL (optional)"
                        }
                    },
                    "required": ["username", "password"],
                    "additionalProperties": False
                }
            ))
            
            tools.append(Tool(
                name="perform_login",
                description="Perform authentication login using stored credentials",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ))
            
            logger.debug(f"Returning {len(tools)} tools ({len(self.api_tools)} API + 2 auth)")
            return tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Call an MCP tool by name."""
            logger.info(f"🔧 Executing tool: {name}")
            logger.debug(f"Arguments: {arguments}")
            
            if name == "set_credentials":
                try:
                    username = arguments.get("username")
                    password = arguments.get("password")
                    api_key_name = arguments.get("api_key_name")
                    api_key_value = arguments.get("api_key_value")
                    login_url = arguments.get("login_url")
                    
                    if not username or not password:
                        raise ValueError("Username and password are required")
                    
                    self.set_credentials(username, password, api_key_name, api_key_value, login_url)
                    
                    response = {
                        "status": "success",
                        "message": "Credentials set successfully",
                        "username": username,
                        "login_url": login_url or getattr(config, 'DEFAULT_LOGIN_URL', 'http://localhost:8080/auth/login')
                    }
                    
                    logger.info(f"✅ Credentials set successfully for user: {username}")
                    return [TextContent(type="text", text=json.dumps(response, indent=2))]
                    
                except Exception as e:
                    logger.error(f"❌ Error setting credentials: {e}")
                    error_response = {
                        "status": "error",
                        "message": f"Error setting credentials: {str(e)}"
                    }
                    return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
                    
            elif name == "perform_login":
                try:
                    if not self.username or not self.password:
                        raise ValueError("Credentials not set. Call set_credentials first.")
                    
                    success = self._perform_login()
                    if success:
                        logger.info("✅ Login performed successfully")
                        response = {"status": "success", "message": "Login performed successfully"}
                    else:
                        logger.warning("⚠️ Login failed")
                        response = {"status": "error", "message": "Login failed - check credentials and URL"}
                    return [TextContent(type="text", text=json.dumps(response, indent=2))]
                except Exception as e:
                    logger.error(f"❌ Error performing login: {e}")
                    error_response = {"status": "error", "message": f"Error performing login: {str(e)}"}
                    return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
            
            # Check if it's an API tool
            if name not in self.api_tools:
                logger.warning(f"❌ Tool not found: {name}")
                available_tools = list(self.api_tools.keys()) + ["set_credentials", "perform_login"]
                error_response = {
                    "status": "error",
                    "message": f"Tool '{name}' not found",
                    "available_tools": available_tools[:10]  # Show first 10 tools
                }
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
            
            try:
                # Execute the tool in a separate thread to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._execute_tool, name, arguments)
                
                if result.get("status") == "success":
                    response_text = json.dumps(result.get("data", result), indent=2)
                    logger.info(f"✅ Tool {name} executed successfully")
                    return [TextContent(type="text", text=response_text)]
                else:
                    error_msg = f"Tool execution failed: {result.get('message', 'Unknown error')}"
                    if result.get('status_code'):
                        error_msg += f" (HTTP {result['status_code']})"
                    logger.error(f"❌ Tool {name} failed: {error_msg}")
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                    
            except Exception as e:
                logger.error(f"❌ Error executing tool {name}: {e}", exc_info=True)
                error_response = {
                    "status": "error",
                    "message": f"Unexpected error executing {name}: {str(e)}"
                }
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    def _register_spec_tools(self, spec_name: str, api_spec: APISpec) -> int:
        """Register tools for a specific API specification. Returns number of tools registered."""
        paths = api_spec.spec.get('paths', {})
        tool_count = 0
        
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
                
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch'] and isinstance(operation, dict):
                    try:
                        self._register_mcp_tool(spec_name, method, path, operation, api_spec.base_url)
                        tool_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to register tool for {method.upper()} {path}: {e}")
        
        return tool_count
    
    def _register_mcp_tool(self, spec_name: str, method: str, path: str, operation: Dict[str, Any], base_url: str):
        """Register a single API endpoint as an MCP tool."""
        operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').strip('_')}")
        tool_name = f"{spec_name}_{operation_id}"
        
        # Clean up tool name to ensure it's valid
        tool_name = re.sub(r'[^a-zA-Z0-9_]', '_', tool_name)
        
        # Ensure tool name is unique
        original_name = tool_name
        counter = 1
        while tool_name in self.api_tools:
            tool_name = f"{original_name}_{counter}"
            counter += 1
        
        # Build description
        summary = operation.get('summary', '').strip()
        description = operation.get('description', '').strip()
        tags = operation.get('tags', [])
        
        tool_description = summary if summary else f"{method.upper()} {path}"
        if description and description != summary:
            tool_description += f"\n{description}"
        if tags:
            tool_description += f"\nTags: {', '.join(tags)}"
        
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
        logger.debug(f"🔧 Registered tool: {tool_name} ({method.upper()} {path})")
    
    def _extract_parameters(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from OpenAPI operation with better error handling."""
        parameters = {}
        
        try:
            # Path parameters
            for param in operation.get('parameters', []):
                if not isinstance(param, dict):
                    continue
                    
                if param.get('in') == 'path':
                    param_name = param.get('name')
                    if not param_name:
                        continue
                        
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
                if not isinstance(param, dict):
                    continue
                    
                if param.get('in') == 'query':
                    param_name = param.get('name')
                    if not param_name:
                        continue
                        
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
                if not isinstance(param, dict):
                    continue
                    
                if param.get('in') == 'header':
                    param_name = param.get('name')
                    if not param_name:
                        continue
                        
                    param_schema = param.get('schema', {})
                    parameters[f"header_{param_name}"] = {
                        'type': param_schema.get('type', 'string'),
                        'description': f"Header: {param.get('description', '')}",
                        'required': param.get('required', False)
                    }
            
            # Request body
            request_body = operation.get('requestBody')
            if request_body and isinstance(request_body, dict):
                content = request_body.get('content', {})
                if 'application/json' in content:
                    parameters['body'] = {
                        'type': 'object',
                        'description': request_body.get('description', 'Request body data'),
                        'required': request_body.get('required', False)
                    }
        
        except Exception as e:
            logger.warning(f"Error extracting parameters from operation: {e}")
        
        return parameters
    
    # ... [Rest of the methods remain the same as your original code] ...
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an API tool."""
        try:
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
            logger.info(f"Making {tool.method} request to {url}")
            logger.debug(f"Query params: {query_params}")
            logger.debug(f"Request data: {request_data}")
            
            response = session.request(
                method=tool.method,
                url=url,
                headers=headers,
                params=query_params if query_params else None,
                json=request_data if request_data else None,
                timeout=getattr(config, 'REQUEST_TIMEOUT', 30),
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
        except Exception as e:
            logger.error(f"Unexpected error executing tool {tool_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
    
    def set_credentials(self, username: str, password: str, 
                       api_key_name: Optional[str] = None, api_key_value: Optional[str] = None,
                       login_url: Optional[str] = None):
        """Set authentication credentials."""
        self.username = username
        self.password = password
        self.api_key_name = api_key_name
        self.api_key_value = api_key_value
        self.login_url = login_url or getattr(config, 'DEFAULT_LOGIN_URL', 'http://localhost:8080/auth/login')
        logger.info(f"Credentials set for authentication (user: {username})")
    
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
            
            logger.debug(f"Attempting login to: {self.login_url}")
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
        logger.info("🚀 Starting MCP server with stdio transport")
        logger.info(f"📊 Server status:")
        logger.info(f"  • API specifications: {len(self.api_specs)}")
        logger.info(f"  • API tools: {len(self.api_tools)}")
        logger.info(f"  • Authentication tools: 2")
        logger.info(f"  • Total tools available: {len(self.api_tools) + 2}")
        
        if self.api_specs:
            logger.info("📋 Loaded API specs:")
            for spec_name, spec in self.api_specs.items():
                tool_count = len([t for t in self.api_tools.values() if t.spec_name == spec_name])
                logger.info(f"  • {spec_name}: {tool_count} tools -> {spec.base_url}")
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="openapi-mcp-server",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities=None,
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"❌ Error in server run loop: {e}")
            raise


def main():
    """Main entry point with enhanced error handling."""
    parser = argparse.ArgumentParser(description="OpenAPI MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    parser.add_argument("--host", default=getattr(config, 'MCP_HOST', 'localhost'))
    parser.add_argument("--port", type=int, default=getattr(config, 'MCP_PORT', 8080))
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    parser.add_argument("--api-key-name", help="API key header name")
    parser.add_argument("--api-key-value", help="API key value")
    parser.add_argument("--login-url", help="Login URL for authentication")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🐛 Debug logging enabled")
    
    try:
        logger.info("🔧 Validating configuration...")
        if not config.validate():
            logger.error("❌ Configuration validation failed")
            return 1
        
        logger.info("✅ Configuration validated")
        
        # Create and configure server
        logger.info("🏗️ Creating MCP server...")
        server = MCPServer()
        
        # Set credentials if provided
        if args.username and args.password:
            logger.info(f"🔑 Setting credentials from command line for user: {args.username}")
            server.set_credentials(
                username=args.username,
                password=args.password,
                api_key_name=args.api_key_name,
                api_key_value=args.api_key_value,
                login_url=args.login_url
            )
        
        if args.transport == "stdio":
            try:
                # Run with proper exception handling
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(server.run())
            except KeyboardInterrupt:
                logger.info("👋 Server shutdown by user")
            except BrokenPipeError:
                logger.info("🔌 Client disconnected (broken pipe)")
            except ConnectionResetError:
                logger.info("🔌 Client disconnected (connection reset)")
            except Exception as e:
                logger.error(f"❌ Server error: {e}", exc_info=True)
                return 1
            finally:
                try:
                    loop.close()
                except:
                    pass
        else:
            # HTTP transport (for backward compatibility)
            logger.warning("⚠️ HTTP transport is deprecated. Use stdio for proper MCP protocol.")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())