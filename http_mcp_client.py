#!/usr/bin/env python3
"""
HTTP MCP Client - Communicates with MCP Server via HTTP
This client connects to the MCP server's HTTP endpoints instead of using stdio transport.
"""

import asyncio
import json
import logging
import aiohttp
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Import config
try:
    from config import config
except ImportError:
    class DefaultConfig:
        MCP_HOST = "localhost"
        MCP_PORT = 9000
        
        def get_mcp_url(self):
            return f"http://{self.MCP_HOST}:{self.MCP_PORT}"
    
    config = DefaultConfig()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("http_mcp_client")


@dataclass
class Tool:
    """Represents an MCP tool."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class HTTPMCPClient:
    """HTTP-based MCP Client that communicates with MCP server via HTTP endpoints."""
    
    def __init__(self, mcp_server_url: str = None):
        self.mcp_server_url = mcp_server_url or f"http://{config.MCP_HOST}:{config.MCP_PORT}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.available_tools: List[Tool] = []
        self.connected = False
        
        logger.info(f"Initialized HTTP MCP Client for {self.mcp_server_url}")
    
    async def connect(self) -> bool:
        """Connect to the MCP server via HTTP."""
        try:
            if self.connected:
                logger.info("Already connected to MCP server")
                return True
            
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Test connection by calling health endpoint
            async with self.session.get(f"{self.mcp_server_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"✅ Connected to MCP server: {health_data}")
                else:
                    logger.error(f"❌ MCP server health check failed: {response.status}")
                    return False
            
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
            if self.session:
                await self.session.close()
            self.connected = False
            logger.info("Disconnected from MCP server")
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server: {e}")
    
    async def _load_tools(self) -> List[Tool]:
        """Load available tools from MCP server."""
        try:
            if not self.session:
                raise Exception("Not connected to MCP server")
            
            async with self.session.get(f"{self.mcp_server_url}/tools") as response:
                if response.status == 200:
                    data = await response.json()
                    tools_data = data.get("tools", [])
                    
                    self.available_tools = []
                    for tool_data in tools_data:
                        tool = Tool(
                            name=tool_data.get("name", ""),
                            description=tool_data.get("description", ""),
                            inputSchema=tool_data.get("inputSchema", {})
                        )
                        self.available_tools.append(tool)
                    
                    logger.info(f"✅ Loaded {len(self.available_tools)} tools from MCP server")
                    return self.available_tools
                else:
                    logger.error(f"Failed to load tools: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error loading tools: {e}")
            return []
    
    async def list_tools(self) -> List[Tool]:
        """Get list of available tools from MCP server."""
        if not self.connected:
            await self.connect()
        return self.available_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server via HTTP."""
        if arguments is None:
            arguments = {}
            
        try:
            if not self.session:
                raise Exception("Not connected to MCP server")
            
            logger.info(f"Calling MCP tool: {tool_name} with arguments: {list(arguments.keys())}")
            
            # Call tool via HTTP endpoint
            payload = {
                "name": tool_name,
                "arguments": arguments
            }
            
            async with self.session.post(
                f"{self.mcp_server_url}/call_tool",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Tool {tool_name} executed successfully")
                    return {"status": "success", "data": result}
                else:
                    error_text = await response.text()
                    logger.error(f"Tool {tool_name} failed: HTTP {response.status} - {error_text}")
                    return {"status": "error", "message": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def perform_login(self) -> Dict[str, Any]:
        """Call the perform_login tool on the MCP server."""
        logger.info("Attempting to perform login via MCP server tool.")
        try:
            result = await self.call_tool("perform_login")
            if result.get("status") == "success":
                logger.info("✅ Login tool call successful.")
                return {"status": "success", "message": "Login successful"}
            else:
                error_message = result.get("message", "Unknown error during login tool call.")
                logger.error(f"❌ Login tool call failed: {error_message}")
                return {"status": "error", "message": error_message}
        except Exception as e:
            logger.error(f"Exception when calling perform_login tool: {e}")
            return {"status": "error", "message": str(e)}
    
    async def set_credentials(self, username: str = None, password: str = None, api_key: str = None) -> Dict[str, Any]:
        """Set credentials using the set_credentials tool."""
        credentials = {}
        if username:
            credentials["username"] = username
        if password:
            credentials["password"] = password
        if api_key:
            credentials["api_key_value"] = api_key
            
        return await self.call_tool("set_credentials", credentials)
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a user query by calling appropriate tools."""
        logger.info(f"Processing query: {user_query}")
        
        # For now, return a simple response
        # TODO: Implement intelligent tool selection and execution
        return {
            "status": "ok",
            "summary": f"Query processed: {user_query}. This is a placeholder response. Tool selection and execution will be implemented.",
            "tools_used": [],
            "results": []
        }


async def main():
    """Example usage of HTTP MCP Client."""
    print("HTTP MCP Client Test")
    print("===================")
    print()
    print("🔌 Using HTTP transport to connect to MCP server")
    print()
    
    # Create HTTP MCP client
    client = HTTPMCPClient()
    
    try:
        print(f"\n🔗 Connecting to MCP server at {client.mcp_server_url}...")
        if not await client.connect():
            print("Failed to connect to MCP server")
            return
        
        print("📋 Listing available tools...")
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools[:5]]}..." + (f" and {len(tools)-5} more" if len(tools) > 5 else ""))
        
        if tools:
            print("\n🧪 Testing tool execution...")
            result = await client.process_query("Show me pending payments")
            print("Result:")
            print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
    finally:
        print("\n👋 Disconnecting from MCP server")
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())