 
#!/usr/bin/env python3
"""
FastMCP 2.0 Server - Proper Implementation with Tool Name Length Fix
"""

import os
import json
import yaml
import base64
import re
import logging
import asyncio
import argparse
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from dataclasses import dataclass

# FastMCP 2.0 imports
from fastmcp import FastMCP

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
    openapi_spec: Any = None

# Create FastMCP app
app = FastMCP("openapi-mcp-server")

class FastMCP2Server:
    """FastMCP 2.0 Server implementation with tool name length fixes."""
    
    def __init__(self):
        logger.info("🚀 Initializing FastMCP 2.0 Server...")
        
        # Enable experimental OpenAPI parser for better $ref handling
        os.environ['FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER'] = 'true'
        
        self.api_specs = {}
        self.sessions = {}
        self.session_id = None
        self.tool_name_mapping = {}  # Map shortened names to full info
        
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
    
    def _generate_short_tool_name(self, spec_name: str, operation_id: str, method: str, path: str) -> str:
        """Generate a short tool name that fits OpenAI's 64 character limit"""
        # Start with the basic combination
        base_name = f"{spec_name}_{operation_id}"
        
        # Clean up the name
        base_name = re.sub(r'[^a-zA-Z0-9_]', '_', base_name)
        
        # If it's already short enough, return it
        if len(base_name) <= 64:
            return base_name
        
        # If too long, try different strategies
        
        # Strategy 1: Shorten spec_name and operation_id
        max_spec_len = 20
        max_op_len = 40
        
        short_spec = spec_name[:max_spec_len] if len(spec_name) > max_spec_len else spec_name
        short_op = operation_id[:max_op_len] if len(operation_id) > max_op_len else operation_id
        
        candidate = f"{short_spec}_{short_op}"
        candidate = re.sub(r'[^a-zA-Z0-9_]', '_', candidate)
        
        if len(candidate) <= 64:
            return candidate
        
        # Strategy 2: Use method + path hash for uniqueness
        path_clean = re.sub(r'[^a-zA-Z0-9]', '', path)
        method_path = f"{method}_{path_clean}"
        
        if len(method_path) <= 30:
            candidate = f"{short_spec}_{method_path}"[:64]
        else:
            # Strategy 3: Use hash for very long names
            full_name = f"{spec_name}_{operation_id}_{method}_{path}"
            name_hash = hashlib.md5(full_name.encode()).hexdigest()[:8]
            candidate = f"{short_spec}_{method}_{name_hash}"
        
        # Ensure it's not too long and clean
        candidate = re.sub(r'[^a-zA-Z0-9_]', '_', candidate)[:64]
        
        # Remove trailing underscores
        candidate = candidate.rstrip('_')
        
        return candidate
    
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
                    openapi_spec=None
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
        """Register tools for a specific API specification with tool name length fixes."""
        paths = api_spec.spec.get('paths', {})
        tool_count = 0
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    self._register_api_tool_enhanced(spec_name, method, path, operation, api_spec)
                    tool_count += 1
        
        logger.info(f"📋 Registered {tool_count} tools from {spec_name} API spec")
    
    def _register_api_tool_enhanced(self, spec_name: str, method: str, path: str, operation: Dict[str, Any], api_spec: APISpec):
        """Register a single API tool with enhanced schema handling and proper tool name length management."""
        operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').strip('_')}")
        
        # FIXED: Generate short tool name that fits OpenAI limits
        tool_name = self._generate_short_tool_name(spec_name, operation_id, method, path)
        
        # Store mapping for execution
        self.tool_name_mapping[tool_name] = {
            'spec_name': spec_name,
            'method': method,
            'path': path,
            'operation': operation,
            'base_url': api_spec.base_url,
            'original_operation_id': operation_id
        }

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

        # Create the tool function with proper parameter handling for FastMCP 2.0
        def create_tool_function(tool_name):
            # Get the input schema to create proper function signature
            input_schema = self._build_input_schema_enhanced(operation, path, method, api_spec.spec)
            
            # Extract parameter names from schema for proper function signature
            param_names = list(input_schema.get('properties', {}).keys())
            required_params = input_schema.get('required', [])
            
            # Create a proper closure that captures the necessary variables
            # Build function signature with proper parameters
            param_signature = []
            for param_name in param_names:
                if param_name in required_params:
                    param_signature.append(f"{param_name}")
                else:
                    param_signature.append(f"{param_name}=None")
            
            # Create function code with proper signature
            func_code = f"""async def api_tool_function(self, {', '.join(param_signature)}) -> str:
    try:
        # Collect all non-None arguments
        arguments = {{}}
{chr(10).join([f'        if {param} is not None: arguments["{param}"] = {param}' for param in param_names])}
        
        logger.info(f"Executing FastMCP 2.0 tool: {tool_name} with arguments: {{list(arguments.keys())}}")
        
        # Get tool info from mapping
        tool_info = self.tool_name_mapping["{tool_name}"]
        
        # Execute the tool
        result = self._execute_tool(
            "{tool_name}", 
            tool_info['spec_name'], 
            tool_info['method'], 
            tool_info['path'], 
            tool_info['base_url'], 
            arguments
        )
        
        if result.get("status") == "success":
            response_text = json.dumps(result.get("data", result), indent=2)
            logger.info(f"Tool {tool_name} executed successfully")
            return response_text
        else:
            error_msg = f"Tool execution failed: {{result.get('message', 'Unknown error')}}"
            if result.get('status_code'):
                error_msg += f" (HTTP {{result['status_code']}})"
            logger.error(f"Tool {tool_name} failed: {{error_msg}}")
            return error_msg
            
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {{e}}", exc_info=True)
        return f"Error: {{str(e)}}"
"""
            
            # Create the function dynamically
            local_vars = {'logger': logger, 'json': json, 'tool_name': tool_name}
            exec(func_code, globals(), local_vars)
            return local_vars['api_tool_function']
        
        # Create the tool function
        tool_func = create_tool_function(tool_name)
        
        # Bind the function to the instance
        bound_tool_func = tool_func.__get__(self, self.__class__)
        
        # Register with FastMCP 2.0 using the correct schema format
        app.tool(
            name=tool_name, 
            description=tool_description,
            annotations={"input_schema": input_schema}
        )(bound_tool_func)
        
        # Log with length info
        logger.debug(f"🔧 Registered tool: {tool_name} (len={len(tool_name)}) -> {method} {path}")
    
    def _build_input_schema_enhanced(self, operation: Dict[str, Any], path: str, method: str, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build input schema from OpenAPI operation with enhanced $ref resolution and comprehensive constraint preservation."""
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
            
            # Build comprehensive parameter schema preserving all constraints
            param_schema_props = {
                "type": resolved_schema.get('type', 'string'),
                "description": param_description or resolved_schema.get('description', ''),
            }
            
            # Preserve all validation constraints
            constraint_fields = [
                'enum', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum',
                'minLength', 'maxLength', 'pattern', 'format', 'multipleOf',
                'minItems', 'maxItems', 'uniqueItems', 'minProperties', 'maxProperties',
                'items', 'properties', 'additionalProperties', 'required', 'allOf', 
                'oneOf', 'anyOf', 'not', 'const', 'default', 'example', 'examples'
            ]
            
            for field in constraint_fields:
                if field in resolved_schema and resolved_schema[field] is not None:
                    param_schema_props[field] = resolved_schema[field]
            
            # Handle array-specific constraints
            if resolved_schema.get('type') == 'array':
                items_schema = resolved_schema.get('items', {})
                if items_schema:
                    # Recursively resolve items schema
                    resolved_items = self._resolve_schema_ref_enhanced(items_schema, spec_data)
                    param_schema_props['items'] = resolved_items
            
            # Handle object-specific constraints
            if resolved_schema.get('type') == 'object':
                properties = resolved_schema.get('properties', {})
                if properties:
                    resolved_properties = {}
                    for prop_name, prop_schema in properties.items():
                        resolved_prop = self._resolve_schema_ref_enhanced(prop_schema, spec_data)
                        resolved_properties[prop_name] = resolved_prop
                    param_schema_props['properties'] = resolved_properties
                
                # Preserve object constraints
                if 'additionalProperties' in resolved_schema:
                    param_schema_props['additionalProperties'] = resolved_schema['additionalProperties']
            
            schema["properties"][param_name] = param_schema_props
            
            if param_required:
                schema["required"].append(param_name)
        
        # Process request body with enhanced schema preservation
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
        """Enhanced $ref resolution with comprehensive schema preservation and nested reference handling."""
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
                # Recursively resolve any nested $ref references while preserving all details
                resolved = self._resolve_schema_ref_enhanced(referenced_schema, spec_data)
                
                # Preserve the original schema name for context
                if 'title' not in resolved:
                    resolved['title'] = schema_name
                
                return resolved
            else:
                logger.warning(f"Schema not found: {schema_name}")
                return {
                    "type": "object",
                    "description": f"Referenced schema not found: {schema_name}",
                    "title": schema_name
                }
        elif ref_path.startswith('#/components/parameters/'):
            # Handle parameter references
            param_name = ref_path.split('/')[-1]
            components = spec_data.get('components', {})
            parameters = components.get('parameters', {})
            
            if param_name in parameters:
                param_def = parameters[param_name]
                param_schema = param_def.get('schema', {})
                return self._resolve_schema_ref_enhanced(param_schema, spec_data)
            else:
                logger.warning(f"Parameter not found: {param_name}")
                return {
                    "type": "string",
                    "description": f"Referenced parameter not found: {param_name}"
                }
        elif ref_path.startswith('#/components/responses/'):
            # Handle response references
            response_name = ref_path.split('/')[-1]
            components = spec_data.get('components', {})
            responses = components.get('responses', {})
            
            if response_name in responses:
                response_def = responses[response_name]
                content = response_def.get('content', {})
                if 'application/json' in content:
                    json_schema = content['application/json'].get('schema', {})
                    return self._resolve_schema_ref_enhanced(json_schema, spec_data)
            else:
                logger.warning(f"Response not found: {response_name}")
                return {
                    "type": "object",
                    "description": f"Referenced response not found: {response_name}"
                }
        else:
            logger.warning(f"Unsupported $ref path: {ref_path}")
            return {
                "type": "object",
                "description": f"Unsupported reference: {ref_path}"
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

            logger.info(f"🌐 [MCP_SERVER] Attempting login to {self.login_url}")
            logger.info(f"🔐 [MCP_SERVER] Login headers: {list(headers.keys())}")
            logger.info(f"👤 [MCP_SERVER] Username: {self.username}")
            logger.info(f"🔑 [MCP_SERVER] API Key: {self.api_key_name if self.api_key_name else 'None'}")
            
            response = session.post(
                self.login_url, 
                headers=headers, 
                verify=False,
                timeout=30,
                allow_redirects=True
            )
            
            logger.info(f"📡 [MCP_SERVER] Login response status: {response.status_code}")
            logger.info(f"📡 [MCP_SERVER] Login response headers: {list(response.headers.keys())}")
            
            response.raise_for_status()

            # Extract JSESSIONID
            token = None
            if "set-cookie" in response.headers:
                logger.info(f"🍪 [MCP_SERVER] Set-Cookie header: {response.headers.get('set-cookie', '')}")
                match = re.search(r'JSESSIONID=([^;]+)', response.headers.get("set-cookie", ""))
                if match:
                    token = match.group(1)
                    logger.info(f"🍪 [MCP_SERVER] Extracted JSESSIONID: {token[:20]}...")

            if token:
                logger.info("✅ [MCP_SERVER] Authentication successful")
                for spec_key in list(self.api_specs.keys()):
                    self.sessions[spec_key] = session
                self.session_id = token
                return True
            else:
                logger.error("❌ [MCP_SERVER] No JSESSIONID found in login response")
                logger.error(f"❌ [MCP_SERVER] Response text: {response.text[:500]}")
                return False

        except Exception as e:
            logger.error(f"❌ [MCP_SERVER] Authentication failed: {e}")
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
