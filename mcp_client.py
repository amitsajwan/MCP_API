"""
MCP Client Implementation - Model Context Protocol Client
Connects to MCP servers and provides tool execution capabilities
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import subprocess
import os

from mcp.client import ClientSession
from mcp.client.stdio import stdio_client
from mcp.types import (
    Tool, Resource, CallToolRequest, ListToolsRequest, 
    ListResourcesRequest, ReadResourceRequest
)

logger = logging.getLogger(__name__)


class IntelligentOrchestrationMCPClient:
    """
    MCP Client for Intelligent API Orchestration System
    Connects to MCP servers and executes orchestration tools
    """
    
    def __init__(self, server_command: Optional[List[str]] = None):
        """
        Initialize MCP client
        
        Args:
            server_command: Command to start the MCP server
        """
        self.server_command = server_command or [
            "python", "-m", "mcp_server"
        ]
        self.session: Optional[ClientSession] = None
        self.available_tools: Dict[str, Tool] = {}
        self.available_resources: Dict[str, Resource] = {}
        self.connected = False
    
    async def connect(self) -> bool:
        """Connect to the MCP server"""
        try:
            if self.session:
                await self.disconnect()
            
            # Start server process
            self.server_process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Create client session
            self.session = await stdio_client(
                self.server_process.stdin,
                self.server_process.stdout
            )
            
            # Initialize session
            await self.session.initialize()
            
            # Load available tools and resources
            await self._load_capabilities()
            
            self.connected = True
            logger.info("Successfully connected to MCP server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            
            if hasattr(self, 'server_process'):
                self.server_process.terminate()
                self.server_process.wait()
            
            self.connected = False
            logger.info("Disconnected from MCP server")
            
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    async def _load_capabilities(self):
        """Load available tools and resources from server"""
        try:
            # Load tools
            tools_response = await self.session.list_tools()
            self.available_tools = {
                tool.name: tool for tool in tools_response.tools
            }
            
            # Load resources
            resources_response = await self.session.list_resources()
            self.available_resources = {
                resource.uri: resource for resource in resources_response.resources
            }
            
            logger.info(f"Loaded {len(self.available_tools)} tools and {len(self.available_resources)} resources")
            
        except Exception as e:
            logger.error(f"Failed to load capabilities: {e}")
    
    async def execute_query(self, query: str, max_iterations: int = 20) -> Dict[str, Any]:
        """
        Execute a natural language query using intelligent orchestration
        
        Args:
            query: Natural language query to execute
            max_iterations: Maximum number of orchestration iterations
            
        Returns:
            Execution result with final answer and details
        """
        if not self.connected:
            await self.connect()
        
        try:
            result = await self.session.call_tool(
                "execute_query",
                {
                    "query": query,
                    "max_iterations": max_iterations
                }
            )
            
            # Parse result
            if result.content and len(result.content) > 0:
                content = result.content[0].text
                return json.loads(content)
            else:
                return {"error": "No result content received"}
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {"error": str(e)}
    
    async def load_api_spec(self, api_spec: Dict[str, Any], api_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load an API specification into the orchestration system
        
        Args:
            api_spec: OpenAPI specification as dictionary
            api_name: Optional name for the API
            
        Returns:
            Loading result with tool count
        """
        if not self.connected:
            await self.connect()
        
        try:
            result = await self.session.call_tool(
                "load_api_spec",
                {
                    "api_spec": api_spec,
                    "api_name": api_name
                }
            )
            
            if result.content and len(result.content) > 0:
                content = result.content[0].text
                return json.loads(content)
            else:
                return {"error": "No result content received"}
                
        except Exception as e:
            logger.error(f"API spec loading failed: {e}")
            return {"error": str(e)}
    
    async def query_semantic_state(self, 
                                 query: str, 
                                 context_types: Optional[List[str]] = None,
                                 limit: int = 5) -> Dict[str, Any]:
        """
        Query the semantic state store for relevant information
        
        Args:
            query: Natural language query for semantic search
            context_types: Filter by context types
            limit: Maximum number of results
            
        Returns:
            Query results with relevant states
        """
        if not self.connected:
            await self.connect()
        
        try:
            arguments = {"query": query, "limit": limit}
            if context_types:
                arguments["context_types"] = context_types
            
            result = await self.session.call_tool(
                "query_semantic_state",
                arguments
            )
            
            if result.content and len(result.content) > 0:
                content = result.content[0].text
                return json.loads(content)
            else:
                return {"error": "No result content received"}
                
        except Exception as e:
            logger.error(f"Semantic state query failed: {e}")
            return {"error": str(e)}
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of an active orchestration execution
        
        Args:
            execution_id: Execution ID to check status for
            
        Returns:
            Execution status information
        """
        if not self.connected:
            await self.connect()
        
        try:
            result = await self.session.call_tool(
                "get_execution_status",
                {"execution_id": execution_id}
            )
            
            if result.content and len(result.content) > 0:
                content = result.content[0].text
                return json.loads(content)
            else:
                return {"error": "No result content received"}
                
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {"error": str(e)}
    
    async def list_available_tools(self) -> Dict[str, Any]:
        """
        List all available API tools loaded in the system
        
        Returns:
            Tool information and context
        """
        if not self.connected:
            await self.connect()
        
        try:
            result = await self.session.call_tool("list_available_tools", {})
            
            if result.content and len(result.content) > 0:
                content = result.content[0].text
                return json.loads(content)
            else:
                return {"error": "No result content received"}
                
        except Exception as e:
            logger.error(f"Tool listing failed: {e}")
            return {"error": str(e)}
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics and health information
        
        Returns:
            System statistics and health data
        """
        if not self.connected:
            await self.connect()
        
        try:
            result = await self.session.call_tool("get_system_stats", {})
            
            if result.content and len(result.content) > 0:
                content = result.content[0].text
                return json.loads(content)
            else:
                return {"error": "No result content received"}
                
        except Exception as e:
            logger.error(f"Stats retrieval failed: {e}")
            return {"error": str(e)}
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a resource from the MCP server
        
        Args:
            uri: Resource URI to read
            
        Returns:
            Resource content
        """
        if not self.connected:
            await self.connect()
        
        try:
            result = await self.session.read_resource(uri)
            
            if result.contents and len(result.contents) > 0:
                content = result.contents[0].text
                return json.loads(content)
            else:
                return {"error": "No resource content received"}
                
        except Exception as e:
            logger.error(f"Resource reading failed: {e}")
            return {"error": str(e)}
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.available_tools.keys())
    
    def get_available_resources(self) -> List[str]:
        """Get list of available resource URIs"""
        return list(self.available_resources.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the MCP connection"""
        try:
            if not self.connected:
                await self.connect()
            
            stats = await self.get_system_stats()
            
            return {
                "connected": self.connected,
                "tools_available": len(self.available_tools),
                "resources_available": len(self.available_resources),
                "system_stats": stats
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }


class MCPOrchestrationManager:
    """
    High-level manager for MCP-based orchestration
    Provides simplified interface for common operations
    """
    
    def __init__(self, server_command: Optional[List[str]] = None):
        self.client = IntelligentOrchestrationMCPClient(server_command)
    
    async def __aenter__(self):
        await self.client.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.disconnect()
    
    async def ask(self, question: str) -> str:
        """
        Ask a question and get an intelligent orchestrated answer
        
        Args:
            question: Natural language question
            
        Returns:
            Intelligent answer from orchestration
        """
        result = await self.client.execute_query(question)
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        return result.get("final_answer", "No answer provided")
    
    async def add_api(self, api_spec: Dict[str, Any], api_name: Optional[str] = None) -> bool:
        """
        Add a new API to the orchestration system
        
        Args:
            api_spec: OpenAPI specification
            api_name: Optional name for the API
            
        Returns:
            Success status
        """
        result = await self.client.load_api_spec(api_spec, api_name)
        return "error" not in result and result.get("success", False)
    
    async def remember(self, query: str, context_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Query the system's semantic memory
        
        Args:
            query: Natural language query for memory
            context_types: Filter by context types
            
        Returns:
            Relevant memories
        """
        result = await self.client.query_semantic_state(query, context_types)
        
        if "error" in result:
            return []
        
        return result.get("results", [])
    
    async def status(self) -> Dict[str, Any]:
        """Get system status and health"""
        return await self.client.health_check()


# Example usage and testing
async def main():
    """Test the MCP client"""
    
    async with MCPOrchestrationManager() as manager:
        # Test system status
        status = await manager.status()
        print(f"System Status: {status}")
        
        # Test loading an API spec
        sample_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Test endpoint",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        success = await manager.add_api(sample_spec, "test_api")
        print(f"API Loading Success: {success}")
        
        # Test asking a question
        answer = await manager.ask("What tools are available in the system?")
        print(f"Answer: {answer}")
        
        # Test memory query
        memories = await manager.remember("recent API calls")
        print(f"Memories: {len(memories)} found")


if __name__ == "__main__":
    asyncio.run(main())