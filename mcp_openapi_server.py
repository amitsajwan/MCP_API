#!/usr/bin/env python3
"""
MCP OpenAPI Server

This MCP server can parse OpenAPI specifications and automatically generate
MCP tools that can be called by MCP clients to interact with REST APIs.

Usage:
    python mcp_openapi_server.py <openapi-spec.yaml>
"""

import asyncio
import json
import logging
import sys
import yaml
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin
import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAPIParser:
    """Parses OpenAPI specifications and extracts tool definitions."""
    
    def __init__(self, spec_data: Dict[str, Any]):
        self.spec = spec_data
        self.schemas = spec_data.get('components', {}).get('schemas', {})
        self.servers = spec_data.get('servers', [])
        self.base_url = self.servers[0]['url'] if self.servers else ''
    
    def parse_operations(self) -> List[Dict[str, Any]]:
        """Parse all operations from the OpenAPI spec."""
        operations = []
        paths = self.spec.get('paths', {})
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if isinstance(operation, dict) and 'operationId' in operation:
                    op_data = {
                        'operationId': operation['operationId'],
                        'method': method.upper(),
                        'path': path,
                        'summary': operation.get('summary', ''),
                        'description': operation.get('description', ''),
                        'parameters': operation.get('parameters', []),
                        'responses': operation.get('responses', {}),
                        'tags': operation.get('tags', [])
                    }
                    operations.append(op_data)
        
        return operations
    
    def resolve_schema_ref(self, ref: str) -> Dict[str, Any]:
        """Resolve a $ref reference to a schema."""
        if ref.startswith('#/components/schemas/'):
            schema_name = ref.split('/')[-1]
            return self.schemas.get(schema_name, {})
        return {}
    
    def get_parameter_schema(self, param: Dict[str, Any]) -> Dict[str, Any]:
        """Get the schema for a parameter."""
        schema = param.get('schema', {})
        if '$ref' in schema:
            return self.resolve_schema_ref(schema['$ref'])
        return schema
    
    def get_response_schema(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Get the schema for a response."""
        content = response.get('content', {})
        for content_type, media_type in content.items():
            if 'schema' in media_type:
                schema = media_type['schema']
                if '$ref' in schema:
                    return self.resolve_schema_ref(schema['$ref'])
                return schema
        return {}

class MCPOpenAPIServer:
    """MCP Server that generates tools from OpenAPI specifications."""
    
    def __init__(self, openapi_spec_path: str):
        self.spec_path = openapi_spec_path
        self.spec_data = self._load_spec()
        self.parser = OpenAPIParser(self.spec_data)
        self.operations = self.parser.parse_operations()
        self.http_client = httpx.AsyncClient()
        
        # Create MCP server
        self.server = Server("openapi-mcp-server")
        self._register_handlers()
    
    def _load_spec(self) -> Dict[str, Any]:
        """Load OpenAPI specification from file."""
        try:
            with open(self.spec_path, 'r') as f:
                if self.spec_path.endswith('.yaml') or self.spec_path.endswith('.yml'):
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load OpenAPI spec: {e}")
            raise
    
    def _register_handlers(self):
        """Register MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List all available tools generated from OpenAPI spec."""
            tools = []
            
            for op in self.operations:
                # Build tool input schema
                input_schema = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
                
                # Add parameters
                for param in op['parameters']:
                    param_name = param['name']
                    param_schema = self.parser.get_parameter_schema(param)
                    
                    input_schema['properties'][param_name] = {
                        "type": param_schema.get('type', 'string'),
                        "description": param.get('description', ''),
                    }
                    
                    # Add enum values if present
                    if 'enum' in param:
                        input_schema['properties'][param_name]['enum'] = param['enum']
                    elif 'enum' in param_schema:
                        input_schema['properties'][param_name]['enum'] = param_schema['enum']
                    
                    # Add example if present
                    if 'example' in param:
                        input_schema['properties'][param_name]['example'] = param['example']
                    elif 'example' in param_schema:
                        input_schema['properties'][param_name]['example'] = param_schema['example']
                    
                    if param.get('required', False):
                        input_schema['required'].append(param_name)
                
                # Create tool definition
                tool = Tool(
                    name=op['operationId'],
                    description=op['summary'] or op['description'] or f"{op['method']} {op['path']}",
                    inputSchema=input_schema
                )
                tools.append(tool)
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            """Execute a tool by making the corresponding API call."""
            try:
                # Find the operation
                operation = None
                for op in self.operations:
                    if op['operationId'] == name:
                        operation = op
                        break
                
                if not operation:
                    return {
                        "content": [{"type": "text", "text": f"Tool '{name}' not found"}],
                        "isError": True,
                        "meta": None
                    }
                
                # Build the request
                url = urljoin(self.parser.base_url, operation['path'])
                
                # Prepare parameters
                params = {}
                for param in operation['parameters']:
                    param_name = param['name']
                    if param_name in arguments:
                        if param['in'] == 'query':
                            params[param_name] = arguments[param_name]
                        elif param['in'] == 'path':
                            # Replace path parameters
                            url = url.replace(f"{{{param_name}}}", str(arguments[param_name]))
                
                # Make the HTTP request
                response = await self.http_client.request(
                    method=operation['method'],
                    url=url,
                    params=params if operation['method'] == 'GET' else None,
                    json=arguments if operation['method'] in ['POST', 'PUT', 'PATCH'] else None,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                )
                
                # Handle response
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        result_text = json.dumps(response_data, indent=2)
                    except:
                        result_text = response.text
                    
                    return {
                        "content": [{"type": "text", "text": result_text}],
                        "isError": False,
                        "meta": None
                    }
                else:
                    error_text = f"API Error {response.status_code}: {response.text}"
                    return {
                        "content": [{"type": "text", "text": error_text}],
                        "isError": True,
                        "meta": None
                    }
                
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True,
                    "meta": None
                }
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="openapi-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={}
                    )
                )
            )

def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python mcp_openapi_server.py <openapi-spec.yaml>")
        sys.exit(1)
    
    spec_path = sys.argv[1]
    
    try:
        server = MCPOpenAPIServer(spec_path)
        print(f"Starting MCP OpenAPI Server with spec: {spec_path}")
        print(f"Found {len(server.operations)} operations:")
        for op in server.operations:
            print(f"  - {op['operationId']}: {op['method']} {op['path']}")
        
        asyncio.run(server.run())
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()