"""
Adaptive Orchestration Engine - LLM-driven orchestration with semantic state
Implements ReAct pattern with continuous replanning and semantic context awareness
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
import uuid

from pydantic import BaseModel
import openai
from anthropic import AsyncAnthropic

from semantic_state_manager import SemanticStateManager
from tool_manager import ToolManager, ToolExecutionResult

logger = logging.getLogger(__name__)


class ExecutionStep(BaseModel):
    """Single execution step in the orchestration"""
    step_id: str
    iteration: int
    action: str
    tool_name: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    reasoning: str
    timestamp: datetime
    success: bool = True


class OrchestrationResult(BaseModel):
    """Final result of orchestration"""
    query: str
    success: bool
    final_answer: str
    execution_steps: List[ExecutionStep]
    total_iterations: int
    execution_time: float
    context_used: Dict[str, Any]


class AdaptiveOrchestrator:
    """
    LLM-driven orchestration with semantic state management
    Uses ReAct pattern with continuous replanning based on semantic context
    """
    
    def __init__(self,
                 llm_provider: str = "openai",  # "openai" or "anthropic"
                 model_name: Optional[str] = None,
                 semantic_state_manager: Optional[SemanticStateManager] = None,
                 tool_manager: Optional[ToolManager] = None,
                 max_iterations: int = 20):
        """
        Initialize adaptive orchestrator
        
        Args:
            llm_provider: LLM provider to use
            model_name: Specific model to use
            semantic_state_manager: Semantic state manager instance
            tool_manager: Tool manager instance
            max_iterations: Maximum iterations before stopping
        """
        self.llm_provider = llm_provider
        self.semantic_state = semantic_state_manager or SemanticStateManager()
        self.tool_manager = tool_manager or ToolManager(self.semantic_state)
        self.max_iterations = max_iterations
        
        # Initialize LLM client
        if llm_provider == "openai":
            self.model_name = model_name or "gpt-4"
            self.llm_client = openai.AsyncOpenAI()
        elif llm_provider == "anthropic":
            self.model_name = model_name or "claude-3-sonnet-20240229"
            self.llm_client = AsyncAnthropic()
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        # Execution tracking
        self.active_executions: Dict[str, List[ExecutionStep]] = {}
        
    async def execute_query(self, user_query: str, execution_id: Optional[str] = None) -> OrchestrationResult:
        """
        Execute user query using adaptive orchestration
        
        Args:
            user_query: Natural language query to execute
            execution_id: Optional execution ID for tracking
            
        Returns:
            Orchestration result with execution details
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        start_time = asyncio.get_event_loop().time()
        execution_steps = []
        
        try:
            logger.info(f"Starting orchestration for query: {user_query[:100]}...")
            
            # Initialize execution tracking
            self.active_executions[execution_id] = execution_steps
            
            iteration = 0
            final_answer = ""
            
            while iteration < self.max_iterations:
                logger.debug(f"Orchestration iteration {iteration}")
                
                # Get relevant context from semantic store
                context = await self.semantic_state.get_execution_context(
                    user_query, iteration
                )
                
                # LLM decides next action based on context
                next_action = await self._plan_next_step(
                    user_query=user_query,
                    context=context,
                    iteration=iteration,
                    execution_steps=execution_steps
                )
                
                # Create execution step
                step = ExecutionStep(
                    step_id=str(uuid.uuid4()),
                    iteration=iteration,
                    action=next_action["action"],
                    tool_name=next_action.get("tool_name"),
                    params=next_action.get("params"),
                    reasoning=next_action["reasoning"],
                    timestamp=datetime.utcnow()
                )
                
                execution_steps.append(step)
                
                # Check if we should complete
                if next_action["action"] == "complete":
                    final_answer = next_action.get("final_answer", "")
                    logger.info(f"Orchestration completed after {iteration} iterations")
                    break
                
                # Execute tool if specified
                if next_action.get("tool_name"):
                    result = await self._execute_tool_step(step, user_query)
                    step.result = result.data if result.success else {"error": result.error}
                    step.success = result.success
                    
                    # Store execution result semantically
                    await self.semantic_state.store_execution_step(
                        action=step.action,
                        tool_name=step.tool_name,
                        params=step.params or {},
                        result=step.result or {},
                        query_context=user_query,
                        iteration=iteration
                    )
                
                iteration += 1
            
            # Build final execution time
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Create result
            result = OrchestrationResult(
                query=user_query,
                success=True,
                final_answer=final_answer,
                execution_steps=execution_steps,
                total_iterations=iteration,
                execution_time=execution_time,
                context_used=context
            )
            
            # Store final result
            await self._store_final_result(result)
            
            return result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Orchestration failed: {e}")
            
            return OrchestrationResult(
                query=user_query,
                success=False,
                final_answer=f"Orchestration failed: {str(e)}",
                execution_steps=execution_steps,
                total_iterations=len(execution_steps),
                execution_time=execution_time,
                context_used={}
            )
        finally:
            # Clean up execution tracking
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def execute_with_streaming(self, 
                                   user_query: str,
                                   execution_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute query with streaming updates for real-time UI
        
        Args:
            user_query: Natural language query to execute
            execution_id: Optional execution ID for tracking
            
        Yields:
            Streaming updates for UI
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        try:
            # Send initial status
            yield {
                "type": "status",
                "execution_id": execution_id,
                "message": "Starting orchestration...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get initial context
            context = await self.semantic_state.get_execution_context(user_query, 0)
            
            yield {
                "type": "context_loaded",
                "execution_id": execution_id,
                "context_items": context.get("total_context_items", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            iteration = 0
            execution_steps = []
            
            while iteration < self.max_iterations:
                # Plan next step
                next_action = await self._plan_next_step(
                    user_query=user_query,
                    context=context,
                    iteration=iteration,
                    execution_steps=execution_steps
                )
                
                # Send planning update
                yield {
                    "type": "step_planned",
                    "execution_id": execution_id,
                    "iteration": iteration,
                    "action": next_action["action"],
                    "tool_name": next_action.get("tool_name"),
                    "reasoning": next_action["reasoning"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Check for completion
                if next_action["action"] == "complete":
                    yield {
                        "type": "completed",
                        "execution_id": execution_id,
                        "final_answer": next_action.get("final_answer", ""),
                        "total_iterations": iteration,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    break
                
                # Execute tool if needed
                if next_action.get("tool_name"):
                    yield {
                        "type": "tool_executing",
                        "execution_id": execution_id,
                        "tool_name": next_action["tool_name"],
                        "params": next_action.get("params"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    result = await self.tool_manager.execute_tool(
                        tool_name=next_action["tool_name"],
                        params=next_action.get("params", {}),
                        cache_key=f"{user_query}_{next_action['tool_name']}"
                    )
                    
                    yield {
                        "type": "tool_completed",
                        "execution_id": execution_id,
                        "tool_name": next_action["tool_name"],
                        "success": result.success,
                        "result": result.data if result.success else {"error": result.error},
                        "execution_time": result.execution_time,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Store execution step
                    await self.semantic_state.store_execution_step(
                        action=next_action["action"],
                        tool_name=next_action["tool_name"],
                        params=next_action.get("params", {}),
                        result=result.data if result.success else {"error": result.error},
                        query_context=user_query,
                        iteration=iteration
                    )
                
                iteration += 1
            
            # Send final status
            yield {
                "type": "final_status",
                "execution_id": execution_id,
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "execution_id": execution_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _plan_next_step(self,
                             user_query: str,
                             context: Dict[str, Any],
                             iteration: int,
                             execution_steps: List[ExecutionStep]) -> Dict[str, Any]:
        """
        Use LLM to plan the next step based on context and history
        
        Args:
            user_query: Original user query
            context: Semantic context from state manager
            iteration: Current iteration number
            execution_steps: Previous execution steps
            
        Returns:
            Next action to take
        """
        try:
            # Build context for LLM
            llm_context = self._build_llm_context(
                user_query, context, iteration, execution_steps
            )
            
            # Get LLM response
            if self.llm_provider == "openai":
                response = await self._get_openai_response(llm_context)
            else:
                response = await self._get_anthropic_response(llm_context)
            
            # Parse LLM response
            return self._parse_llm_response(response)
            
        except Exception as e:
            logger.error(f"Failed to plan next step: {e}")
            return {
                "action": "complete",
                "final_answer": f"Planning failed: {str(e)}",
                "reasoning": f"Error in planning step: {str(e)}"
            }
    
    def _build_llm_context(self,
                          user_query: str,
                          context: Dict[str, Any],
                          iteration: int,
                          execution_steps: List[ExecutionStep]) -> str:
        """Build comprehensive context for LLM decision making"""
        
        context_str = f"""You are an intelligent API orchestration assistant. Your job is to help users accomplish their goals by using available API tools.

USER QUERY: {user_query}

CURRENT ITERATION: {iteration}

AVAILABLE TOOLS:
{self.tool_manager.get_tool_context()}

RELEVANT CONTEXT FROM PAST INTERACTIONS:
"""
        
        # Add past execution context
        if context.get("past_executions"):
            context_str += "\nPast Executions:\n"
            for execution in context["past_executions"][:3]:
                context_str += f"- {execution['description']} (Score: {execution['score']:.3f})\n"
        
        # Add API results context
        if context.get("api_results"):
            context_str += "\nRelevant API Results:\n"
            for result in context["api_results"][:3]:
                context_str += f"- {result['description']} (Score: {result['score']:.3f})\n"
        
        # Add memory context
        if context.get("memory_context"):
            context_str += "\nRelevant Memory:\n"
            for memory in context["memory_context"][:2]:
                context_str += f"- {memory['description']} (Score: {memory['score']:.3f})\n"
        
        # Add current execution steps
        if execution_steps:
            context_str += "\nCURRENT EXECUTION STEPS:\n"
            for step in execution_steps[-3:]:  # Last 3 steps
                context_str += f"Iteration {step.iteration}: {step.action}"
                if step.tool_name:
                    context_str += f" using {step.tool_name}"
                if step.success:
                    context_str += " ✓"
                else:
                    context_str += " ✗"
                context_str += f"\nReasoning: {step.reasoning}\n"
        
        context_str += """

INSTRUCTIONS:
1. Analyze the user query and available context
2. Decide on the next action to take
3. If you need to use a tool, specify the exact tool name and parameters
4. If you have enough information to answer, provide a complete final answer
5. Always explain your reasoning

RESPONSE FORMAT (JSON):
{
    "action": "use_tool" | "complete",
    "reasoning": "Your reasoning for this decision",
    "tool_name": "tool_name_if_using_tool",
    "params": {"param1": "value1"} if using tool,
    "final_answer": "Complete answer if action is complete"
}
"""
        
        return context_str
    
    async def _get_openai_response(self, context: str) -> str:
        """Get response from OpenAI"""
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an intelligent API orchestration assistant."},
                    {"role": "user", "content": context}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _get_anthropic_response(self, context: str) -> str:
        """Get response from Anthropic"""
        try:
            response = await self.llm_client.messages.create(
                model=self.model_name,
                max_tokens=1000,
                temperature=0.1,
                messages=[{"role": "user", "content": context}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured action"""
        try:
            # Try to parse as JSON
            parsed = json.loads(response.strip())
            
            # Validate required fields
            if "action" not in parsed or "reasoning" not in parsed:
                raise ValueError("Missing required fields in LLM response")
            
            return parsed
            
        except json.JSONDecodeError:
            # Fallback parsing for non-JSON responses
            logger.warning("LLM response not in JSON format, using fallback parsing")
            
            if "complete" in response.lower() or "answer" in response.lower():
                return {
                    "action": "complete",
                    "final_answer": response,
                    "reasoning": "LLM indicated completion"
                }
            else:
                return {
                    "action": "complete",
                    "final_answer": f"Unable to parse LLM response: {response}",
                    "reasoning": "Failed to parse LLM response"
                }
    
    async def _execute_tool_step(self, 
                                step: ExecutionStep, 
                                user_query: str) -> ToolExecutionResult:
        """Execute a tool step"""
        try:
            if not step.tool_name or not step.params:
                raise ValueError("Tool name and parameters required for execution")
            
            return await self.tool_manager.execute_tool(
                tool_name=step.tool_name,
                params=step.params,
                cache_key=f"{user_query}_{step.tool_name}_{step.iteration}"
            )
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolExecutionResult(
                success=False,
                error=str(e),
                execution_time=0.0,
                tool_name=step.tool_name or "unknown",
                endpoint="unknown"
            )
    
    async def _store_final_result(self, result: OrchestrationResult) -> None:
        """Store final orchestration result in semantic state"""
        try:
            await self.semantic_state.store_state(
                state_description=f"Completed orchestration for: {result.query}",
                data={
                    "query": result.query,
                    "success": result.success,
                    "final_answer": result.final_answer,
                    "total_iterations": result.total_iterations,
                    "execution_time": result.execution_time,
                    "steps_count": len(result.execution_steps)
                },
                context_type="orchestration_result",
                metadata={
                    "total_iterations": result.total_iterations,
                    "execution_time": result.execution_time,
                    "success": result.success
                }
            )
        except Exception as e:
            logger.error(f"Failed to store final result: {e}")
    
    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active execution"""
        if execution_id in self.active_executions:
            steps = self.active_executions[execution_id]
            return {
                "execution_id": execution_id,
                "active": True,
                "steps_completed": len(steps),
                "current_iteration": steps[-1].iteration if steps else 0,
                "last_action": steps[-1].action if steps else None
            }
        return None


# Example usage and testing
async def main():
    """Test the adaptive orchestrator"""
    
    # Initialize components
    semantic_state = SemanticStateManager()
    tool_manager = ToolManager(semantic_state)
    orchestrator = AdaptiveOrchestrator(
        semantic_state_manager=semantic_state,
        tool_manager=tool_manager
    )
    
    # Test query
    test_query = "What is the current balance of my account?"
    
    print(f"Executing query: {test_query}")
    
    # Execute with streaming
    async for update in orchestrator.execute_with_streaming(test_query):
        print(f"Update: {update['type']} - {update.get('message', update.get('action', ''))}")


if __name__ == "__main__":
    asyncio.run(main())