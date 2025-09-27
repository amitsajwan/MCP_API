"""
MCP Server Implementation - Model Context Protocol Server
Provides tool registration, execution, and semantic state management via MCP
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    CallToolRequest, ListToolsRequest, ListResourcesRequest,
    ReadResourceRequest, ToolResult, ResourceResult
)

from semantic_state_manager import SemanticStateManager
from tool_manager import ToolManager

logger = logging.getLogger(__name__)


class IntelligentOrchestrationMCPServer:
    """
    MCP Server for Intelligent API Orchestration System
    Provides tools and resources via Model Context Protocol
    """
    
    def __init__(self):
        self.server = Server("intelligent-orchestration")
        self.semantic_state = SemanticStateManager()
        self.tool_manager = ToolManager(self.semantic_state)
        
        # Register MCP handlers
        self._register_handlers()
        
        # Active executions tracking
        self.active_executions: Dict[str, Dict[str, Any]] = {}
    
    def _register_handlers(self):
        """Register MCP protocol handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available orchestration tools"""
            return [
                Tool(
                    name="execute_query",
                    description="Execute a natural language query using intelligent API orchestration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query to execute"
                            },
                            "max_iterations": {
                                "type": "integer",
                                "description": "Maximum number of orchestration iterations",
                                "default": 20
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="load_api_spec",
                    description="Load a new API specification into the orchestration system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "api_spec": {
                                "type": "object",
                                "description": "OpenAPI specification as JSON object"
                            },
                            "api_name": {
                                "type": "string",
                                "description": "Name for the API (optional)"
                            }
                        },
                        "required": ["api_spec"]
                    }
                ),
                Tool(
                    name="query_semantic_state",
                    description="Query the semantic state store for relevant information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query for semantic search"
                            },
                            "context_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by context types (execution_result, api_result, memory, etc.)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_execution_status",
                    description="Get status of an active orchestration execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "execution_id": {
                                "type": "string",
                                "description": "Execution ID to check status for"
                            }
                        },
                        "required": ["execution_id"]
                    }
                ),
                Tool(
                    name="list_available_tools",
                    description="List all available API tools loaded in the system",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_system_stats",
                    description="Get comprehensive system statistics and health information",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool execution requests"""
            try:
                if name == "execute_query":
                    return await self._handle_execute_query(arguments)
                elif name == "load_api_spec":
                    return await self._handle_load_api_spec(arguments)
                elif name == "query_semantic_state":
                    return await self._handle_query_semantic_state(arguments)
                elif name == "get_execution_status":
                    return await self._handle_get_execution_status(arguments)
                elif name == "list_available_tools":
                    return await self._handle_list_available_tools(arguments)
                elif name == "get_system_stats":
                    return await self._handle_get_system_stats(arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
                    
            except Exception as e:
                logger.error(f"Tool execution failed for {name}: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error executing {name}: {str(e)}"
                )]
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="orchestration://executions",
                    name="Active Executions",
                    description="List of currently active orchestration executions",
                    mimeType="application/json"
                ),
                Resource(
                    uri="orchestration://tools",
                    name="Available Tools",
                    description="List of all available API tools",
                    mimeType="application/json"
                ),
                Resource(
                    uri="orchestration://semantic-state",
                    name="Semantic State",
                    description="Semantic state store information",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource content"""
            if uri == "orchestration://executions":
                return json.dumps({
                    "active_executions": len(self.active_executions),
                    "executions": list(self.active_executions.keys())
                })
            elif uri == "orchestration://tools":
                tools = self.tool_manager.get_tool_names()
                return json.dumps({
                    "total_tools": len(tools),
                    "tools": tools,
                    "context": self.tool_manager.get_tool_context()
                })
            elif uri == "orchestration://semantic-state":
                stats = await self.semantic_state.get_stats()
                return json.dumps(stats)
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def _handle_execute_query(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle query execution"""
        query = arguments.get("query", "")
        max_iterations = arguments.get("max_iterations", 20)
        
        if not query:
            return [TextContent(
                type="text",
                text="Error: Query is required"
            )]
        
        execution_id = str(uuid.uuid4())
        
        # Import orchestrator here to avoid circular imports
        from adaptive_orchestrator import AdaptiveOrchestrator
        
        orchestrator = AdaptiveOrchestrator(
            semantic_state_manager=self.semantic_state,
            tool_manager=self.tool_manager,
            max_iterations=max_iterations
        )
        
        # Track execution
        self.active_executions[execution_id] = {
            "query": query,
            "start_time": datetime.utcnow(),
            "status": "running"
        }
        
        try:
            # Execute query
            result = await orchestrator.execute_query(
                user_query=query,
                execution_id=execution_id
            )
            
            # Update execution status
            self.active_executions[execution_id].update({
                "status": "completed" if result.success else "failed",
                "end_time": datetime.utcnow(),
                "result": result.final_answer,
                "iterations": result.total_iterations,
                "execution_time": result.execution_time
            })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "execution_id": execution_id,
                    "success": result.success,
                    "final_answer": result.final_answer,
                    "total_iterations": result.total_iterations,
                    "execution_time": result.execution_time,
                    "execution_steps": [
                        {
                            "iteration": step.iteration,
                            "action": step.action,
                            "tool_name": step.tool_name,
                            "success": step.success,
                            "reasoning": step.reasoning
                        }
                        for step in result.execution_steps
                    ]
                }, indent=2)
            )]
            
        except Exception as e:
            self.active_executions[execution_id].update({
                "status": "error",
                "error": str(e)
            })
            raise
    
    async def _handle_load_api_spec(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle API specification loading"""
        api_spec = arguments.get("api_spec")
        api_name = arguments.get("api_name")
        
        if not api_spec:
            return [TextContent(
                type="text",
                text="Error: API specification is required"
            )]
        
        try:
            tools_loaded = await self.tool_manager.load_api_spec(api_spec, api_name)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "tools_loaded": tools_loaded,
                    "api_name": api_name or "unknown",
                    "message": f"Successfully loaded {tools_loaded} tools"
                })
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e),
                    "message": "Failed to load API specification"
                })
            )]
    
    async def _handle_query_semantic_state(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle semantic state queries"""
        query = arguments.get("query", "")
        context_types = arguments.get("context_types")
        limit = arguments.get("limit", 5)
        
        if not query:
            return [TextContent(
                type="text",
                text="Error: Query is required"
            )]
        
        try:
            results = await self.semantic_state.query_relevant_state(
                query=query,
                context_types=context_types,
                limit=limit
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "query": query,
                    "results_count": len(results),
                    "results": results
                }, indent=2)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error querying semantic state: {str(e)}"
            )]
    
    async def _handle_get_execution_status(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle execution status requests"""
        execution_id = arguments.get("execution_id", "")
        
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
            return [TextContent(
                type="text",
                text=json.dumps(execution, indent=2, default=str)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Execution {execution_id} not found"
            )]
    
    async def _handle_list_available_tools(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle listing available tools"""
        try:
            tool_names = self.tool_manager.get_tool_names()
            tool_context = self.tool_manager.get_tool_context()
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "total_tools": len(tool_names),
                    "tool_names": tool_names,
                    "context": tool_context
                }, indent=2)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error listing tools: {str(e)}"
            )]
    
    async def _handle_get_system_stats(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle system statistics requests"""
        try:
            semantic_stats = await self.semantic_state.get_stats()
            tool_health = await self.tool_manager.health_check()
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "semantic_state": semantic_stats,
                    "tools": tool_health,
                    "active_executions": len(self.active_executions),
                    "timestamp": datetime.utcnow().isoformat()
                }, indent=2)
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting system stats: {str(e)}"
            )]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="intelligent-orchestration",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None
                    )
                )
            )


async def main():
    """Main entry point for MCP server"""
    server = IntelligentOrchestrationMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())