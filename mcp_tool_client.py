#!/usr/bin/env python3
"""
MCP Tool Client
A comprehensive client for using MCP tools registered with app.tool().
This client can connect to FastMCP servers and execute their registered tools.
"""

import asyncio
import json
import logging
import os
import sys
import subprocess
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime
import traceback

# FastMCP 2.0 imports
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_tool_client")

@dataclass
class ToolInfo:
    """Information about an available tool."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_params: List[str]
    optional_params: List[str]

@dataclass
class ToolCall:
    """Represents a tool call to be executed."""
    tool_name: str
    arguments: Dict[str, Any]
    reason: Optional[str] = None

@dataclass
class ToolResult:
    """Represents the result of a tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    response_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "response_size": self.response_size,
        }

class MCPToolClient:
    """Client for using MCP tools registered with app.tool()."""
    
    def __init__(self, server_script: str = None, server_args: List[str] = None):
        """
        Initialize the MCP Tool Client.
        
        Args:
            server_script: Path to the server script to run
            server_args: Additional arguments to pass to the server
        """
        self.server_script = server_script or "fastmcp_chatbot_server.py"
        self.server_args = server_args or ["--transport", "stdio"]
        self.client: Optional[Client] = None
        self.client_context = None
        self.connected = False
        self.available_tools: List[ToolInfo] = []
        
        logger.info(f"Initialized MCP Tool Client for server: {self.server_script}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> bool:
        """Connect to the MCP server."""
        try:
            if self.connected:
                logger.info("Already connected to MCP server")
                return True
            
            # Create FastMCP client with stdio transport
            transport = StdioTransport(
                command=sys.executable,
                args=[self.server_script] + self.server_args,
                env=os.environ.copy()
            )
            
            # Create client with stdio transport
            self.client = Client(transport=transport)
            
            # Enter the FastMCP client's async context manager
            self.client_context = self.client.__aenter__()
            await self.client_context
            
            # Load available tools
            await self._load_tools()
            
            self.connected = True
            logger.info(f"✅ Connected to MCP server with {len(self.available_tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MCP server: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        try:
            if self.client_context:
                await self.client.__aexit__(None, None, None)
                self.client_context = None
            
            self.connected = False
            logger.info("Disconnected from MCP server")
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server: {e}")
    
    async def _load_tools(self) -> List[ToolInfo]:
        """Load available tools from the MCP server."""
        try:
            if not self.client:
                raise Exception("Not connected to MCP server")
            
            # Get tools from MCP server
            tools_response = await self.client.list_tools()
            
            # Convert to ToolInfo objects
            self.available_tools = []
            if isinstance(tools_response, list):
                for tool in tools_response:
                    tool_dict = tool.model_dump() if hasattr(tool, 'model_dump') else (tool.dict() if hasattr(tool, 'dict') else tool)
                    tool_info = self._parse_tool_info(tool_dict)
                    self.available_tools.append(tool_info)
            elif isinstance(tools_response, dict) and 'tools' in tools_response:
                for tool in tools_response['tools']:
                    tool_info = self._parse_tool_info(tool)
                    self.available_tools.append(tool_info)
            
            logger.info(f"✅ Loaded {len(self.available_tools)} tools from MCP server")
            return self.available_tools
            
        except Exception as e:
            logger.error(f"Error loading tools: {e}")
            return []
    
    def _parse_tool_info(self, tool_dict: Dict[str, Any]) -> ToolInfo:
        """Parse tool dictionary into ToolInfo object."""
        name = tool_dict.get('name', 'unknown')
        description = tool_dict.get('description', 'No description available')
        
        # Parse parameters from inputSchema
        parameters = {}
        required_params = []
        optional_params = []
        
        input_schema = tool_dict.get('inputSchema', {})
        if isinstance(input_schema, dict):
            properties = input_schema.get('properties', {})
            required = input_schema.get('required', [])
            
            for param_name, param_info in properties.items():
                if isinstance(param_info, dict):
                    parameters[param_name] = {
                        'type': param_info.get('type', 'string'),
                        'description': param_info.get('description', ''),
                        'required': param_name in required
                    }
                    
                    if param_name in required:
                        required_params.append(param_name)
                    else:
                        optional_params.append(param_name)
        
        return ToolInfo(
            name=name,
            description=description,
            parameters=parameters,
            required_params=required_params,
            optional_params=optional_params
        )
    
    async def list_tools(self) -> List[ToolInfo]:
        """Get list of available tools."""
        if not self.connected:
            await self.connect()
        return self.available_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> ToolResult:
        """Call a tool on the MCP server."""
        if arguments is None:
            arguments = {}
        
        start_time = datetime.now()
        
        try:
            if not self.client:
                raise Exception("Not connected to MCP server")
            
            logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
            
            # Call tool using FastMCP 2.0 protocol
            result = await self.client.call_tool(tool_name, arguments)
            
            # Process result
            if isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                except json.JSONDecodeError:
                    parsed_result = {"message": result}
            elif isinstance(result, dict):
                parsed_result = result
            else:
                parsed_result = {"result": result}
            
            execution_time = (datetime.now() - start_time).total_seconds()
            response_size = len(str(parsed_result))
            
            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=parsed_result,
                execution_time=execution_time,
                response_size=response_size
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error calling tool {tool_name}: {e}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time,
                response_size=0
            )
    
    async def execute_tool_plan(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute a plan of tool calls and collect results."""
        results = []
        for i, tc in enumerate(tool_calls, 1):
            logger.info(f"Executing tool {i}/{len(tool_calls)}: {tc.tool_name}")
            result = await self.call_tool(tc.tool_name, tc.arguments)
            results.append(result)
        return results
    
    def get_tool_by_name(self, tool_name: str) -> Optional[ToolInfo]:
        """Get tool information by name."""
        for tool in self.available_tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def find_tools_by_keyword(self, keyword: str) -> List[ToolInfo]:
        """Find tools by keyword in name or description."""
        keyword_lower = keyword.lower()
        matching_tools = []
        
        for tool in self.available_tools:
            if (keyword_lower in tool.name.lower() or 
                keyword_lower in tool.description.lower()):
                matching_tools.append(tool)
        
        return matching_tools
    
    def print_tools_summary(self):
        """Print a summary of available tools."""
        if not self.available_tools:
            print("No tools available")
            return
        
        print(f"\n📋 Available Tools ({len(self.available_tools)}):")
        print("=" * 50)
        
        for tool in self.available_tools:
            print(f"\n🔧 {tool.name}")
            print(f"   Description: {tool.description}")
            
            if tool.parameters:
                print("   Parameters:")
                for param_name, param_info in tool.parameters.items():
                    required = " (required)" if param_info.get('required', False) else " (optional)"
                    param_type = param_info.get('type', 'string')
                    param_desc = param_info.get('description', '')
                    print(f"     - {param_name}: {param_type}{required}")
                    if param_desc:
                        print(f"       {param_desc}")
            else:
                print("   No parameters")
    
    async def interactive_mode(self):
        """Start interactive mode for tool calling."""
        print("\n🚀 MCP Tool Client - Interactive Mode")
        print("=" * 40)
        print("Available commands:")
        print("  list                    - List all available tools")
        print("  info <tool_name>        - Get detailed info about a tool")
        print("  call <tool_name> <args> - Call a tool with arguments")
        print("  search <keyword>        - Search for tools by keyword")
        print("  help                    - Show this help")
        print("  quit                    - Exit interactive mode")
        print()
        
        while True:
            try:
                user_input = input("mcp> ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split()
                command = parts[0].lower()
                
                if command == "quit" or command == "exit":
                    print("👋 Goodbye!")
                    break
                elif command == "help":
                    print("Available commands: list, info, call, search, help, quit")
                elif command == "list":
                    self.print_tools_summary()
                elif command == "info" and len(parts) > 1:
                    tool_name = parts[1]
                    tool = self.get_tool_by_name(tool_name)
                    if tool:
                        print(f"\n🔧 {tool.name}")
                        print(f"Description: {tool.description}")
                        print(f"Required parameters: {tool.required_params}")
                        print(f"Optional parameters: {tool.optional_params}")
                        if tool.parameters:
                            print("Parameter details:")
                            for param_name, param_info in tool.parameters.items():
                                print(f"  - {param_name}: {param_info}")
                    else:
                        print(f"Tool '{tool_name}' not found")
                elif command == "search" and len(parts) > 1:
                    keyword = " ".join(parts[1:])
                    matching_tools = self.find_tools_by_keyword(keyword)
                    if matching_tools:
                        print(f"\nFound {len(matching_tools)} tools matching '{keyword}':")
                        for tool in matching_tools:
                            print(f"  - {tool.name}: {tool.description}")
                    else:
                        print(f"No tools found matching '{keyword}'")
                elif command == "call" and len(parts) > 1:
                    tool_name = parts[1]
                    tool = self.get_tool_by_name(tool_name)
                    if not tool:
                        print(f"Tool '{tool_name}' not found")
                        continue
                    
                    # Parse arguments from remaining parts
                    args = {}
                    if len(parts) > 2:
                        # Simple argument parsing - expects key=value format
                        for arg in parts[2:]:
                            if "=" in arg:
                                key, value = arg.split("=", 1)
                                # Try to parse as JSON, fallback to string
                                try:
                                    args[key] = json.loads(value)
                                except json.JSONDecodeError:
                                    args[key] = value
                            else:
                                print(f"Invalid argument format: {arg} (expected key=value)")
                                continue
                    
                    print(f"Calling {tool_name} with arguments: {args}")
                    result = await self.call_tool(tool_name, args)
                    
                    if result.success:
                        print("✅ Tool executed successfully:")
                        print(json.dumps(result.result, indent=2))
                    else:
                        print(f"❌ Tool execution failed: {result.error}")
                else:
                    print("Unknown command. Type 'help' for available commands.")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

# Convenience functions for common operations
async def create_client(server_script: str = None, server_args: List[str] = None) -> MCPToolClient:
    """Create and connect an MCP Tool Client."""
    client = MCPToolClient(server_script, server_args)
    await client.connect()
    return client

async def call_tool_simple(server_script: str, tool_name: str, arguments: Dict[str, Any] = None) -> ToolResult:
    """Simple function to call a single tool."""
    async with MCPToolClient(server_script) as client:
        return await client.call_tool(tool_name, arguments)

async def list_tools_simple(server_script: str) -> List[ToolInfo]:
    """Simple function to list available tools."""
    async with MCPToolClient(server_script) as client:
        return await client.list_tools()

async def main():
    """Main entry point for interactive mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Tool Client")
    parser.add_argument("--server", default="fastmcp_chatbot_server.py", 
                       help="Server script to connect to")
    parser.add_argument("--args", nargs="*", default=["--transport", "stdio"],
                       help="Additional arguments for the server")
    parser.add_argument("--tool", help="Tool name to call")
    parser.add_argument("--args-json", help="JSON string of arguments for the tool")
    parser.add_argument("--list", action="store_true", help="List available tools and exit")
    
    args = parser.parse_args()
    
    try:
        async with MCPToolClient(args.server, args.args) as client:
            if args.list:
                client.print_tools_summary()
            elif args.tool:
                arguments = {}
                if args.args_json:
                    try:
                        arguments = json.loads(args.args_json)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON arguments: {e}")
                        return 1
                
                result = await client.call_tool(args.tool, arguments)
                if result.success:
                    print(json.dumps(result.result, indent=2))
                else:
                    print(f"Error: {result.error}")
                    return 1
            else:
                await client.interactive_mode()
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))