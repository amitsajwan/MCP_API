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

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fastmcp2_server")

@dataclass
class APISpec:
    """API specification container."""
    name: str
    spec: Dict[str, Any]
    base_url: str
    file_path: Optional[str] = None

# Create FastMCP app
app = FastMCP("openapi-mcp-server")

class FastMCP2Server:
    """FastMCP 2.0 Server implementation."""
    
    def __init__(self):
        logger.info("🚀 Initializing FastMCP 2.0 Server...")
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
        """Register tools for a specific API specification."""
        paths = api_spec.spec.get('paths', {})
        tool_count = 0
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    self._register_api_tool(spec_name, method, path, operation, api_spec.base_url)
                    tool_count += 1
        
        logger.info(f"📋 Registered {tool_count} tools from {spec_name} API spec")
    
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

        # Create the tool function
        def create_tool_function(tool_name, spec_name, method, path, base_url):
            async def api_tool_function(**kwargs) -> str:
                try:
                    logger.info(f"Executing FastMCP 2.0 tool: {tool_name} with arguments: {list(kwargs.keys())}")
                    
                    # Execute the tool
                    result = self._execute_tool(tool_name, spec_name, method, path, base_url, kwargs)
                    
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
        
        # Register with FastMCP 2.0
        app.tool(name=tool_name, description=tool_description)(tool_func)
        logger.debug(f"🔧 Registered FastMCP 2.0 tool: {tool_name}")
    
    def _execute_tool(self, tool_name: str, spec_name: str, method: str, path: str, base_url: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an API tool."""
        try:
            # Ensure authentication
            if not self._ensure_authenticated():
                return {"status": "error", "message": "Authentication failed"}
            
            # Build request URL
            url = f"{base_url.rstrip('/')}{path}"
            
            # Replace path parameters
            for param_name, value in arguments.items():
                placeholder = f"{{{param_name}}}"
                if placeholder in url:
                    url = url.replace(placeholder, str(value))
            
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
            
            # Get session
            session = self.sessions.get(spec_name)
            if not session:
                session = requests.Session()
                session.headers.update({'User-Agent': 'FastMCP2-Financial-API-Client/2.0'})
                if self.session_id:
                    session.cookies.set('JSESSIONID', self.session_id)
                self.sessions[spec_name] = session
            
            # Prepare request data
            request_data = None
            query_params = {}
            
            for param_name, value in arguments.items():
                if param_name == 'body':
                    request_data = value
                elif not param_name.startswith('header_'):
                    # Only add to query params if it's not a path parameter
                    placeholder = f"{{{param_name}}}"
                    if placeholder not in path:
                        query_params[param_name] = value
            
            # Make request
            logger.info(f"Making {method} request to {url}")
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
            
            response.raise_for_status()
            
            # Parse response
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
                    error_msg = f"API Error ({status_code}): {error_detail}"
                except:
                    error_msg = f"API Error ({status_code}): {e.response.text[:500]}"
            
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