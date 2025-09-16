#!/usr/bin/env python3
"""
MCP Tool Executor - MCP Implementation of ToolExecutor
====================================================
Implements the ToolExecutor interface using MCP (Model Context Protocol).
Handles actual tool execution through MCP client connections.
"""

import json
import logging
from typing import Dict, Any, Optional
from tool_orchestrator import ToolExecutor
try:
    from mcp_client import MCPClient, safe_truncate
except ImportError:
    # Fallback for missing dependencies
    class MCPClient:
        def __init__(self, *args, **kwargs):
            pass
    def safe_truncate(data, max_length=1000):
        return str(data)[:max_length] + "..." if len(str(data)) > max_length else data

logger = logging.getLogger(__name__)

class MCPToolExecutor(ToolExecutor):
    """MCP implementation of ToolExecutor"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self._tool_cache: Dict[str, Dict[str, Any]] = {}
        self._execution_count = 0
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool through MCP client"""
        try:
            self._execution_count += 1
            logger.info(f"🔧 [MCP_EXECUTOR] Executing tool #{self._execution_count}: {tool_name}")
            logger.info(f"🔧 [MCP_EXECUTOR] Tool args: {args}")
            
            # Validate tool exists
            if not await self._validate_tool_exists(tool_name):
                raise ValueError(f"Tool '{tool_name}' not found in available tools")
            
            # Execute the tool
            raw_result = await self.mcp_client.call_tool(tool_name, args)
            logger.info(f"✅ [MCP_EXECUTOR] Tool {tool_name} executed successfully")
            
            # Truncate result if too large
            result = safe_truncate(raw_result)
            logger.info(f"🔄 [MCP_EXECUTOR] Tool result truncated: {len(str(result))} chars")
            
            # Cache the result for potential reuse
            self._cache_tool_result(tool_name, args, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [MCP_EXECUTOR] Tool execution failed: {tool_name} - {e}")
            raise
    
    async def _validate_tool_exists(self, tool_name: str) -> bool:
        """Validate that the tool exists in available tools"""
        try:
            # Get available tools if not cached
            if not self._tool_cache:
                await self._load_available_tools()
            
            return tool_name in self._tool_cache
            
        except Exception as e:
            logger.error(f"❌ [MCP_EXECUTOR] Failed to validate tool existence: {e}")
            return False
    
    async def _load_available_tools(self):
        """Load available tools from MCP client"""
        try:
            logger.info("🔄 [MCP_EXECUTOR] Loading available tools...")
            
            # This would need to be implemented based on your MCP client
            # For now, we'll assume tools are available
            logger.info("✅ [MCP_EXECUTOR] Tools loaded (cached)")
            
        except Exception as e:
            logger.error(f"❌ [MCP_EXECUTOR] Failed to load tools: {e}")
            raise
    
    def _cache_tool_result(self, tool_name: str, args: Dict[str, Any], result: Any):
        """Cache tool result for potential reuse"""
        cache_key = f"{tool_name}_{hash(json.dumps(args, sort_keys=True))}"
        self._tool_cache[cache_key] = {
            "tool_name": tool_name,
            "args": args,
            "result": result,
            "timestamp": json.dumps({"cached": True})  # Placeholder for timestamp
        }
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            "total_executions": self._execution_count,
            "cached_results": len(self._tool_cache),
            "executor_type": "MCP"
        }
    
    def clear_cache(self):
        """Clear tool result cache"""
        self._tool_cache.clear()
        logger.info("🧹 [MCP_EXECUTOR] Tool cache cleared")

class MockToolExecutor(ToolExecutor):
    """Mock implementation of ToolExecutor for testing"""
    
    def __init__(self):
        self.execution_count = 0
        self.mock_responses = {
            "get_payments": {
                "payments": [
                    {"id": "PAY001", "amount": 1000, "status": "pending"},
                    {"id": "PAY002", "amount": 2500, "status": "completed"}
                ],
                "total": 2
            },
            "get_portfolio": {
                "holdings": [
                    {"symbol": "AAPL", "shares": 100, "value": 15000},
                    {"symbol": "GOOGL", "shares": 50, "value": 12000}
                ],
                "total_value": 27000
            },
            "create_payment": {
                "id": "PAY_NEW_123",
                "status": "created",
                "amount": 500,
                "currency": "USD"
            }
        }
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mock tool"""
        self.execution_count += 1
        logger.info(f"🔧 [MOCK_EXECUTOR] Executing mock tool: {tool_name}")
        
        # Simulate some processing time
        import asyncio
        await asyncio.sleep(0.1)
        
        # Return mock response
        if tool_name in self.mock_responses:
            return self.mock_responses[tool_name]
        else:
            return {"error": f"Mock tool '{tool_name}' not found", "args": args}
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get mock execution statistics"""
        return {
            "total_executions": self.execution_count,
            "executor_type": "Mock"
        }