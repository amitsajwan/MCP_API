#!/usr/bin/env python3
"""
Tool Orchestrator - Adaptive Tool Execution Management
====================================================
Handles the execution of multiple tools using adaptive strategy.
Intelligently executes tools based on dependencies and availability.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class ToolExecutor(ABC):
    """Abstract base class for tool execution"""
    
    @abstractmethod
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool with given arguments"""
        pass

class ToolResult:
    """Represents the result of a tool execution"""
    
    def __init__(self, tool_call_id: str, tool_name: str, args: Dict[str, Any], 
                 result: Any = None, error: str = None, success: bool = True, execution_time: float = 0.0):
        self.tool_call_id = tool_call_id
        self.tool_name = tool_name
        self.args = args
        self.result = result
        self.error = error
        self.success = success
        self.execution_time = execution_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "args": self.args,
            "result": self.result,
            "error": self.error,
            "success": self.success,
            "execution_time": self.execution_time
        }

class ToolOrchestrator:
    """Orchestrates the execution of multiple tools using adaptive strategy"""
    
    def __init__(self, tool_executor: ToolExecutor, max_concurrent_tools: int = 5):
        self.tool_executor = tool_executor
        self.max_concurrent_tools = max_concurrent_tools
        self.execution_history: List[ToolResult] = []
        
    async def execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """
        Execute multiple tool calls using adaptive strategy
        
        Args:
            tool_calls: List of tool call dictionaries from LLM
        
        Returns:
            List of ToolResult objects
        """
        logger.info(f"🔧 [ORCHESTRATOR] Executing {len(tool_calls)} tool calls with adaptive strategy")
        return await self._execute_adaptive(tool_calls)
    
    
    async def _execute_adaptive(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """Execute tools with adaptive strategy based on dependencies"""
        results = []
        remaining_calls = tool_calls.copy()
        
        while remaining_calls:
            # Find tools that can be executed (no dependencies on remaining tools)
            executable_calls = self._find_executable_tools(remaining_calls, results)
            
            if not executable_calls:
                logger.warning("❌ [ORCHESTRATOR] No executable tools found, executing remaining sequentially")
                # Fallback to sequential execution for remaining tools
                for tool_call in remaining_calls:
                    result = await self._execute_single_tool(tool_call)
                    results.append(result)
                    self.execution_history.append(result)
                break
            
            # Execute executable tools in parallel
            logger.info(f"🔧 [ORCHESTRATOR] Executing {len(executable_calls)} tools in parallel")
            parallel_results = await self._execute_parallel_batch(executable_calls)
            results.extend(parallel_results)
            
            # Remove executed tools from remaining
            for tool_call in executable_calls:
                remaining_calls.remove(tool_call)
        
        return results
    
    async def _execute_parallel_batch(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """Execute a batch of tools in parallel with concurrency limit"""
        # Create semaphore to limit concurrent executions
        semaphore = asyncio.Semaphore(self.max_concurrent_tools)
        
        async def execute_with_semaphore(tool_call):
            async with semaphore:
                return await self._execute_single_tool(tool_call)
        
        # Execute all tools concurrently
        tasks = [execute_with_semaphore(tool_call) for tool_call in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results and add to history
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tool_call = tool_calls[i]
                failed_result = ToolResult(
                    tool_call_id=tool_call.get("id", f"call_{i}"),
                    tool_name=tool_call.get("function", {}).get("name", "unknown"),
                    args=json.loads(tool_call.get("function", {}).get("arguments", "{}")),
                    error=str(result),
                    success=False
                )
                processed_results.append(failed_result)
                self.execution_history.append(failed_result)
            else:
                processed_results.append(result)
                self.execution_history.append(result)
        
        return processed_results
    
    async def _execute_single_tool(self, tool_call: Dict[str, Any]) -> ToolResult:
        """Execute a single tool call"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            tool_name = tool_call.get("function", {}).get("name", "unknown")
            args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
            tool_call_id = tool_call.get("id", "unknown")
            
            logger.info(f"🔧 [ORCHESTRATOR] Executing tool: {tool_name} with args: {args}")
            
            # Execute the tool
            result = await self.tool_executor.execute_tool(tool_name, args)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return ToolResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                args=args,
                result=result,
                success=True,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"❌ [ORCHESTRATOR] Tool execution failed: {e}")
            
            return ToolResult(
                tool_call_id=tool_call.get("id", "unknown"),
                tool_name=tool_call.get("function", {}).get("name", "unknown"),
                args=json.loads(tool_call.get("function", {}).get("arguments", "{}")),
                error=str(e),
                success=False,
                execution_time=execution_time
            )
    
    def _is_critical_tool(self, tool_call: Dict[str, Any]) -> bool:
        """Determine if a tool is critical and execution should stop on failure"""
        tool_name = tool_call.get("function", {}).get("name", "").lower()
        
        # Define critical tool patterns
        critical_patterns = ["login", "authenticate", "setup", "initialize"]
        return any(pattern in tool_name for pattern in critical_patterns)
    
    def _find_executable_tools(self, tool_calls: List[Dict[str, Any]], 
                              completed_results: List[ToolResult]) -> List[Dict[str, Any]]:
        """Find tools that can be executed based on dependencies"""
        # For now, return all tools (no dependency analysis)
        # This can be enhanced with actual dependency analysis
        return tool_calls
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of tool execution history"""
        if not self.execution_history:
            return {"total_tools": 0, "success_rate": 0.0, "average_time": 0.0}
        
        total_tools = len(self.execution_history)
        successful_tools = len([r for r in self.execution_history if r.success])
        success_rate = successful_tools / total_tools
        average_time = sum(r.execution_time for r in self.execution_history) / total_tools
        
        return {
            "total_tools": total_tools,
            "successful_tools": successful_tools,
            "failed_tools": total_tools - successful_tools,
            "success_rate": success_rate,
            "average_execution_time": average_time,
            "total_execution_time": sum(r.execution_time for r in self.execution_history)
        }
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history.clear()
        logger.info("🧹 [ORCHESTRATOR] Execution history cleared")