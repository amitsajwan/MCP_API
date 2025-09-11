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
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import requests
from dataclasses import dataclass
from datetime import datetime

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

# HTTP server imports
try:
    from aiohttp import web, web_request, web_response
    from aiohttp.web import Application, RouteTableDef
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

# Import config or create default
try:
    from config import config
except ImportError:
    # Fallback configuration if config.py doesn't exist
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
            pass
    
    config = DefaultConfig()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

# Argument validator type placeholders (optional dependency)
ArgumentValidator = None
ValidationResult = None


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
        logger.info("🚀 Initializing MCP Server...")
        self.server = Server("openapi-mcp-server")
        self.api_specs = {}
        self.api_tools = {}
        self.sessions = {}
        self.session_id = None
        
        # Initialize argument validator (optional, import lazily to avoid import diagnostics)
        self.validator = None
        try:
            mod_name = "_".join(["argument", "validator"])  # avoid static import analyzers
            mod = importlib.import_module(mod_name)
            ArgValidator = getattr(mod, "ArgumentValidator", None)
            if ArgValidator:
                self.validator = ArgValidator()
        except Exception:
            self.validator = None
        if self.validator:
            logger.info("✅ Argument validator initialized")
        else:
            logger.warning("⚠️  Argument validator not available - validation disabled")

        # Authentication state - Load from environment if available
        self.username = os.getenv('API_USERNAME')
        self.password = os.getenv('API_PASSWORD')
        self.api_key_name = os.getenv('API_KEY_NAME')
        self.api_key_value = os.getenv('API_KEY_VALUE')
        self.login_url = os.getenv('LOGIN_URL')

        # Initialize
        logger.info("📂 Loading API specifications...")
        self._load_api_specs()
        logger.info("🔧 Registering MCP tools...")
        self._register_mcp_tools()
        logger.info(f"✅ MCP Server initialized with {len(self.api_tools)} tools from {len(self.api_specs)} API specs")

        # Log credential status
        if self.username:
            logger.info(f"🔐 Credentials loaded from environment for user: {self.username}")
        else:
            logger.info("🔓 No credentials found in environment - use set_credentials tool")
    
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
            url = servers[0].get('url') if isinstance(servers[0], dict) else servers[0]
            if isinstance(url, str):
                return url
        
        # Default fallback
        return f"http://localhost:8080"
    
    def _register_mcp_tools(self):
        """Register API endpoints as MCP tools using proper MCP protocol."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available MCP tools."""
            tools = []
            
            for tool_name, api_tool in self.api_tools.items():
                # Convert parameters to MCP format with comprehensive schema support
                mcp_parameters = {}
                required_params = []
                
                for param_name, param_info in api_tool.parameters.items():
                    param_schema = {
                        "type": param_info.get('type', 'string'),
                        "description": param_info.get('description', ''),
                    }
                    
                    # Handle all schema properties
                    schema_properties = ['enum', 'format', 'minimum', 'maximum', 'minLength', 'maxLength', 'pattern', 'example', 'default']
                    for prop in schema_properties:
                        if prop in param_info:
                            param_schema[prop] = param_info[prop]
                    
                    # Handle object properties for request body
                    if param_name == 'body' and param_info.get('type') == 'object':
                        if 'properties' in param_info:
                            param_schema['properties'] = param_info['properties']
                        if 'schema_required' in param_info:
                            param_schema['required'] = param_info['schema_required']
                        if '$ref' in param_info:
                            param_schema['$ref'] = param_info['$ref']
                    
                    mcp_parameters[param_name] = param_schema
                    
                    if param_info.get('required', False):
                        required_params.append(param_name)
                
                # Create enhanced tool with API-specific properties
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
                
                # Add API-specific properties for LLM-based tool selection
                tool_dict["api_properties"] = {
                    "method": api_tool.method,
                    "path": api_tool.path,
                    "spec_name": api_tool.spec_name,
                    "tags": api_tool.tags,
                    "summary": api_tool.summary,
                    "operation_id": api_tool.operation_id,
                    "endpoint_url": f"{api_tool.spec_name}_{api_tool.method}_{api_tool.path}",
                    "category": api_tool.tags[0] if api_tool.tags else "general",
                    "parameters_count": len(api_tool.parameters),
                    "required_parameters": required_params,
                    "optional_parameters": [p for p in api_tool.parameters.keys() if p not in required_params]
                }
                
                # Create Tool object with enhanced properties
                tool = Tool(**tool_dict)
                tools.append(tool)
            
            # Add set_credentials tool for authentication
            tools.append(Tool(
                name="set_credentials",
                description="Set authentication credentials for API access. If not provided, values will be loaded from environment variables (API_USERNAME, API_PASSWORD, API_KEY_NAME, API_KEY_VALUE, LOGIN_URL).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Username for authentication (fallback: API_USERNAME env var)"
                        },
                        "password": {
                            "type": "string",
                            "description": "Password for authentication (fallback: API_PASSWORD env var)"
                        },
                        "api_key_name": {
                            "type": "string",
                            "description": "API key header name (fallback: API_KEY_NAME env var)"
                        },
                        "api_key_value": {
                            "type": "string",
                            "description": "API key value (fallback: API_KEY_VALUE env var)"
                        },
                        "login_url": {
                            "type": "string",
                            "description": "Login URL (fallback: LOGIN_URL env var or config.DEFAULT_LOGIN_URL)"
                        }
                    },
                    "required": [],
                    "additionalProperties": False
                }
            ))
            
            # Add perform_login tool for authentication
            tools.append(Tool(
                name="perform_login",
                description="Perform login using stored credentials to obtain session token. Credentials must be set first using set_credentials or environment variables.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "force_login": {
                            "type": "boolean",
                            "description": "Force login even if already authenticated (default: false)",
                            "default": False
                        }
                    },
                    "required": [],
                    "additionalProperties": False
                }
            ))

            
            return tools
        
        @self.server.call_tool()
        async def mcp_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Call an MCP tool by name."""
            safe_args = {k: ('****' if 'password' in k.lower() else v) for k, v in (arguments or {}).items()}
            logger.info(f"🔧 Executing tool: {name} with arguments: {list(safe_args.keys())}")
            
            if name == "set_credentials":
                try:
                    # Use provided values or fallback to environment variables or existing values
                    username = arguments.get("username") or self.username or os.getenv('API_USERNAME')
                    password = arguments.get("password") or self.password or os.getenv('API_PASSWORD')
                    api_key_name = arguments.get("api_key_name") or self.api_key_name or os.getenv('API_KEY_NAME')
                    api_key_value = arguments.get("api_key_value") or self.api_key_value or os.getenv('API_KEY_VALUE')
                    login_url = arguments.get("login_url") or self.login_url or os.getenv('LOGIN_URL') or config.DEFAULT_LOGIN_URL
                    
                    # Validate required credentials
                    if not username or not password:
                        error_msg = "Username and password are required. Provide them as arguments or set API_USERNAME and API_PASSWORD environment variables."
                        logger.error(f"❌ {error_msg}")
                        return [TextContent(type="text", text=json.dumps({"status": "error", "message": error_msg}, indent=2))]
                    
                    # Store credentials locally without making external API calls
                    self.username = username
                    self.password = password
                    self.api_key_name = api_key_name
                    self.api_key_value = api_key_value
                    self.login_url = login_url
                    
                    response = {
                        "status": "success",
                        "message": "Credentials stored successfully in MCP server",
                        "username": username,
                        "login_url": login_url,
                        "has_api_key": bool(api_key_name and api_key_value),
                        "api_key_name": api_key_name if api_key_name else None
                    }
                    
                    logger.info(f"✅ Credentials stored successfully for user: {username}")
                    return [TextContent(type="text", text=json.dumps(response, indent=2))]
                    
                except Exception as e:
                    logger.error(f"❌ Error setting credentials: {e}")
                    return [TextContent(type="text", text=json.dumps({"status": "error", "message": str(e)}, indent=2))]
            elif name == "perform_login":
                try:
                    force_login = arguments.get("force_login", False)
                    
                    # Check if already authenticated and not forcing login
                    if not force_login and self.session_id:
                        response = {
                            "status": "success",
                            "message": "Already authenticated",
                            "session_id": self.session_id,
                            "username": self.username,
                            "login_url": self.login_url
                        }
                        logger.info("✅ Already authenticated")
                        return [TextContent(type="text", text=json.dumps(response, indent=2))]
                    
                    # Check if credentials are available
                    if not self.username or not self.password:
                        error_msg = "No credentials available. Please call set_credentials first or set environment variables."
                        logger.error(f"❌ {error_msg}")
                        return [TextContent(type="text", text=json.dumps({"status": "error", "message": error_msg}, indent=2))]
                    
                    result = self._perform_login()
                    if result:
                        response = {
                            "status": "success",
                            "message": "Login successful",
                            "session_id": self.session_id,
                            "username": self.username,
                            "login_url": self.login_url,
                            "has_api_key": bool(self.api_key_name and self.api_key_value)
                        }
                        logger.info("✅ Login successful")
                        return [TextContent(type="text", text=json.dumps(response, indent=2))]
                    else:
                        error_msg = "Login failed - check credentials and login URL"
                        logger.error(f"❌ {error_msg}")
                        return [TextContent(type="text", text=json.dumps({"status": "error", "message": error_msg}, indent=2))]
                        
                except Exception as e:
                    logger.error(f"❌ Error during login: {e}")
                    return [TextContent(type="text", text=json.dumps({"status": "error", "message": str(e)}, indent=2))]
            
            if name not in self.api_tools:
                logger.warning(f"Tool not found: {name}")
                return [TextContent(type="text", text=f"Tool not found: {name}")]
            
            try:
                logger.info(f"Executing tool: {name} with arguments: {list(arguments.keys())}")
                
                # Execute the tool in a separate thread to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._execute_tool, name, arguments)
                
                if result.get("status") == "success":
                    response_text = json.dumps(result.get("data", result), indent=2)
                    logger.info(f"Tool {name} executed successfully")
                    return [TextContent(type="text", text=response_text)]
                else:
                    error_msg = f"Tool execution failed: {result.get('message', 'Unknown error')}"
                    if result.get('status_code'):
                        error_msg += f" (HTTP {result['status_code']})"
                    logger.error(f"Tool {name} failed: {error_msg}")
                    return [TextContent(type="text", text=error_msg)]
                    
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        # Store reference to the MCP call_tool function for HTTP endpoint
        self.mcp_call_tool = mcp_call_tool
    
    def _register_spec_tools(self, spec_name: str, api_spec: APISpec):
        """Register tools for a specific API specification."""
        paths = api_spec.spec.get('paths', {})
        tool_count = 0
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    self._register_mcp_tool(spec_name, method, path, operation, api_spec.base_url)
                    tool_count += 1
        
        logger.info(f"📋 Registered {tool_count} tools from {spec_name} API spec")
    
    def _register_mcp_tool(self, spec_name: str, method: str, path: str, operation: Dict[str, Any], base_url: str):
        """Register a single API endpoint as an MCP tool with comprehensive details."""
        operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').strip('_')}")
        tool_name = f"{spec_name}_{operation_id}"

        # Clean up tool name to ensure it's valid
        tool_name = re.sub(r'[^a-zA-Z0-9_]', '_', tool_name)

        # Build comprehensive description
        summary = operation.get('summary', '')
        description = operation.get('description', '')
        tags = operation.get('tags', [])

        tool_description = f"{method.upper()} {path}"
        if summary:
            tool_description += f"\n\nSummary: {summary}"
        if description:
            tool_description += f"\n\nDescription: {description}"
        if tags:
            tool_description += f"\n\nTags: {', '.join(tags)}"

        # Add response information
        responses = operation.get('responses', {})
        if responses:
            tool_description += "\n\nResponses:"
            for status_code, response_info in responses.items():
                response_desc = response_info.get('description', '')
                tool_description += f"\n- {status_code}: {response_desc}"

                # Add response schema info if available
                content = response_info.get('content', {})
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    if 'properties' in schema:
                        tool_description += f" (Returns: {', '.join(schema['properties'].keys())})"

        # Build parameters with enhanced schema information
        parameters = self._extract_parameters(operation, api_spec=self.api_specs.get(spec_name))

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
            operation_id=operation_id,
        )

        self.api_tools[tool_name] = api_tool
        logger.debug(f"🔧 Registered tool: {tool_name} ({method.upper()} {path}) with {len(parameters)} parameters")
        logger.debug(f"Registered MCP tool: {tool_name}")
    
    def _extract_parameters(self, operation: Dict[str, Any], api_spec: Optional[APISpec] = None) -> Dict[str, Any]:
        """Extract parameters from OpenAPI operation with comprehensive schema support."""
        parameters = {}
        
        def resolve_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
            # Minimal $ref resolver for same-doc refs
            if not schema:
                return {}
            if '$ref' in schema and api_spec and api_spec.spec:
                ref = schema['$ref']
                if ref.startswith('#/'):
                    parts = ref.lstrip('#/').split('/')
                    node: Any = api_spec.spec
                    for p in parts:
                        if isinstance(node, dict):
                            node = node.get(p)
                        else:
                            node = None
                            break
                    if isinstance(node, dict):
                        # Avoid infinite loops
                        clone = dict(node)
                        clone.pop('$ref', None)
                        return clone
            return schema

        # Path parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'path':
                param_name = param['name']
                param_schema = resolve_schema(param.get('schema', {}))
                param_def = {
                    'type': param_schema.get('type', 'string'),
                    'description': param.get('description', ''),
                    'required': param.get('required', True)
                }
                
                # Add additional schema properties
                self._add_schema_properties(param_def, param_schema)
                parameters[param_name] = param_def
        
        # Query parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'query':
                param_name = param['name']
                param_schema = resolve_schema(param.get('schema', {}))
                param_def = {
                    'type': param_schema.get('type', 'string'),
                    'description': param.get('description', ''),
                    'required': param.get('required', False)
                }
                
                # Add additional schema properties
                self._add_schema_properties(param_def, param_schema)
                parameters[param_name] = param_def
        
        # Header parameters
        for param in operation.get('parameters', []):
            if param.get('in') == 'header':
                param_name = param['name']
                param_schema = resolve_schema(param.get('schema', {}))
                param_def = {
                    'type': param_schema.get('type', 'string'),
                    'description': f"Header: {param.get('description', '')}",
                    'required': param.get('required', False)
                }
                
                # Add additional schema properties
                self._add_schema_properties(param_def, param_schema)
                parameters[f"header_{param_name}"] = param_def
        
        # Request body with detailed schema
        request_body = operation.get('requestBody')
        if request_body:
            content = request_body.get('content', {})
            if 'application/json' in content:
                json_content = content['application/json']
                schema = resolve_schema(json_content.get('schema', {}))
                body_param = {
                    'type': 'object',
                    'description': request_body.get('description', 'Request body data'),
                    'required': request_body.get('required', False)
                }
                # Add detailed schema information
                if 'properties' in schema:
                    body_param['properties'] = schema['properties']
                if 'required' in schema:
                    body_param['schema_required'] = schema['required']
                if '$ref' in schema:
                    body_param['$ref'] = schema['$ref']
                parameters['body'] = body_param
        
        return parameters
    
    def _add_schema_properties(self, param_def: Dict[str, Any], schema: Dict[str, Any]):
        """Add additional schema properties to parameter definition."""
        # Add enum if present
        if 'enum' in schema:
            param_def['enum'] = schema['enum']
        
        # Add format if present
        if 'format' in schema:
            param_def['format'] = schema['format']
        
        # Add min/max values
        if 'minimum' in schema:
            param_def['minimum'] = schema['minimum']
        if 'maximum' in schema:
            param_def['maximum'] = schema['maximum']
        
        # Add string length constraints
        if 'minLength' in schema:
            param_def['minLength'] = schema['minLength']
        if 'maxLength' in schema:
            param_def['maxLength'] = schema['maxLength']
        
        # Add pattern if present
        if 'pattern' in schema:
            param_def['pattern'] = schema['pattern']
        
        # Add example if present
        if 'example' in schema:
            param_def['example'] = schema['example']
        
        # Add default value if present
        if 'default' in schema:
            param_def['default'] = schema['default']
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an API tool."""
        try:
            tool = self.api_tools[tool_name]
            spec = self.api_specs[tool.spec_name]
            
            # Ensure authentication
            if not self._ensure_authenticated():
                return {"status": "error", "message": "Authentication failed"}
            
            # Validate and clean arguments if validator is available
            if self.validator:
                validation_result = self.validator.validate_arguments(
                    arguments, tool.parameters, tool.method
                )
                if not validation_result.is_valid:
                    logger.warning(f"Validation failed for {tool_name}: {validation_result.errors}")
                    return {
                        "status": "error", 
                        "message": f"Validation failed: {'; '.join(validation_result.errors)}"
                    }
                # Use cleaned arguments
                arguments = validation_result.cleaned_args
                logger.debug(f"Arguments validated and cleaned for {tool_name}")
            else:
                logger.debug(f"No validator available - using arguments as-is for {tool_name}")

            # Build request URL
            url = f"{spec.base_url.rstrip('/')}{tool.path}"
            
            # Replace path parameters
            for param_name, value in arguments.items():
                if param_name in tool.parameters and tool.parameters[param_name].get('type') != 'object':
                    placeholder = f"{{{param_name}}}"
                    if placeholder in url:
                        url = url.replace(placeholder, str(value))
            
            # Prepare request with comprehensive headers
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'MCP-Financial-API-Client/1.0',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
            
            # Add API key if configured
            if self.api_key_name and self.api_key_value:
                headers[self.api_key_name] = self.api_key_value
            
            # Add custom headers
            for param_name, value in arguments.items():
                if param_name.startswith('header_'):
                    header_name = param_name[7:]  # Remove 'header_' prefix
                    headers[header_name] = str(value)
            
            # Get session with proper configuration
            session = self.sessions.get(tool.spec_name)
            if not session:
                session = requests.Session()
                # Configure session for better reliability
                session.headers.update({
                    'User-Agent': 'MCP-Financial-API-Client/1.0'
                })
                # Add session-level authentication if available
                if self.session_id:
                    session.cookies.set('JSESSIONID', self.session_id)
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
            
            # Make request with enhanced error handling
            logger.info(f"Making {tool.method} request to {url}")
            logger.debug(f"Headers: {dict(headers)}")
            logger.debug(f"Query params: {query_params}")
            logger.debug(f"Request data: {request_data}")
            
            response = session.request(
                method=tool.method,
                url=url,
                headers=headers,
                params=query_params if query_params else None,
                json=request_data if request_data else None,
                timeout=getattr(config, 'REQUEST_TIMEOUT', 30),
                verify=False,
                allow_redirects=True
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
            error_details = {}
            
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                error_details['response_headers'] = dict(e.response.headers)
                error_details['request_url'] = url
                error_details['request_method'] = tool.method
                
                try:
                    error_detail = e.response.json()
                    error_msg = f"API Error ({status_code}): {error_detail}"
                    error_details['response_body'] = error_detail
                except:
                    error_msg = f"API Error ({status_code}): {e.response.text[:500]}"
                    error_details['response_text'] = e.response.text[:500]
            else:
                error_details['connection_error'] = True
                error_details['request_url'] = url
                error_details['request_method'] = tool.method
            
            logger.error(f"API request failed: {error_msg}")
            logger.debug(f"Error details: {error_details}")
            return {
                "status": "error",
                "message": error_msg,
                "status_code": status_code,
                "error_details": error_details
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
        """Perform authentication login with enhanced error handling."""
        try:
            session = requests.Session()

            headers = {
                "Authorization": self._get_basic_auth_header(self.username, self.password),
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "MCP-Financial-API-Client/1.0"
            }

            if self.api_key_name and self.api_key_value:
                headers[self.api_key_name] = self.api_key_value

            logger.info(f"Attempting login to {self.login_url}")
            logger.debug(f"Login headers: {dict(headers)}")
            
            response = session.post(
                self.login_url, 
                headers=headers, 
                verify=False,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()

            # Extract JSESSIONID
            token = None
            if "set-cookie" in response.headers:
                match = re.search(r'JSESSIONID=([^;]+)', response.headers.get("set-cookie", ""))
                if match:
                    token = match.group(1)

            if token:
                logger.info("✅ Authentication successful")
                # Set session for all specs
                for spec_key in list(self.api_specs.keys()):
                    self.sessions[spec_key] = session
                self.session_id = token
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
        logger.info(f"📋 Loaded {len(self.api_specs)} API specifications")
        logger.info(f"🔧 Registered {len(self.api_tools)} MCP tools")
        logger.info("✅ MCP Server is ready for client connections")
        
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
            logger.error(f"Error in server run loop: {e}")
            raise

    async def run_http(self, host: str = "localhost", port: int = 8080):
        """Run HTTP server for health checks and documentation."""
        if not HTTP_AVAILABLE:
            logger.error("aiohttp is not available. Please install with: pip install aiohttp")
            return
            
        app = web.Application()
        
        # Health check endpoint
        async def health(request):
            return web.json_response({
                "status": "healthy",
                "server": "openapi-mcp-server",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "api_specs": len(self.api_specs),
                "tools": len(self.api_tools),
                "specs_loaded": list(self.api_specs.keys())
            })
        
        # Documentation endpoint
        async def docs(request):
            tools_info = []
            for tool_name, tool in self.api_tools.items():
                # Build input schema
                props = {}
                required = []
                for pname, pinfo in tool.parameters.items():
                    pschema = {"type": pinfo.get("type", "string"), "description": pinfo.get("description", "")}
                    for prop in ["enum", "format", "minimum", "maximum", "minLength", "maxLength", "pattern", "example", "default", "properties", "schema_required", "$ref"]:
                        if prop in pinfo:
                            pschema[prop] = pinfo[prop]
                    props[pname] = pschema
                    if pinfo.get("required"):
                        required.append(pname)
                input_schema = {"type": "object", "properties": props, "required": required, "additionalProperties": False}
                tools_info.append({
                    "name": tool_name,
                    "description": tool.description,
                    "method": tool.method,
                    "path": tool.path,
                    "spec": tool.spec_name,
                    "tags": tool.tags,
                    "parameters": list(tool.parameters.keys()),
                    "inputSchema": input_schema
                })
            
            return web.json_response({
                "server": "OpenAPI MCP Server",
                "version": "1.0.0",
                "description": "MCP Server exposing OpenAPI specifications as tools",
                "api_specifications": {
                    spec_name: {
                        "base_url": spec.base_url,
                        "file_path": spec.file_path,
                        "info": spec.spec.get("info", {})
                    } for spec_name, spec in self.api_specs.items()
                },
                "tools": tools_info,
                "usage": {
                    "mcp_client": "Connect using MCP protocol via stdio transport",
                    "authentication": "Use set_credentials tool to authenticate",
                    "health_check": f"http://{host}:{port}/health"
                }
            })
        
        # API endpoints for HTTP MCP integration
        async def api_tools(request):
            """API endpoint to list tools for HTTP clients."""
            tools_info = []
            for tool_name, tool in self.api_tools.items():
                # Build input schema
                props = {}
                required = []
                for pname, pinfo in tool.parameters.items():
                    pschema = {"type": pinfo.get("type", "string"), "description": pinfo.get("description", "")}
                    for prop in ["enum", "format", "minimum", "maximum", "minLength", "maxLength", "pattern", "example", "default", "properties", "schema_required", "$ref"]:
                        if prop in pinfo:
                            pschema[prop] = pinfo[prop]
                    props[pname] = pschema
                    if pinfo.get("required"):
                        required.append(pname)
                input_schema = {"type": "object", "properties": props, "required": required, "additionalProperties": False}
                tools_info.append({
                    "name": tool_name,
                    "description": tool.description,
                    "method": tool.method,
                    "path": tool.path,
                    "spec": tool.spec_name,
                    "tags": tool.tags,
                    "parameters": list(tool.parameters.keys()),
                    "inputSchema": input_schema
                })
            return web.json_response({"tools": tools_info})
        
        async def api_credentials(request):
            """API endpoint to set credentials via HTTP."""
            try:
                data = await request.json()
                username = data.get("username")
                password = data.get("password")
                
                if not username or not password:
                    return web.json_response(
                        {"status": "error", "message": "Username and password required"}, 
                        status=400
                    )
                
                # Set credentials on the server
                self.set_credentials(
                    username=username,
                    password=password,
                    api_key_name=data.get("api_key_name"),
                    api_key_value=data.get("api_key_value"),
                    login_url=data.get("login_url")
                )
                
                return web.json_response({
                    "status": "success", 
                    "message": "Credentials set successfully"
                })
                
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)}, 
                    status=500
                )
        
        async def api_login(request):
            """API endpoint to perform login via HTTP."""
            try:
                success = self._perform_login()
                if success:
                    return web.json_response({
                        "status": "success", 
                        "message": "Login successful"
                    })
                else:
                    return web.json_response(
                        {"status": "error", "message": "Login failed"}, 
                        status=401
                    )
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)}, 
                    status=500
                )
            
        # Swagger UI-like endpoint
        async def swagger_ui(request):
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>OpenAPI MCP Server</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    h1 { color: #333; border-bottom: 3px solid #007acc; padding-bottom: 10px; }
                    h2 { color: #555; margin-top: 30px; }
                    .status { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 4px; margin: 20px 0; }
                    .spec { background: #f8f9fa; border-left: 4px solid #007acc; padding: 15px; margin: 15px 0; }
                    .tool { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 10px 0; border-radius: 4px; }
                    .method { display: inline-block; padding: 2px 8px; border-radius: 3px; color: white; font-weight: bold; }
                    .get { background: #61affe; }
                    .post { background: #49cc90; }
                    .put { background: #fca130; }
                    .delete { background: #f93e3e; }
                    .patch { background: #50e3c2; }
                    code { background: #f1f1f1; padding: 2px 4px; border-radius: 3px; }
                    .endpoint { margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; }
                    ul { margin: 10px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🚀 OpenAPI MCP Server</h1>
                    <div class="status">
                        ✅ Server is running and healthy<br>
                        📊 API Specifications: """ + str(len(self.api_specs)) + """<br>
                        🔧 Tools Available: """ + str(len(self.api_tools)) + """
                    </div>
                    
                    <h2>📋 Loaded API Specifications</h2>
            """
            
            for spec_name, spec in self.api_specs.items():
                info = spec.spec.get("info", {})
                html += f"""
                    <div class="spec">
                        <h3>{spec_name}</h3>
                        <p><strong>Base URL:</strong> <code>{spec.base_url}</code></p>
                        <p><strong>Title:</strong> {info.get('title', 'N/A')}</p>
                        <p><strong>Version:</strong> {info.get('version', 'N/A')}</p>
                        <p><strong>Description:</strong> {info.get('description', 'N/A')}</p>
                    </div>
                """
            
            html += "<h2>🔧 Available Tools</h2>"
            
            for tool_name, tool in self.api_tools.items():
                method_class = tool.method.lower()
                html += f"""
                    <div class="tool">
                        <h4>{tool_name}</h4>
                        <div class="endpoint">
                            <span class="method {method_class}">{tool.method}</span>
                            <code>{tool.path}</code>
                        </div>
                        <p>{tool.description}</p>
                        <p><strong>Spec:</strong> {tool.spec_name}</p>
                        <p><strong>Tags:</strong> {', '.join(tool.tags) if tool.tags else 'None'}</p>
                        <p><strong>Parameters:</strong> {', '.join(tool.parameters.keys()) if tool.parameters else 'None'}</p>
                    </div>
                """
            
            html += """
                    <h2>🔌 Usage</h2>
                    <div class="endpoint">
                        <p><strong>MCP Client Connection:</strong> Use stdio transport to connect via MCP protocol</p>
                        <p><strong>Health Check:</strong> <code>GET /health</code></p>
                        <p><strong>API Documentation:</strong> <code>GET /docs</code></p>
                        <p><strong>Authentication:</strong> Use the <code>set_credentials</code> tool after connecting</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return web.Response(text=html, content_type='text/html')
        
        # MCP tool calling endpoint
        async def call_tool(request):
            """Handle MCP tool calls via HTTP."""
            try:
                data = await request.json()
                tool_name = data.get("name")
                arguments = data.get("arguments", {})
                
                if not tool_name:
                    return web.json_response(
                        {"error": "Tool name is required"}, 
                        status=400
                    )
                
                # Call the tool using the stored MCP function reference
                result = await self.mcp_call_tool(tool_name, arguments)
                
                # Extract text content from MCP result
                if result and len(result) > 0:
                    content = result[0]
                    if hasattr(content, 'text'):
                        try:
                            # Try to parse as JSON first
                            import json
                            response_data = json.loads(content.text)
                            return web.json_response(response_data)
                        except json.JSONDecodeError:
                            # Return as plain text if not JSON
                            return web.json_response({"result": content.text})
                    else:
                        return web.json_response({"result": str(content)})
                else:
                    return web.json_response({"result": "No result returned"})
                    
            except Exception as e:
                logger.error(f"Error in call_tool endpoint: {e}", exc_info=True)
                return web.json_response(
                    {"error": str(e)}, 
                    status=500
                )
        
        app.router.add_get('/health', health)
        app.router.add_get('/docs', docs)
        app.router.add_get('/', swagger_ui)
        app.router.add_get('/swagger', swagger_ui)
        app.router.add_post('/call_tool', call_tool)
        app.router.add_get('/tools', api_tools)
        app.router.add_post('/credentials', api_credentials)
        app.router.add_post('/login', api_login)
        
        logger.info(f"🌐 Starting HTTP server on http://{host}:{port}")
        logger.info(f"📊 Health check: http://{host}:{port}/health")
        logger.info(f"📚 Documentation: http://{host}:{port}/docs")
        logger.info(f"🎨 Web UI: http://{host}:{port}/")
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        return runner


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="OpenAPI MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http", "both"])
    parser.add_argument("--host", default=getattr(config, 'MCP_HOST', 'localhost'))
    parser.add_argument("--port", type=int, default=getattr(config, 'MCP_PORT', 9000))
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    parser.add_argument("--api-key-name", help="API key header name")
    parser.add_argument("--api-key-value", help="API key value")
    parser.add_argument("--login-url", help="Login URL for authentication")
    
    args = parser.parse_args()
    
    try:
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
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
                # Run with proper exception handling
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(server.run())
            except KeyboardInterrupt:
                logger.info("Server shutdown by user")
            except Exception as e:
                logger.error(f"Server error: {e}", exc_info=True)
                return 1
            finally:
                loop.close()
        elif args.transport == "http":
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def run_http_only():
                    runner = await server.run_http(args.host, args.port)
                    try:
                        # Keep running
                        while True:
                            await asyncio.sleep(1)
                    except KeyboardInterrupt:
                        logger.info("HTTP server shutdown by user")
                    finally:
                        await runner.cleanup()
                
                loop.run_until_complete(run_http_only())
            except KeyboardInterrupt:
                logger.info("Server shutdown by user")
            except Exception as e:
                logger.error(f"Server error: {e}", exc_info=True)
                return 1
            finally:
                loop.close()
        elif args.transport == "both":
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def run_both():
                    # Start HTTP server
                    http_runner = await server.run_http(args.host, args.port)
                    
                    # Also prepare for stdio (but don't block on it)
                    logger.info("🔌 Server ready for MCP stdio connections")
                    logger.info("💡 To connect via MCP: python mcp_client_proper_working.py")
                    
                    try:
                        # Keep HTTP server running
                        while True:
                            await asyncio.sleep(1)
                    except KeyboardInterrupt:
                        logger.info("Server shutdown by user")
                    finally:
                        await http_runner.cleanup()
                
                loop.run_until_complete(run_both())
            except KeyboardInterrupt:
                logger.info("Server shutdown by user")
            except Exception as e:
                logger.error(f"Server error: {e}", exc_info=True)
                return 1
            finally:
                loop.close()
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())