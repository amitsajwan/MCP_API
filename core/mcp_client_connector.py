"""
MCP Client Connector for Demo MCP System
Connects to MCP Server via stdio protocol to discover and execute tools
The MCP Server loads OpenAPI specs and exposes tools via MCP protocol
"""

import json
import logging
import asyncio
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPClientConnector:
    """
    Connects to MCP Server via stdio protocol
    MCP Server is responsible for loading OpenAPI specs and exposing tools
    Client uses MCP protocol to list and execute tools
    """
    
    def __init__(self, server_command: Optional[List[str]] = None):
        """
        Initialize MCP client connector
        
        Args:
            server_command: Command to start MCP server
                          e.g., ["python", "mcp_server_fastmcp.py"]
        """
        self.server_command = server_command or ["python", "mcp_server_fastmcp.py"]
        self.session = None
        self.server_process = None
        self.connected = False
        self.available_tools: List[Dict[str, Any]] = []
    
    async def connect(self) -> bool:
        """
        Connect to MCP server via stdio
        MCP server loads OpenAPI specs on startup
        """
        try:
            logger.info(f"Starting MCP server: {' '.join(self.server_command)}")
            
            # Start MCP server process
            self.server_process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # In production, use actual MCP protocol:
            # from mcp.client import ClientSession
            # from mcp.client.stdio import stdio_client
            # self.session = await stdio_client(
            #     self.server_process.stdin,
            #     self.server_process.stdout
            # )
            # await self.session.initialize()
            
            # For demo, simulate connection
            await asyncio.sleep(0.5)
            
            # Discover tools via MCP protocol
            await self._discover_tools_via_mcp()
            
            self.connected = True
            logger.info(f"✓ Connected to MCP server, discovered {len(self.available_tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def _discover_tools_via_mcp(self) -> None:
        """
        Use MCP protocol to list available tools
        MCP Server exposes tools after loading OpenAPI specs
        """
        try:
            # In production, use MCP protocol:
            # tools_response = await self.session.list_tools()
            # self.available_tools = [
            #     {
            #         "name": tool.name,
            #         "description": tool.description,
            #         "parameters": tool.inputSchema
            #     }
            #     for tool in tools_response.tools
            # ]
            
            # For demo, simulate MCP tool discovery
            # In reality, these come from OpenAPI spec loaded by MCP server
            self.available_tools = await self._simulate_mcp_tool_discovery()
            
            logger.info(f"Discovered {len(self.available_tools)} tools via MCP protocol")
            
        except Exception as e:
            logger.error(f"Failed to discover tools via MCP: {e}")
            self.available_tools = []
    
    async def _simulate_mcp_tool_discovery(self) -> List[Dict[str, Any]]:
        """
        Simulate MCP tool discovery
        In production, this comes from MCP server's list_tools() response
        MCP server loads OpenAPI specs and exposes them as tools
        """
        # Simulate network delay
        await asyncio.sleep(0.3)
        
        # These would come from MCP server after it loads OpenAPI specs
        # MCP Server flow:
        # 1. Load cash_api.yaml → Extract tools
        # 2. Load securities_api.yaml → Extract tools  
        # 3. Load mailbox_api.yaml → Extract tools
        # 4. Load cls_api.yaml → Extract tools
        # 5. Expose all via MCP protocol
        
        return [
            {
                "name": "get_accounts",
                "description": "Retrieve list of all user accounts",
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"}
                },
                "category": "Account",
                "source": "cash_api.yaml"
            },
            {
                "name": "get_account_balance",
                "description": "Get balance for specific account",
                "parameters": {
                    "account_id": {"type": "string", "description": "Account identifier"}
                },
                "category": "Account",
                "source": "cash_api.yaml"
            },
            {
                "name": "get_securities",
                "description": "Get securities holdings",
                "parameters": {
                    "portfolio_id": {"type": "string", "description": "Portfolio identifier"}
                },
                "category": "Securities",
                "source": "securities_api.yaml"
            },
            {
                "name": "get_messages",
                "description": "Retrieve mailbox messages",
                "parameters": {
                    "mailbox_id": {"type": "string", "description": "Mailbox identifier"}
                },
                "category": "Mailbox",
                "source": "mailbox_api.yaml"
            },
            {
                "name": "execute_cls_check",
                "description": "Execute CLS check",
                "parameters": {
                    "transaction_id": {"type": "string", "description": "Transaction identifier"}
                },
                "category": "CLS",
                "source": "cls_api.yaml"
            }
        ]
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all tools available via MCP protocol
        
        Returns:
            List of tools discovered from MCP server
        """
        if not self.connected:
            await self.connect()
        
        return self.available_tools
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool via MCP protocol
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            
        Returns:
            Tool execution result
        """
        if not self.connected:
            await self.connect()
        
        try:
            # In production, use MCP protocol:
            # result = await self.session.call_tool(tool_name, parameters)
            # return {
            #     "tool": tool_name,
            #     "success": True,
            #     "result": result.content[0].text if result.content else None
            # }
            
            # For demo, simulate tool execution
            await asyncio.sleep(0.2)  # Simulate network call
            
            return {
                "tool": tool_name,
                "parameters": parameters,
                "success": True,
                "result": f"Tool {tool_name} executed successfully via MCP protocol",
                "execution_time": "0.2s"
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "tool": tool_name,
                "success": False,
                "error": str(e)
            }
    
    async def load_openapi_spec(self, spec_path: str, api_name: str) -> Dict[str, Any]:
        """
        Request MCP server to load an OpenAPI spec
        MCP server will parse spec and expose new tools
        
        Args:
            spec_path: Path to OpenAPI spec file
            api_name: Name for the API
            
        Returns:
            Result with count of tools added
        """
        try:
            # In production, use MCP protocol:
            # result = await self.session.call_tool(
            #     "load_api_spec",
            #     {"file_path": spec_path, "api_name": api_name}
            # )
            
            # For demo, simulate loading
            logger.info(f"Requesting MCP server to load: {spec_path}")
            await asyncio.sleep(0.5)
            
            # Refresh tool list after loading
            await self._discover_tools_via_mcp()
            
            return {
                "success": True,
                "api_name": api_name,
                "spec_path": spec_path,
                "tools_added": 5,  # Simulated
                "message": f"API '{api_name}' loaded successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to load OpenAPI spec: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        try:
            if self.session:
                # In production: await self.session.close()
                pass
            
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            
            self.connected = False
            logger.info("Disconnected from MCP server")
            
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about specific tool"""
        for tool in self.available_tools:
            if tool["name"] == tool_name:
                return tool
        return None
    
    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """Search tools by name or description"""
        query_lower = query.lower()
        results = []
        
        for tool in self.available_tools:
            if (query_lower in tool["name"].lower() or 
                query_lower in tool["description"].lower()):
                results.append(tool)
        
        return results
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tools by category"""
        return [tool for tool in self.available_tools if tool.get("category") == category]
    
    def get_status(self) -> Dict[str, Any]:
        """Get connection status"""
        return {
            "connected": self.connected,
            "server_command": " ".join(self.server_command),
            "tools_available": len(self.available_tools),
            "categories": list(set(t.get("category", "Unknown") for t in self.available_tools))
        }
