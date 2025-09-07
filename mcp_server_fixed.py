#!/usr/bin/env python3
"""
Fixed MCP Server - Handles Real OpenAPI Specifications
This version properly handles complex OpenAPI specs with $ref resolution,
complex schemas, and real authentication schemes.
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
from typing import Dict, Any, List, Optional, Callable, Union
import requests
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlparse

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
logger = logging.getLogger("mcp_server_fixed")


@dataclass
class APISpec:
    """API specification container with resolved references."""
    name: str
    spec: Dict[str, Any]
    base_url: str
    file_path: Optional[str] = None
    resolved_spec: Optional[Dict[str, Any]] = None


@dataclass
class APITool:
    """API tool representation with enhanced schema support."""
    name: str
    description: str
    method: str
    path: str
    parameters: Dict[str, Any]
    spec_name: str
    tags: List[str]
    summary: Optional[str] = None
    operation_id: Optional[str] = None
    security_schemes: List[Dict[str, Any]] = None


class OpenAPISpecResolver:
    """Resolves $ref references in OpenAPI specifications."""
    
    def __init__(self, spec_data: Dict[str, Any], spec_file_path: str = None):
        self.spec_data = spec_data
        self.spec_file_path = spec_file_path
        self.resolved_spec = None
        self._resolve_references()
    
    def _resolve_references(self):
        """Resolve all $ref references in the spec."""
        self.resolved_spec = self._deep_resolve_refs(self.spec_data)
    
    def _deep_resolve_refs(self, obj: Any, path: str = "#") -> Any:
        """Recursively resolve $ref references."""
        if isinstance(obj, dict):
            if '$ref' in obj:
                return self._resolve_ref(obj['$ref'], path)
            else:
                return {k: self._deep_resolve_refs(v, f"{path}/{k}") for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_resolve_refs(item, f"{path}[{i}]") for i, item in enumerate(obj)]
        else:
            return obj
    
    def _resolve_ref(self, ref: str, current_path: str) -> Any:
        """Resolve a single $ref reference."""
        if ref.startswith('#'):
            # Internal reference
            ref_path = ref[1:]  # Remove #
            return self._get_by_path(self.spec_data, ref_path)
        else:
            # External reference - for now, return the ref as-is
            # In a full implementation, you'd fetch and resolve external refs
            logger.warning(f"External reference not resolved: {ref}")
            return {"$ref": ref}
    
    def _get_by_path(self, obj: Any, path: str) -> Any:
        """Get value by JSON pointer path."""
        if not path:
            return obj
        
        parts = path.split('/')
        current = obj
        
        for part in parts:
            if part:
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    current = current[int(part)]
                else:
                    return None
        
        return current


class FixedMCPServer:
    """Fixed MCP Server that properly handles real OpenAPI specifications."""
    
    def __init__(self):
        logger.info("🚀 Initializing Fixed MCP Server...")
        self.server = Server("openapi-mcp-server-fixed")
        self.api_specs: Dict[str, APISpec] = {}
        self.api_tools: Dict[str, APITool] = {}
        self.sessions: Dict[str, requests.Session] = {}
        
        # Authentication state
        self.username: Optional[str] = os.getenv('API_USERNAME')
        self.password: Optional[str] = os.getenv('API_PASSWORD')
        self.api_key_name: Optional[str] = os.getenv('API_KEY_NAME')
        self.api_key_value: Optional[str] = os.getenv('API_KEY_VALUE')
        self.login_url: Optional[str] = os.getenv('LOGIN_URL')
        self.session_id: Optional[str] = None
        
        # Initialize
        logger.info("📂 Loading API specifications...")
        self._load_api_specs()
        logger.info("🔧 Registering MCP tools...")
        self._register_mcp_tools()
        logger.info(f"✅ Fixed MCP Server initialized with {len(self.api_tools)} tools from {len(self.api_specs)} API specs")
    
    def _load_api_specs(self):
        """Load OpenAPI specifications with proper $ref resolution."""
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
                
                # Resolve $ref references
                resolver = OpenAPISpecResolver(spec_data, str(spec_file))
                resolved_spec = resolver.resolved_spec
                
                api_spec = APISpec(
                    name=spec_name,
                    spec=spec_data,
                    base_url=base_url,
                    file_path=str(spec_file),
                    resolved_spec=resolved_spec
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
                # Convert parameters to MCP format with comprehensive schema support
                mcp_parameters = {}
                required_params = []
                
                for param_name, param_info in api_tool.parameters.items():
                    param_schema = self._build_mcp_parameter_schema(param_info)
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
            tools.extend(self._get_auth_tools())
            
            return tools
        
        @self.server.call_tool()
        async def mcp_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Call an MCP tool by name."""
            logger.info(f"🔧 Executing tool: {name} with arguments: {list(arguments.keys())}")
            
            # Handle authentication tools
            if name in ["set_credentials", "perform_login"]:
                return await self._handle_auth_tool(name, arguments)
            
            if name not in self.api_tools:
                logger.warning(f"Tool not found: {name}")
                return [TextContent(type="text", text=f"Tool not found: {name}")]
            
            try:
                logger.info(f"Executing tool: {name} with arguments: {arguments}")
                
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
    
    def _build_mcp_parameter_schema(self, param_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build MCP parameter schema from OpenAPI parameter info."""
        schema = {
            "type": param_info.get('type', 'string'),
            "description": param_info.get('description', ''),
        }
        
        # Handle all schema properties
        schema_properties = ['enum', 'format', 'minimum', 'maximum', 'minLength', 'maxLength', 'pattern', 'example', 'default']
        for prop in schema_properties:
            if prop in param_info:
                schema[prop] = param_info[prop]
        
        # Handle object properties for request body
        if param_info.get('type') == 'object':
            if 'properties' in param_info:
                schema['properties'] = param_info['properties']
            if 'schema_required' in param_info:
                schema['required'] = param_info['schema_required']
            if '$ref' in param_info:
                schema['$ref'] = param_info['$ref']
        
        # Handle array types
        if param_info.get('type') == 'array':
            if 'items' in param_info:
                schema['items'] = param_info['items']
        
        return schema
    
    def _get_auth_tools(self) -> List[Tool]:
        """Get authentication tools."""
        return [
            Tool(
                name="set_credentials",
                description="Set authentication credentials for API access",
                inputSchema={
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
            ),
            Tool(
                name="perform_login",
                description="Perform login using stored credentials",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "force_login": {"type": "boolean", "description": "Force login even if already authenticated", "default": False}
                    },
                    "required": [],
                    "additionalProperties": False
                }
            )
        ]
    
    async def _handle_auth_tool(self, name: str, arguments: dict) -> List[TextContent]:
        """Handle authentication tool calls."""
        if name == "set_credentials":
            try:
                # Store credentials
                self.username = arguments.get("username") or self.username or os.getenv('API_USERNAME')
                self.password = arguments.get("password") or self.password or os.getenv('API_PASSWORD')
                self.api_key_name = arguments.get("api_key_name") or self.api_key_name or os.getenv('API_KEY_NAME')
                self.api_key_value = arguments.get("api_key_value") or self.api_key_value or os.getenv('API_KEY_VALUE')
                self.login_url = arguments.get("login_url") or self.login_url or os.getenv('LOGIN_URL') or config.DEFAULT_LOGIN_URL
                
                if not self.username or not self.password:
                    error_msg = "Username and password are required"
                    logger.error(f"❌ {error_msg}")
                    return [TextContent(type="text", text=json.dumps({"status": "error", "message": error_msg}, indent=2))]
                
                response = {
                    "status": "success",
                    "message": "Credentials stored successfully",
                    "username": self.username,
                    "login_url": self.login_url,
                    "has_api_key": bool(self.api_key_name and self.api_key_value)
                }
                
                logger.info(f"✅ Credentials stored successfully for user: {self.username}")
                return [TextContent(type="text", text=json.dumps(response, indent=2))]
                
            except Exception as e:
                logger.error(f"❌ Error setting credentials: {e}")
                return [TextContent(type="text", text=json.dumps({"status": "error", "message": str(e)}, indent=2))]
        
        elif name == "perform_login":
            try:
                force_login = arguments.get("force_login", False)
                
                if not force_login and self.session_id:
                    response = {
                        "status": "success",
                        "message": "Already authenticated",
                        "session_id": self.session_id,
                        "username": self.username
                    }
                    logger.info("✅ Already authenticated")
                    return [TextContent(type="text", text=json.dumps(response, indent=2))]
                
                if not self.username or not self.password:
                    error_msg = "No credentials available. Please call set_credentials first"
                    logger.error(f"❌ {error_msg}")
                    return [TextContent(type="text", text=json.dumps({"status": "error", "message": error_msg}, indent=2))]
                
                result = self._perform_login()
                if result:
                    response = {
                        "status": "success",
                        "message": "Login successful",
                        "session_id": self.session_id,
                        "username": self.username
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
    
    def _register_spec_tools(self, spec_name: str, api_spec: APISpec):
        """Register tools for a specific API specification using resolved spec."""
        # Use resolved spec for better handling
        spec_to_use = api_spec.resolved_spec or api_spec.spec
        paths = spec_to_use.get('paths', {})
        tool_count = 0
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    self._register_mcp_tool(spec_name, method, path, operation, api_spec.base_url, spec_to_use)
                    tool_count += 1
        
        logger.info(f"📋 Registered {tool_count} tools from {spec_name} API spec")
    
    def _register_mcp_tool(self, spec_name: str, method: str, path: str, operation: Dict[str, Any], base_url: str, full_spec: Dict[str, Any]):
        """Register a single API endpoint as an MCP tool with enhanced schema support."""
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
        
        # Add response information with proper schema handling
        responses = operation.get('responses', {})
        if responses:
            tool_description += "\n\nResponses:"
            for status_code, response_info in responses.items():
                response_desc = response_info.get('description', '')
                tool_description += f"\n- {status_code}: {response_desc}"
                
                # Add response schema info with $ref resolution
                content = response_info.get('content', {})
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    if schema:
                        resolved_schema = self._resolve_schema_refs(schema, full_spec)
                        if 'properties' in resolved_schema:
                            tool_description += f" (Returns: {', '.join(resolved_schema['properties'].keys())})"
        
        # Build parameters with enhanced schema information
        parameters = self._extract_parameters_enhanced(operation, full_spec)
        
        # Extract security schemes
        security_schemes = self._extract_security_schemes(operation, full_spec)
        
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
            security_schemes=security_schemes
        )
        
        self.api_tools[tool_name] = api_tool
        logger.debug(f"🔧 Registered tool: {tool_name} ({method.upper()} {path}) with {len(parameters)} parameters")
    
    def _resolve_schema_refs(self, schema: Dict[str, Any], full_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve $ref references in a schema."""
        if '$ref' in schema:
            ref_path = schema['$ref']
            if ref_path.startswith('#'):
                # Internal reference
                ref_path = ref_path[1:]  # Remove #
                parts = ref_path.split('/')
                current = full_spec
                for part in parts:
                    if part and isinstance(current, dict):
                        current = current.get(part)
                return current or schema
        return schema
    
    def _extract_parameters_enhanced(self, operation: Dict[str, Any], full_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from OpenAPI operation with enhanced schema support."""
        parameters = {}
        
        # Path parameters
        for param in operation.get('parameters', []):
            param_name = param['name']
            param_schema = param.get('schema', {})
            
            # Resolve schema references
            resolved_schema = self._resolve_schema_refs(param_schema, full_spec)
            
            param_def = {
                'type': resolved_schema.get('type', 'string'),
                'description': param.get('description', ''),
                'required': param.get('required', param.get('in') == 'path')
            }
            
            # Add additional schema properties
            self._add_schema_properties_enhanced(param_def, resolved_schema)
            
            if param.get('in') == 'path':
                parameters[param_name] = param_def
            elif param.get('in') == 'query':
                parameters[param_name] = param_def
            elif param.get('in') == 'header':
                parameters[f"header_{param_name}"] = param_def
        
        # Request body with enhanced schema handling
        request_body = operation.get('requestBody')
        if request_body:
            content = request_body.get('content', {})
            if 'application/json' in content:
                json_content = content['application/json']
                schema = json_content.get('schema', {})
                
                # Resolve schema references
                resolved_schema = self._resolve_schema_refs(schema, full_spec)
                
                body_param = {
                    'type': resolved_schema.get('type', 'object'),
                    'description': request_body.get('description', 'Request body data'),
                    'required': request_body.get('required', False)
                }
                
                # Add detailed schema information
                if 'properties' in resolved_schema:
                    body_param['properties'] = resolved_schema['properties']
                if 'required' in resolved_schema:
                    body_param['schema_required'] = resolved_schema['required']
                if 'items' in resolved_schema:
                    body_param['items'] = resolved_schema['items']
                
                parameters['body'] = body_param
        
        return parameters
    
    def _add_schema_properties_enhanced(self, param_def: Dict[str, Any], schema: Dict[str, Any]):
        """Add additional schema properties to parameter definition with enhanced support."""
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
        
        # Add items for array types
        if 'items' in schema:
            param_def['items'] = schema['items']
        
        # Add properties for object types
        if 'properties' in schema:
            param_def['properties'] = schema['properties']
    
    def _extract_security_schemes(self, operation: Dict[str, Any], full_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract security schemes from operation."""
        security_schemes = []
        
        # Get security requirements from operation
        security_requirements = operation.get('security', [])
        
        # Get security schemes from components
        components = full_spec.get('components', {})
        security_schemes_def = components.get('securitySchemes', {})
        
        for security_req in security_requirements:
            for scheme_name, scopes in security_req.items():
                if scheme_name in security_schemes_def:
                    scheme_def = security_schemes_def[scheme_name]
                    security_schemes.append({
                        'name': scheme_name,
                        'type': scheme_def.get('type'),
                        'scheme': scheme_def.get('scheme'),
                        'scopes': scopes
                    })
        
        return security_schemes
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an API tool with enhanced error handling."""
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
                self.session_id = token
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
        logger.info("🚀 Starting Fixed MCP server with stdio transport")
        logger.info(f"📋 Loaded {len(self.api_specs)} API specifications")
        logger.info(f"🔧 Registered {len(self.api_tools)} MCP tools")
        logger.info("✅ Fixed MCP Server is ready for client connections")
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="openapi-mcp-server-fixed",
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fixed OpenAPI MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http", "both"])
    parser.add_argument("--host", default=getattr(config, 'MCP_HOST', 'localhost'))
    parser.add_argument("--port", type=int, default=getattr(config, 'MCP_PORT', 8080))
    
    args = parser.parse_args()
    
    try:
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            return 1
        
        # Create and configure server
        server = FixedMCPServer()
        
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
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())