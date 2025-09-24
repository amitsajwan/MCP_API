#!/usr/bin/env python3
"""
Simplified FastMCP Server using from_openapi
============================================
A clean, simple implementation using FastMCP's from_openapi capability
to automatically generate tools from OpenAPI specifications.
"""

import os
import json
import yaml
import asyncio
import logging
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('simplified_fastmcp.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("simplified_fastmcp")

class SimplifiedFastMCPServer:
    """Simplified FastMCP server using from_openapi approach"""
    
    def __init__(self, openapi_dir: str = "./openapi_specs"):
        self.openapi_dir = Path(openapi_dir)
        self.mcp_instances = {}
        self.http_clients = {}
        self.session_id = None
        
        # Authentication state
        self.username = os.getenv('API_USERNAME')
        self.password = os.getenv('API_PASSWORD')
        self.api_key_name = os.getenv('API_KEY_NAME')
        self.api_key_value = os.getenv('API_KEY_VALUE')
        self.login_url = os.getenv('LOGIN_URL', 'http://localhost:8080/auth/login')
        self.base_url = os.getenv('FORCE_BASE_URL', 'http://localhost:8080')
        
        logger.info("🚀 Initializing Simplified FastMCP Server...")
        logger.info(f"📂 OpenAPI directory: {self.openapi_dir}")
        logger.info(f"🔐 Username: {self.username or 'Not set'}")
        logger.info(f"🌐 Base URL: {self.base_url}")
    
    async def initialize(self) -> bool:
        """Initialize the server by loading OpenAPI specs and creating FastMCP instances"""
        try:
            if not self.openapi_dir.exists():
                logger.error(f"OpenAPI directory not found: {self.openapi_dir}")
                return False
            
            # Load all OpenAPI specifications
            spec_files = list(self.openapi_dir.glob("*.yaml"))
            if not spec_files:
                logger.warning(f"No YAML files found in {self.openapi_dir}")
                return False
            
            logger.info(f"📋 Found {len(spec_files)} OpenAPI specification files")
            
            for spec_file in spec_files:
                await self._load_openapi_spec(spec_file)
            
            logger.info(f"✅ Initialized {len(self.mcp_instances)} FastMCP instances")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            return False
    
    async def _load_openapi_spec(self, spec_file: Path):
        """Load a single OpenAPI specification and create FastMCP instance"""
        try:
            spec_name = spec_file.stem
            logger.info(f"📖 Loading OpenAPI spec: {spec_name}")
            
            # Load the OpenAPI specification
            with open(spec_file, 'r', encoding='utf-8') as f:
                spec_data = yaml.safe_load(f)
            
            # Create HTTP client with authentication
            client = await self._create_authenticated_client(spec_data, spec_name)
            
            # Create FastMCP instance using from_openapi
            logger.info(f"🔧 Creating FastMCP instance for {spec_name}...")
            mcp_instance = FastMCP.from_openapi(
                openapi_spec=spec_data,
                client=client,
                name=f"{spec_name}-api"
            )
            
            # Store the instance and client
            self.mcp_instances[spec_name] = mcp_instance
            self.http_clients[spec_name] = client
            
            logger.info(f"✅ Created FastMCP instance for {spec_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load spec {spec_file}: {e}")
    
    async def _create_authenticated_client(self, spec_data: Dict[str, Any], spec_name: str) -> httpx.AsyncClient:
        """Create an authenticated HTTP client for the API"""
        
        # Determine base URL
        base_url = self._get_base_url(spec_data, spec_name)
        
        # Prepare headers
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Simplified-FastMCP-Client/1.0'
        }
        
        # Add API key if configured
        if self.api_key_name and self.api_key_value:
            headers[self.api_key_name] = self.api_key_value
            logger.info(f"🔑 Added API key header: {self.api_key_name}")
        
        # Create client with authentication
        client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=30.0,
            verify=False  # For development - should be True in production
        )
        
        # Set up session authentication if credentials are available
        if self.username and self.password:
            # Perform login to get session token
            await self._authenticate_client(client)
        
        return client
    
    def _get_base_url(self, spec_data: Dict[str, Any], spec_name: str) -> str:
        """Get base URL for the API specification"""
        # Check for environment override
        env_key = f"FORCE_BASE_URL_{spec_name.upper()}"
        if os.getenv(env_key):
            return os.getenv(env_key)
        
        # Use global override
        if self.base_url:
            return self.base_url
        
        # Extract from spec
        servers = spec_data.get('servers', [])
        if servers:
            server = servers[0]
            if isinstance(server, dict):
                return server.get('url', 'http://localhost:8080')
            else:
                return server
        
        return 'http://localhost:8080'
    
    async def _authenticate_client(self, client: httpx.AsyncClient):
        """Authenticate the client and store session token"""
        if not self.username or not self.password:
            logger.warning("No credentials available for authentication")
            return
        
        try:
            logger.info(f"🔐 Authenticating with {self.login_url}")
            
            # Prepare authentication headers
            import base64
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            auth_headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # Perform login
            response = await client.post(
                self.login_url,
                headers=auth_headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            
            # Extract session token from cookies
            cookies = response.cookies
            if 'JSESSIONID' in cookies:
                self.session_id = cookies['JSESSIONID']
                logger.info(f"✅ Authentication successful, session ID: {self.session_id[:20]}...")
            else:
                logger.warning("No JSESSIONID found in login response")
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from all FastMCP instances"""
        all_tools = []
        
        for spec_name, mcp_instance in self.mcp_instances.items():
            try:
                tools = await mcp_instance.get_tools()
                logger.info(f"📋 Retrieved {len(tools)} tools from {spec_name}")
                all_tools.extend(tools)
            except Exception as e:
                logger.error(f"❌ Failed to get tools from {spec_name}: {e}")
        
        logger.info(f"📋 Total tools available: {len(all_tools)}")
        return all_tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by finding the appropriate FastMCP instance"""
        for spec_name, mcp_instance in self.mcp_instances.items():
            try:
                # Try to execute the tool with this instance
                result = await mcp_instance.call_tool(tool_name, arguments)
                logger.info(f"✅ Tool {tool_name} executed successfully via {spec_name}")
                return {
                    "status": "success",
                    "result": result,
                    "spec_name": spec_name
                }
            except Exception as e:
                # Tool not found in this instance, continue to next
                continue
        
        # Tool not found in any instance
        error_msg = f"Tool '{tool_name}' not found in any API specification"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }
    
    async def set_credentials(self, username: str = None, password: str = None, 
                            api_key_name: str = None, api_key_value: str = None,
                            login_url: str = None, base_url: str = None) -> Dict[str, Any]:
        """Set authentication credentials"""
        try:
            # Update credentials
            if username:
                self.username = username
            if password:
                self.password = password
            if api_key_name:
                self.api_key_name = api_key_name
            if api_key_value:
                self.api_key_value = api_key_value
            if login_url:
                self.login_url = login_url
            if base_url:
                self.base_url = base_url
            
            # Re-authenticate all clients
            for spec_name, client in self.http_clients.items():
                await self._authenticate_client(client)
            
            return {
                "status": "success",
                "message": "Credentials updated and clients re-authenticated",
                "username": self.username,
                "has_api_key": bool(self.api_key_name and self.api_key_value),
                "base_url": self.base_url
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to set credentials: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            for client in self.http_clients.values():
                await client.aclose()
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

# Global server instance
server_instance = None

async def get_server() -> SimplifiedFastMCPServer:
    """Get or create the global server instance"""
    global server_instance
    if server_instance is None:
        server_instance = SimplifiedFastMCPServer()
        await server_instance.initialize()
    return server_instance

# FastMCP app for tool registration
app = FastMCP("simplified-fastmcp-server")

@app.tool()
async def get_available_tools() -> str:
    """Get list of all available API tools"""
    try:
        server = await get_server()
        tools = await server.get_tools()
        
        # Format tools for display
        tool_list = []
        for tool in tools:
            tool_info = {
                "name": tool.get("name", "unknown"),
                "description": tool.get("description", "No description"),
                "input_schema": tool.get("inputSchema", {})
            }
            tool_list.append(tool_info)
        
        return json.dumps({
            "status": "success",
            "total_tools": len(tool_list),
            "tools": tool_list
        }, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Error getting tools: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@app.tool()
async def set_credentials(username: str = None, password: str = None,
                         api_key_name: str = None, api_key_value: str = None,
                         login_url: str = None, base_url: str = None) -> str:
    """Set authentication credentials for API access"""
    try:
        server = await get_server()
        result = await server.set_credentials(
            username=username,
            password=password,
            api_key_name=api_key_name,
            api_key_value=api_key_value,
            login_url=login_url,
            base_url=base_url
        )
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Error setting credentials: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@app.tool()
async def execute_api_tool(tool_name: str, arguments: str = "{}") -> str:
    """Execute an API tool with the given arguments"""
    try:
        server = await get_server()
        
        # Parse arguments
        try:
            args_dict = json.loads(arguments) if isinstance(arguments, str) else arguments
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "Invalid JSON in arguments"
            }, indent=2)
        
        result = await server.execute_tool(tool_name, args_dict)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Error executing tool {tool_name}: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simplified FastMCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9001)
    
    args = parser.parse_args()
    
    try:
        logger.info("🚀 Starting Simplified FastMCP Server...")
        
        if args.transport == "stdio":
            logger.info("📡 Using stdio transport")
            app.run(transport="stdio")
        elif args.transport == "http":
            logger.info(f"🌐 Starting HTTP server on http://{args.host}:{args.port}")
            app.run(transport="http", host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        logger.info("👋 Shutting down server...")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
    finally:
        if server_instance:
            asyncio.run(server_instance.cleanup())