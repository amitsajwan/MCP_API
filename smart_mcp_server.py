#!/usr/bin/env python3
"""
Smart MCP Server with API Relationship Intelligence
==================================================
A sophisticated MCP server that understands API relationships, handles authentication,
and provides intelligent response truncation.
"""

import os
import json
import yaml
import asyncio
import logging
import httpx
import base64
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('smart_mcp.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("smart_mcp")

@dataclass
class APIRelationship:
    """Represents a relationship between APIs"""
    source_api: str
    target_api: str
    relationship_type: str  # 'depends_on', 'calls_after', 'uses_data_from'
    description: str
    required_fields: List[str]

@dataclass
class TruncatedResponse:
    """Represents a truncated API response"""
    items: List[Any]
    total_count: int
    returned_count: int
    truncated: bool
    truncation_note: str

class SmartMCPServer:
    """Smart MCP server with API relationship intelligence"""
    
    def __init__(self, openapi_dir: str = "./openapi_specs"):
        self.openapi_dir = Path(openapi_dir)
        self.mcp_instances = {}
        self.http_clients = {}
        self.session_id = None
        self.api_relationships = {}
        self.call_history = []
        
        # Authentication state
        self.username = os.getenv('API_USERNAME')
        self.password = os.getenv('API_PASSWORD')
        self.api_key_name = os.getenv('API_KEY_NAME')
        self.api_key_value = os.getenv('API_KEY_VALUE')
        self.login_url = os.getenv('LOGIN_URL', 'http://localhost:8080/auth/login')
        self.base_url = os.getenv('FORCE_BASE_URL', 'http://localhost:8080')
        
        # Response truncation settings
        self.max_response_items = int(os.getenv('MAX_RESPONSE_ITEMS', '100'))
        
        logger.info("🧠 Initializing Smart MCP Server...")
        logger.info(f"📂 OpenAPI directory: {self.openapi_dir}")
        logger.info(f"🔐 Username: {self.username or 'Not set'}")
        logger.info(f"🌐 Base URL: {self.base_url}")
        logger.info(f"📊 Max response items: {self.max_response_items}")
    
    async def initialize(self) -> bool:
        """Initialize the server with API relationship mapping"""
        try:
            if not self.openapi_dir.exists():
                logger.error(f"OpenAPI directory not found: {self.openapi_dir}")
                return False
            
            # Load API relationships
            await self._load_api_relationships()
            
            # Load all OpenAPI specifications
            spec_files = list(self.openapi_dir.glob("*.yaml"))
            if not spec_files:
                logger.warning(f"No YAML files found in {self.openapi_dir}")
                return False
            
            logger.info(f"📋 Found {len(spec_files)} OpenAPI specification files")
            
            for spec_file in spec_files:
                await self._load_openapi_spec(spec_file)
            
            logger.info(f"✅ Initialized {len(self.mcp_instances)} MCP instances")
            logger.info(f"🔗 Loaded {len(self.api_relationships)} API relationships")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            return False
    
    async def _load_api_relationships(self):
        """Load API relationships configuration"""
        # Define intelligent API relationships
        self.api_relationships = {
            # Cash API relationships
            'cash_api': {
                'depends_on': [],
                'calls_after': ['securities_api'],  # Cash operations often follow securities trades
                'uses_data_from': ['securities_api', 'cls_api'],
                'provides_data_to': ['cls_api']
            },
            # Securities API relationships
            'securities_api': {
                'depends_on': [],
                'calls_after': [],
                'uses_data_from': [],
                'provides_data_to': ['cash_api', 'cls_api']
            },
            # CLS API relationships
            'cls_api': {
                'depends_on': ['cash_api', 'securities_api'],
                'calls_after': ['cash_api', 'securities_api'],
                'uses_data_from': ['cash_api', 'securities_api'],
                'provides_data_to': []
            },
            # Mailbox API relationships
            'mailbox_api': {
                'depends_on': [],
                'calls_after': ['cash_api', 'securities_api', 'cls_api'],
                'uses_data_from': ['cash_api', 'securities_api', 'cls_api'],
                'provides_data_to': []
            }
        }
        
        logger.info("🔗 API relationships loaded")
    
    async def _load_openapi_spec(self, spec_file: Path):
        """Load a single OpenAPI specification and create MCP instance"""
        try:
            spec_name = spec_file.stem
            logger.info(f"📖 Loading OpenAPI spec: {spec_name}")
            
            # Load the OpenAPI specification
            with open(spec_file, 'r', encoding='utf-8') as f:
                spec_data = yaml.safe_load(f)
            
            # Create HTTP client with authentication
            client = await self._create_authenticated_client(spec_data, spec_name)
            
            # Create FastMCP instance using from_openapi
            logger.info(f"🔧 Creating MCP instance for {spec_name}...")
            mcp_instance = FastMCP.from_openapi(
                openapi_spec=spec_data,
                client=client,
                name=f"{spec_name}-api"
            )
            
            # Store the instance and client
            self.mcp_instances[spec_name] = mcp_instance
            self.http_clients[spec_name] = client
            
            logger.info(f"✅ Created MCP instance for {spec_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load spec {spec_file}: {e}")
    
    async def _create_authenticated_client(self, spec_data: Dict[str, Any], spec_name: str) -> httpx.AsyncClient:
        """Create an authenticated HTTP client with JSESSIONID and API key support"""
        
        # Determine base URL
        base_url = self._get_base_url(spec_data, spec_name)
        
        # Prepare headers
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Smart-MCP-Client/1.0'
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
            # Perform login to get JSESSIONID
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
        """Authenticate the client and store JSESSIONID"""
        if not self.username or not self.password:
            logger.warning("No credentials available for authentication")
            return
        
        try:
            logger.info(f"🔐 Authenticating with {self.login_url}")
            
            # Prepare authentication headers
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
            
            # Extract JSESSIONID from cookies
            cookies = response.cookies
            if 'JSESSIONID' in cookies:
                self.session_id = cookies['JSESSIONID']
                logger.info(f"✅ Authentication successful, JSESSIONID: {self.session_id[:20]}...")
                
                # Set JSESSIONID in all clients
                for spec_name, http_client in self.http_clients.items():
                    http_client.cookies.set('JSESSIONID', self.session_id)
                    logger.info(f"🍪 Set JSESSIONID for {spec_name}")
            else:
                logger.warning("No JSESSIONID found in login response")
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
    
    def _truncate_response(self, data: Any) -> TruncatedResponse:
        """Intelligently truncate API responses to prevent huge responses"""
        if not isinstance(data, (list, dict)):
            return TruncatedResponse(
                items=[data],
                total_count=1,
                returned_count=1,
                truncated=False,
                truncation_note=""
            )
        
        # Handle list responses
        if isinstance(data, list):
            total_count = len(data)
            if total_count <= self.max_response_items:
                return TruncatedResponse(
                    items=data,
                    total_count=total_count,
                    returned_count=total_count,
                    truncated=False,
                    truncation_note=""
                )
            
            logger.info(f"📊 Truncating list response from {total_count} to {self.max_response_items} items")
            
            truncated_items = data[:self.max_response_items]
            return TruncatedResponse(
                items=truncated_items,
                total_count=total_count,
                returned_count=len(truncated_items),
                truncated=True,
                truncation_note=f"Response limited to {self.max_response_items} items out of {total_count} total items"
            )
        
        # Handle dict responses - look for common list fields
        if isinstance(data, dict):
            truncated_data = data.copy()
            truncation_info = {}
            
            # Common field names that might contain lists
            list_fields = ['items', 'data', 'results', 'records', 'list', 'array', 'values', 'payments', 'securities', 'messages']
            
            for field in list_fields:
                if field in data and isinstance(data[field], list):
                    original_list = data[field]
                    if len(original_list) > self.max_response_items:
                        logger.info(f"📊 Truncating field '{field}' from {len(original_list)} to {self.max_response_items} items")
                        
                        truncated_data[field] = original_list[:self.max_response_items]
                        truncation_info[f"{field}_truncated"] = True
                        truncation_info[f"{field}_total_count"] = len(original_list)
                        truncation_info[f"{field}_returned_count"] = self.max_response_items
            
            # Add truncation metadata if any fields were truncated
            if truncation_info:
                truncated_data["_truncation_info"] = {
                    **truncation_info,
                    "truncation_note": "Some list fields were limited to prevent huge responses"
                }
            
            return TruncatedResponse(
                items=truncated_data,
                total_count=1,
                returned_count=1,
                truncated=bool(truncation_info),
                truncation_note=truncation_info.get("truncation_note", "")
            )
        
        return TruncatedResponse(
            items=[data],
            total_count=1,
            returned_count=1,
            truncated=False,
            truncation_note=""
        )
    
    def _determine_api_call_order(self, requested_tools: List[str]) -> List[Tuple[str, str]]:
        """Determine the optimal order for API calls based on relationships"""
        api_calls = []
        
        # Group tools by API
        api_tools = {}
        for tool_name in requested_tools:
            for spec_name, mcp_instance in self.mcp_instances.items():
                try:
                    # This is a simplified check - in reality you'd need to check if tool exists
                    if spec_name in tool_name.lower() or any(api in tool_name.lower() for api in ['cash', 'securities', 'cls', 'mailbox']):
                        if spec_name not in api_tools:
                            api_tools[spec_name] = []
                        api_tools[spec_name].append(tool_name)
                        break
                except:
                    continue
        
        # Determine call order based on relationships
        call_order = []
        processed_apis = set()
        
        # First, add APIs with no dependencies
        for api_name in api_tools.keys():
            if api_name in self.api_relationships:
                deps = self.api_relationships[api_name].get('depends_on', [])
                if not deps or all(dep in processed_apis for dep in deps):
                    call_order.append(api_name)
                    processed_apis.add(api_name)
        
        # Then add remaining APIs
        for api_name in api_tools.keys():
            if api_name not in processed_apis:
                call_order.append(api_name)
                processed_apis.add(api_name)
        
        # Build final call list
        for api_name in call_order:
            for tool_name in api_tools[api_name]:
                api_calls.append((api_name, tool_name))
        
        return api_calls
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from all MCP instances"""
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
        """Execute a tool with intelligent response truncation"""
        for spec_name, mcp_instance in self.mcp_instances.items():
            try:
                # Try to execute the tool with this instance
                result = await mcp_instance.call_tool(tool_name, arguments)
                
                # Apply intelligent truncation
                if isinstance(result, dict) and 'content' in result:
                    content = result['content']
                    if isinstance(content, list) and len(content) > 0:
                        text_content = content[0].get('text', '')
                        try:
                            # Try to parse as JSON
                            json_data = json.loads(text_content)
                            truncated_response = self._truncate_response(json_data)
                            
                            # Rebuild the response with truncated data
                            if truncated_response.truncated:
                                truncated_json = json.dumps(truncated_response.items, indent=2)
                                if truncated_response.truncation_note:
                                    truncated_json += f"\n\n<!-- {truncated_response.truncation_note} -->"
                                
                                result['content'] = [{'type': 'text', 'text': truncated_json}]
                                result['truncation_info'] = {
                                    'total_count': truncated_response.total_count,
                                    'returned_count': truncated_response.returned_count,
                                    'truncated': True,
                                    'note': truncated_response.truncation_note
                                }
                        except json.JSONDecodeError:
                            # Not JSON, leave as is
                            pass
                
                # Record the call
                self.call_history.append({
                    'tool_name': tool_name,
                    'spec_name': spec_name,
                    'timestamp': asyncio.get_event_loop().time(),
                    'success': True
                })
                
                logger.info(f"✅ Tool {tool_name} executed successfully via {spec_name}")
                return {
                    "status": "success",
                    "result": result,
                    "spec_name": spec_name,
                    "truncation_applied": result.get('truncation_info', {}).get('truncated', False)
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
    
    async def execute_multiple_tools(self, tool_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple tools with intelligent ordering"""
        tool_names = [req.get('tool_name') for req in tool_requests]
        call_order = self._determine_api_call_order(tool_names)
        
        results = []
        for spec_name, tool_name in call_order:
            # Find the request for this tool
            request = next((req for req in tool_requests if req.get('tool_name') == tool_name), {})
            arguments = request.get('arguments', {})
            
            result = await self.execute_tool(tool_name, arguments)
            results.append(result)
        
        return results
    
    async def set_credentials(self, username: str = None, password: str = None, 
                            api_key_name: str = None, api_key_value: str = None,
                            login_url: str = None, base_url: str = None) -> Dict[str, Any]:
        """Set authentication credentials and re-authenticate"""
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
                "has_jsessionid": bool(self.session_id),
                "base_url": self.base_url
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to set credentials: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_api_relationships(self) -> Dict[str, Any]:
        """Get API relationship information"""
        return {
            "relationships": self.api_relationships,
            "call_history": self.call_history[-10:],  # Last 10 calls
            "total_calls": len(self.call_history)
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

async def get_server() -> SmartMCPServer:
    """Get or create the global server instance"""
    global server_instance
    if server_instance is None:
        server_instance = SmartMCPServer()
        await server_instance.initialize()
    return server_instance

# FastMCP app for tool registration
app = FastMCP("smart-mcp-server")

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

@app.tool()
async def execute_multiple_tools(tool_requests: str) -> str:
    """Execute multiple tools with intelligent ordering"""
    try:
        server = await get_server()
        
        # Parse tool requests
        try:
            requests = json.loads(tool_requests) if isinstance(tool_requests, str) else tool_requests
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "Invalid JSON in tool_requests"
            }, indent=2)
        
        results = await server.execute_multiple_tools(requests)
        return json.dumps({
            "status": "success",
            "results": results,
            "total_executed": len(results)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Error executing multiple tools: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@app.tool()
async def get_api_relationships() -> str:
    """Get API relationship information and call history"""
    try:
        server = await get_server()
        relationships = await server.get_api_relationships()
        return json.dumps(relationships, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Error getting API relationships: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9002)
    
    args = parser.parse_args()
    
    try:
        logger.info("🧠 Starting Smart MCP Server...")
        
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