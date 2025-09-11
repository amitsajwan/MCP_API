#!/usr/bin/env python3
"""
FastMCP 2.0 Server - Proper Implementation
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
from typing import Dict, Any, List, Optional
import requests
from dataclasses import dataclass

# FastMCP 2.0 imports
from fastmcp import FastMCP

# OpenAPI imports - using manual parsing with better schema handling

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
        
        def validate(self):
            pass
    
    config = DefaultConfig()

# Configure comprehensive logging for MCP server
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_server.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("fastmcp2_server")

@dataclass
class APISpec:
    """API specification container."""
    name: str
    spec: Dict[str, Any]
    base_url: str
    file_path: Optional[str] = None
    openapi_spec: Any = None  # The parsed OpenAPI spec object

# Create FastMCP app
app = FastMCP("openapi-mcp-server")

class FastMCP2Server:
    """FastMCP 2.0 Server implementation."""
    
    def __init__(self):
        logger.info("🚀 Initializing FastMCP 2.0 Server...")
        
        # Enable experimental OpenAPI parser for better $ref handling
        os.environ['FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER'] = 'true'
        
        self.api_specs = {}
        self.sessions = {}
        self.session_id = None
        
        # Authentication state
        self.username = os.getenv('API_USERNAME')
        self.password = os.getenv('API_PASSWORD')
        self.api_key_name = os.getenv('API_KEY_NAME')
        self.api_key_value = os.getenv('API_KEY_VALUE')
        self.login_url = os.getenv('LOGIN_URL')

        # Initialize
        logger.info("📂 Loading API specifications...")
        self._load_api_specs()
        logger.info("🔧 Registering FastMCP 2.0 tools...")
        self._register_fastmcp_tools()
        logger.info(f"✅ FastMCP 2.0 Server initialized with {len(self.api_specs)} API specs")

        # Log credential status
        if self.username:
            logger.info(f"🔐 Credentials loaded from environment for user: {self.username}")
        else:
            logger.info("🔓 No credentials found in environment - use set_credentials tool")
    
    def _load_api_specs(self):
        """Load OpenAPI specifications from directory with enhanced schema handling."""
        openapi_dir = Path(config.OPENAPI_DIR)
        if not openapi_dir.exists():
            logger.warning(f"OpenAPI directory not found: {openapi_dir}")
            return
        
        for spec_file in openapi_dir.glob("*.yaml"):
            try:
                # Load spec with enhanced schema resolution
                with open(spec_file, 'r') as f:
                    spec_data = yaml.safe_load(f)
                
                spec_name = spec_file.stem
                base_url = self._get_base_url(spec_data, spec_name)
                
                api_spec = APISpec(
                    name=spec_name,
                    spec=spec_data,
                    base_url=base_url,
                    file_path=str(spec_file),
                    openapi_spec=None  # We'll use enhanced manual parsing
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
    
    def _register_fastmcp_tools(self):
        """Register API endpoints as FastMCP 2.0 tools."""
        
        # Add set_credentials tool
        @app.tool()
        async def set_credentials(
            username: str = None,
            password: str = None,
            api_key_name: str = None,
            api_key_value: str = None,
            login_url: str = None
        ) -> str:
            """Set authentication credentials for API access."""
            try:
                # Use provided values or fallback to environment variables or existing values
                username = username or self.username or os.getenv('API_USERNAME')
                password = password or self.password or os.getenv('API_PASSWORD')
                api_key_name = api_key_name or self.api_key_name or os.getenv('API_KEY_NAME')
                api_key_value = api_key_value or self.api_key_value or os.getenv('API_KEY_VALUE')
                login_url = login_url or self.login_url or os.getenv('LOGIN_URL') or config.DEFAULT_LOGIN_URL
                
                # Validate required credentials
                if not username or not password:
                    error_msg = "Username and password are required. Provide them as arguments or set API_USERNAME and API_PASSWORD environment variables."
                    logger.error(f"❌ {error_msg}")
                    return json.dumps({"status": "error", "message": error_msg}, indent=2)
                
                # Store credentials locally
                self.username = username
                self.password = password
                self.api_key_name = api_key_name
                self.api_key_value = api_key_value
                self.login_url = login_url
                
                response = {
                    "status": "success",
                    "message": "Credentials stored successfully in FastMCP 2.0 server",
                    "username": username,
                    "login_url": login_url,
                    "has_api_key": bool(api_key_name and api_key_value),
                    "api_key_name": api_key_name if api_key_name else None
                }
                
                logger.info(f"✅ Credentials stored successfully for user: {username}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"❌ Error setting credentials: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)
        
        # Add perform_login tool
        @app.tool()
        async def perform_login(force_login: bool = False) -> str:
            """Perform login using stored credentials to obtain session token."""
            try:
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
                    return json.dumps(response, indent=2)
                
                # Check if credentials are available
                if not self.username or not self.password:
                    error_msg = "No credentials available. Please call set_credentials first or set environment variables."
                    logger.error(f"❌ {error_msg}")
                    return json.dumps({"status": "error", "message": error_msg}, indent=2)
                
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
                    return json.dumps(response, indent=2)
                else:
                    error_msg = "Login failed - check credentials and login URL"
                    logger.error(f"❌ {error_msg}")
                    return json.dumps({"status": "error", "message": error_msg}, indent=2)
                    
            except Exception as e:
                logger.error(f"❌ Error during login: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)
    
    def _register_spec_tools(self, spec_name: str, api_spec: APISpec):
        """Register tools for a specific API specification with enhanced schema handling."""
        paths = api_spec.spec.get('paths', {})
        tool_count = 0
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    self._register_api_tool_enhanced(spec_name, method, path, operation, api_spec)
                    tool_count += 1
        
        logger.info(f"📋 Registered {tool_count} tools from {spec_name} API spec")
    
    def _register_api_tool_enhanced(self, spec_name: str, method: str, path: str, operation: Dict[str, Any], api_spec: APISpec):
        """Register a single API tool with enhanced schema handling including enums and $ref resolution."""
        operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').strip('_')}")
        tool_name = f"{spec_name}_{operation_id}"

        # Clean up tool name
        tool_name = re.sub(r'[^a-zA-Z0-9_]', '_', tool_name)

        # Build description from OpenAPI operation
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

        # Extract full OpenAPI schema for parameters with enhanced handling
        input_schema = self._build_input_schema_enhanced(operation, path, method, api_spec.spec)
        
        # Add schema information to description
        if input_schema.get('properties'):
            tool_description += f"\n\nParameters:"
            for param_name, param_schema in input_schema['properties'].items():
                param_type = param_schema.get('type', 'string')
                param_desc = param_schema.get('description', '')
                param_enum = param_schema.get('enum', [])
                required = param_name in input_schema.get('required', [])
                
                tool_description += f"\n- {param_name} ({param_type}){'*' if required else ''}: {param_desc}"
                if param_enum:
                    tool_description += f" [Options: {', '.join(map(str, param_enum))}]"

        # Create the tool function with Dict parameter
        def create_tool_function(tool_name, spec_name, method, path, base_url):
            async def api_tool_function(arguments: Dict[str, Any]) -> str:
                try:
                    logger.info(f"Executing FastMCP 2.0 tool: {tool_name} with arguments: {list(arguments.keys())}")
                    
                    # Execute the tool
                    result = self._execute_tool(tool_name, spec_name, method, path, base_url, arguments)
                    
                    if result.get("status") == "success":
                        response_text = json.dumps(result.get("data", result), indent=2)
                        logger.info(f"Tool {tool_name} executed successfully")
                        return response_text
                    else:
                        error_msg = f"Tool execution failed: {result.get('message', 'Unknown error')}"
                        if result.get('status_code'):
                            error_msg += f" (HTTP {result['status_code']})"
                        logger.error(f"Tool {tool_name} failed: {error_msg}")
                        return error_msg
                        
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                    return f"Error: {str(e)}"
            
            return api_tool_function
        
        # Create the tool function
        tool_func = create_tool_function(tool_name, spec_name, method, path, api_spec.base_url)
        
        # Register with FastMCP 2.0 using the full schema
        app.tool(
            name=tool_name, 
            description=tool_description,
            annotations={"input_schema": input_schema}
        )(tool_func)
        logger.debug(f"🔧 Registered FastMCP 2.0 tool: {tool_name} with enhanced schema")
    
    def _build_input_schema_enhanced(self, operation: Dict[str, Any], path: str, method: str, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build input schema from OpenAPI operation with enhanced $ref resolution and enum handling."""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Process path parameters
        path_params = re.findall(r'\{([^}]+)\}', path)
        for param_name in path_params:
            schema["properties"][param_name] = {
                "type": "string",
                "description": f"Path parameter: {param_name}"
            }
            schema["required"].append(param_name)
        
        # Process parameters (query, header, etc.)
        parameters = operation.get('parameters', [])
        for param in parameters:
            param_name = param.get('name')
            param_location = param.get('in', 'query')
            param_schema = param.get('schema', {})
            param_required = param.get('required', False)
            param_description = param.get('description', '')
            
            # Resolve $ref references in parameter schema
            resolved_schema = self._resolve_schema_ref_enhanced(param_schema, spec_data)
            
            schema["properties"][param_name] = {
                "type": resolved_schema.get('type', 'string'),
                "description": param_description,
                "enum": resolved_schema.get('enum'),
                "minimum": resolved_schema.get('minimum'),
                "maximum": resolved_schema.get('maximum'),
                "format": resolved_schema.get('format'),
                "pattern": resolved_schema.get('pattern'),
                "items": resolved_schema.get('items'),
                "default": resolved_schema.get('default'),
                "example": resolved_schema.get('example')
            }
            
            # Remove None values
            schema["properties"][param_name] = {k: v for k, v in schema["properties"][param_name].items() if v is not None}
            
            if param_required:
                schema["required"].append(param_name)
        
        # Process request body
        request_body = operation.get('requestBody', {})
        if request_body:
            content = request_body.get('content', {})
            if 'application/json' in content:
                json_schema = content['application/json'].get('schema', {})
                if json_schema:
                    resolved_schema = self._resolve_schema_ref_enhanced(json_schema, spec_data)
                    schema["properties"]["body"] = resolved_schema
                    if request_body.get('required', False):
                        schema["required"].append("body")
        
        # Clean up empty required list
        if not schema["required"]:
            del schema["required"]
        
        return schema
    
    def _resolve_schema_ref_enhanced(self, schema: Dict[str, Any], spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced $ref resolution with better handling of nested references and enums."""
        if '$ref' not in schema:
            return schema
        
        ref_path = schema['$ref']
        if ref_path.startswith('#/components/schemas/'):
            schema_name = ref_path.split('/')[-1]
            
            # Get components from spec
            components = spec_data.get('components', {})
            schemas = components.get('schemas', {})
            
            if schema_name in schemas:
                referenced_schema = schemas[schema_name]
                # Recursively resolve any nested $ref references
                return self._resolve_schema_ref_enhanced(referenced_schema, spec_data)
        
        logger.warning(f"Could not resolve $ref: {ref_path}")
        return {
            "type": "object",
            "description": f"Referenced schema: {ref_path}"
        }
    
    
    def _register_api_tool(self, spec_name: str, method: str, path: str, operation: Dict[str, Any], base_url: str):
        """Register a single API tool with FastMCP 2.0."""
        operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').strip('_')}")
        tool_name = f"{spec_name}_{operation_id}"

        # Clean up tool name
        tool_name = re.sub(r'[^a-zA-Z0-9_]', '_', tool_name)

        # Build description
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

        # Extract full OpenAPI schema for parameters
        input_schema = self._build_input_schema(operation, path, method)
        
        # Add schema information to description
        if input_schema.get('properties'):
            tool_description += f"\n\nParameters:"
            for param_name, param_schema in input_schema['properties'].items():
                param_type = param_schema.get('type', 'string')
                param_desc = param_schema.get('description', '')
                param_enum = param_schema.get('enum', [])
                required = param_name in input_schema.get('required', [])
                
                tool_description += f"\n- {param_name} ({param_type}){'*' if required else ''}: {param_desc}"
                if param_enum:
                    tool_description += f" [Options: {', '.join(map(str, param_enum))}]"

        # Create the tool function with Dict parameter
        def create_tool_function(tool_name, spec_name, method, path, base_url):
            async def api_tool_function(arguments: Dict[str, Any]) -> str:
                try:
                    logger.info(f"Executing FastMCP 2.0 tool: {tool_name} with arguments: {list(arguments.keys())}")
                    
                    # Execute the tool
                    result = self._execute_tool(tool_name, spec_name, method, path, base_url, arguments)
                    
                    if result.get("status") == "success":
                        response_text = json.dumps(result.get("data", result), indent=2)
                        logger.info(f"Tool {tool_name} executed successfully")
                        return response_text
                    else:
                        error_msg = f"Tool execution failed: {result.get('message', 'Unknown error')}"
                        if result.get('status_code'):
                            error_msg += f" (HTTP {result['status_code']})"
                        logger.error(f"Tool {tool_name} failed: {error_msg}")
                        return error_msg
                        
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                    return f"Error: {str(e)}"
            
            return api_tool_function
        
        # Create the tool function
        tool_func = create_tool_function(tool_name, spec_name, method, path, base_url)
        
        # Register with FastMCP 2.0 using the full schema
        app.tool(
            name=tool_name, 
            description=tool_description,
            annotations={"input_schema": input_schema}
        )(tool_func)
        logger.debug(f"🔧 Registered FastMCP 2.0 tool: {tool_name} with full schema")
    
    def _build_input_schema(self, operation: Dict[str, Any], path: str, method: str) -> Dict[str, Any]:
        """Build input schema from OpenAPI operation with full $ref resolution."""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Process path parameters
        path_params = re.findall(r'\{([^}]+)\}', path)
        for param_name in path_params:
            schema["properties"][param_name] = {
                "type": "string",
                "description": f"Path parameter: {param_name}"
            }
            schema["required"].append(param_name)
        
        # Process query parameters
        parameters = operation.get('parameters', [])
        for param in parameters:
            if param.get('in') == 'query':
                param_name = param['name']
                param_schema = self._resolve_schema_ref(param.get('schema', {}))
                
                schema["properties"][param_name] = {
                    "type": param_schema.get('type', 'string'),
                    "description": param.get('description', ''),
                    "enum": param_schema.get('enum'),
                    "minimum": param_schema.get('minimum'),
                    "maximum": param_schema.get('maximum'),
                    "format": param_schema.get('format'),
                    "pattern": param_schema.get('pattern'),
                    "items": param_schema.get('items'),
                    "default": param_schema.get('default'),
                    "example": param_schema.get('example')
                }
                
                # Remove None values
                schema["properties"][param_name] = {k: v for k, v in schema["properties"][param_name].items() if v is not None}
                
                if param.get('required', False):
                    schema["required"].append(param_name)
        
        # Process request body
        request_body = operation.get('requestBody', {})
        if request_body:
            content = request_body.get('content', {})
            if 'application/json' in content:
                json_schema = content['application/json'].get('schema', {})
                if json_schema:
                    # Resolve $ref references in request body
                    resolved_schema = self._resolve_schema_ref(json_schema)
                    schema["properties"]["body"] = resolved_schema
                    
                    if request_body.get('required', False):
                        schema["required"].append("body")
        
        # Clean up empty required list
        if not schema["required"]:
            del schema["required"]
        
        return schema
    
    def _resolve_schema_ref(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve $ref references in OpenAPI schema."""
        if '$ref' not in schema:
            return schema
        
        ref_path = schema['$ref']
        if ref_path.startswith('#/components/schemas/'):
            # Extract schema name from reference
            schema_name = ref_path.split('/')[-1]
            
            # Find the referenced schema in all loaded specs
            for spec_name, api_spec in self.api_specs.items():
                spec_data = api_spec.spec
                components = spec_data.get('components', {})
                schemas = components.get('schemas', {})
                
                if schema_name in schemas:
                    referenced_schema = schemas[schema_name]
                    # Recursively resolve any nested $ref references
                    return self._resolve_schema_ref(referenced_schema)
        
        # If reference cannot be resolved, return a generic object
        logger.warning(f"Could not resolve $ref: {ref_path}")
        return {
            "type": "object",
            "description": f"Referenced schema: {ref_path}"
        }
    
    def _execute_tool(self, tool_name: str, spec_name: str, method: str, path: str, base_url: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an API tool."""
        logger.info(f"🔧 [MCP_SERVER] Executing tool: {tool_name}")
        logger.info(f"🔧 [MCP_SERVER] Spec: {spec_name}, Method: {method}, Path: {path}")
        logger.info(f"🔧 [MCP_SERVER] Arguments: {list(arguments.keys())}")
        
        try:
            # Ensure authentication
            logger.info(f"🔐 [MCP_SERVER] Checking authentication for {tool_name}")
            if not self._ensure_authenticated():
                logger.error(f"❌ [MCP_SERVER] Authentication failed for {tool_name}")
                return {"status": "error", "message": "Authentication failed"}
            logger.info(f"✅ [MCP_SERVER] Authentication successful for {tool_name}")
            
            # Build request URL
            url = f"{base_url.rstrip('/')}{path}"
            logger.info(f"🔗 [MCP_SERVER] Base URL: {base_url}, Final URL: {url}")
            
            # Replace path parameters
            for param_name, value in arguments.items():
                placeholder = f"{{{param_name}}}"
                if placeholder in url:
                    url = url.replace(placeholder, str(value))
                    logger.info(f"🔗 [MCP_SERVER] Replaced {placeholder} with {value}")
            
            # Prepare request headers
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'FastMCP2-Financial-API-Client/2.0',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
            
            # Add API key if configured
            if self.api_key_name and self.api_key_value:
                headers[self.api_key_name] = self.api_key_value
                logger.info(f"🔑 [MCP_SERVER] Added API key: {self.api_key_name}")
            
            # Get session
            session = self.sessions.get(spec_name)
            if not session:
                logger.info(f"🔄 [MCP_SERVER] Creating new session for {spec_name}")
                session = requests.Session()
                session.headers.update({'User-Agent': 'FastMCP2-Financial-API-Client/2.0'})
                if self.session_id:
                    session.cookies.set('JSESSIONID', self.session_id)
                    logger.info(f"🍪 [MCP_SERVER] Set JSESSIONID: {self.session_id[:20]}...")
                self.sessions[spec_name] = session
            else:
                logger.info(f"✅ [MCP_SERVER] Using existing session for {spec_name}")
            
            # Prepare request data
            request_data = None
            query_params = {}
            
            for param_name, value in arguments.items():
                if param_name == 'body':
                    request_data = value
                    logger.info(f"📦 [MCP_SERVER] Request body: {len(str(value))} chars")
                elif not param_name.startswith('header_'):
                    # Only add to query params if it's not a path parameter
                    placeholder = f"{{{param_name}}}"
                    if placeholder not in path:
                        query_params[param_name] = value
                        logger.info(f"❓ [MCP_SERVER] Query param: {param_name} = {value}")
            
            # Make request
            logger.info(f"🌐 [MCP_SERVER] Making {method} request to {url}")
            logger.info(f"🌐 [MCP_SERVER] Query params: {query_params}")
            logger.info(f"🌐 [MCP_SERVER] Headers: {list(headers.keys())}")
            
            response = session.request(
                method=method,
                url=url,
                headers=headers,
                params=query_params if query_params else None,
                json=request_data if request_data else None,
                timeout=getattr(config, 'REQUEST_TIMEOUT', 30),
                verify=False,
                allow_redirects=True
            )
            
            logger.info(f"📡 [MCP_SERVER] Response status: {response.status_code}")
            logger.info(f"📡 [MCP_SERVER] Response headers: {list(response.headers.keys())}")
            
            response.raise_for_status()
            
            # Parse response
            try:
                result = response.json()
                logger.info(f"✅ [MCP_SERVER] JSON response parsed successfully")
            except json.JSONDecodeError:
                result = response.text
                logger.info(f"📝 [MCP_SERVER] Text response: {len(result)} chars")
            
            logger.info(f"✅ [MCP_SERVER] Tool {tool_name} executed successfully")
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
                    error_msg = f"API Error ({status_code}): {error_detail}"
                except:
                    error_msg = f"API Error ({status_code}): {e.response.text[:500]}"
            
            logger.error(f"❌ [MCP_SERVER] API request failed for {tool_name}: {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "status_code": status_code
            }
        except Exception as e:
            logger.error(f"❌ [MCP_SERVER] Unexpected error executing tool {tool_name}: {e}", exc_info=True)
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
                "User-Agent": "FastMCP2-Financial-API-Client/2.0"
            }

            if self.api_key_name and self.api_key_value:
                headers[self.api_key_name] = self.api_key_value

            logger.info(f"Attempting login to {self.login_url}")
            
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

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="FastMCP 2.0 Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9000)
    
    args = parser.parse_args()
    
    try:
        # Create server instance
        server = FastMCP2Server()
        
        if args.transport == "stdio":
            logger.info("🚀 Starting FastMCP 2.0 server with stdio transport")
            app.run(transport="stdio")
        elif args.transport == "http":
            logger.info(f"🌐 Starting FastMCP 2.0 server on http://{args.host}:{args.port}")
            app.run(transport="http", host=args.host, port=args.port)
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())