#!/usr/bin/env python3
"""
Enhanced MCP Client - POC Implementation
Integrates all advanced features:
- Enhanced schema processing with external $ref, allOf/oneOf/anyOf
- Context-aware response generation like modern AI chat systems  
- Parallel tool execution and dependency management
- Comprehensive business intelligence and insights
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import requests
from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Import our enhanced components
from enhanced_schema_processor import EnhancedSchemaProcessor, SchemaContext, ValidationResult
from context_aware_response_generator import (
    ContextAwareResponseGenerator, ContextualResponse, DataInsight, Recommendation
)

logger = logging.getLogger(__name__)

@dataclass
class ToolCall:
    """Represents a tool call to be executed."""
    tool_name: str
    arguments: Dict[str, Any]
    reason: Optional[str] = None
    dependencies: List[str] = None
    priority: int = 1  # 1 = highest priority
    parallel_group: Optional[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class ToolResult:
    """Represents the result of a tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict representation of the result."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp
        }

@dataclass
class ExecutionPlan:
    """Represents a complete execution plan with dependencies."""
    tool_calls: List[ToolCall]
    execution_order: List[List[str]]  # Groups of tools that can run in parallel
    estimated_time: float
    complexity_score: float
    
class EnhancedMCPClient:
    """Enhanced MCP Client with advanced capabilities."""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8000", 
                 openai_model: str = "gpt-4"):
        self.server_url = mcp_server_url
        self.available_tools: Dict[str, Dict[str, Any]] = {}
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}
        self.session = requests.Session()
        
        # Enhanced components
        self.schema_processor = None
        self.response_generator = ContextAwareResponseGenerator()
        
        # OpenAI client
        self.openai_client = None
        self.model = openai_model
        
        # Execution tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {
            "total_executions": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0,
            "cache_hit_rate": 0.0
        }
        
        # Configuration
        self.max_parallel_tools = 3
        self.max_tool_executions = 10
        self.tool_timeout = 30.0
        
        logger.info(f"🚀 Enhanced MCP Client initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.schema_processor = EnhancedSchemaProcessor()
        await self.schema_processor.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.schema_processor:
            await self.schema_processor.__aexit__(exc_type, exc_val, exc_tb)
        if self.session:
            self.session.close()
    
    def _create_openai_client(self) -> AsyncAzureOpenAI:
        """Create Azure OpenAI client with azure_ad_token_provider."""
        try:
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            if not azure_endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
            
            # Create Azure AD token provider
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            
            client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                azure_ad_token_provider=token_provider,
                api_version="2024-02-01"
            )
            logger.info("✅ Azure OpenAI client created with Azure AD authentication")
            return client
        except Exception as e:
            logger.error(f"Failed to create Azure OpenAI client: {e}")
            raise e
    
    async def connect(self) -> bool:
        """Connect to MCP server and initialize tools."""
        try:
            response = self.session.get(f"{self.server_url}/health")
            if response.status_code == 200:
                logger.info(f"✅ Connected to Enhanced MCP server at {self.server_url}")
                
                # Load tools and schemas
                await self._load_tools_and_schemas()
                return True
            else:
                raise Exception(f"Server health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MCP server: {e}")
            return False
    
    async def _load_tools_and_schemas(self):
        """Load available tools and process their schemas."""
        try:
            response = self.session.get(f"{self.server_url}/tools")
            if response.status_code == 200:
                data = response.json()
                tools = data.get("tools", [])
                
                logger.info(f"📋 Loading {len(tools)} tools with enhanced schema processing...")
                
                for tool_data in tools:
                    tool_name = tool_data["name"]
                    description = tool_data["description"]
                    input_schema = tool_data.get("inputSchema", {"type": "object"})
                    
                    # Store basic tool info
                    self.available_tools[tool_name] = {
                        "name": tool_name,
                        "description": description,
                        "inputSchema": input_schema
                    }
                    
                    # Process schema with enhanced processor
                    if self.schema_processor:
                        try:
                            context = SchemaContext(base_url=self.server_url)
                            resolved_schema = await self.schema_processor.resolve_schema(input_schema, context)
                            self.tool_schemas[tool_name] = resolved_schema
                            logger.debug(f"✅ Enhanced schema processed for {tool_name}")
                        except Exception as e:
                            logger.warning(f"⚠️ Schema processing failed for {tool_name}: {e}")
                            self.tool_schemas[tool_name] = input_schema
                
                logger.info(f"✅ Loaded {len(self.available_tools)} tools with enhanced schemas")
            else:
                raise Exception(f"Failed to load tools: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error loading tools: {e}")
            raise
    
    async def enhanced_query_processing(self, user_query: str) -> ContextualResponse:
        """
        Enhanced end-to-end query processing with all advanced features.
        
        Args:
            user_query: The user's question/request
            
        Returns:
            ContextualResponse with comprehensive analysis and insights
        """
        logger.info(f"🎯 Processing enhanced query: {user_query}")
        
        start_time = time.time()
        
        try:
            # Ensure connection and OpenAI client
            if not await self.connect():
                raise Exception("Failed to connect to MCP server")
            
            if not self.openai_client:
                self.openai_client = self._create_openai_client()
            
            # Step 1: Intelligent tool planning with dependency analysis
            execution_plan = await self._create_intelligent_execution_plan(user_query)
            
            if not execution_plan.tool_calls:
                return ContextualResponse(
                    direct_answer="No suitable tools found for this request.",
                    insights=[],
                    recommendations=[],
                    business_context="Unable to process request with available tools.",
                    follow_up_questions=["Could you rephrase your question?", "What specific information are you looking for?"],
                    warnings=["Request could not be mapped to available tools"],
                    data_sources=[],
                    confidence_score=0.0
                )
            
            # Step 2: Enhanced argument validation and extraction
            validated_plan = await self._validate_and_enhance_arguments(user_query, execution_plan)
            
            # Step 3: Parallel execution with dependency management
            tool_results = await self._execute_parallel_plan(validated_plan)
            
            # Step 4: Generate comprehensive contextual response
            response = await self.response_generator.generate_response(
                user_query=user_query,
                tool_results=[result.to_dict() for result in tool_results],
                schemas=self.tool_schemas,
                openai_client=self.openai_client
            )
            
            # Step 5: Update performance metrics
            execution_time = time.time() - start_time
            self._update_performance_metrics(tool_results, execution_time)
            
            logger.info(f"✅ Enhanced query processed in {execution_time:.2f}s with {response.confidence_score:.1%} confidence")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Enhanced query processing failed: {e}")
            
            # Return error response in consistent format
            return ContextualResponse(
                direct_answer=f"I encountered an error while processing your request: {str(e)}",
                insights=[],
                recommendations=[Recommendation(
                    action="Try rephrasing your question or check system status",
                    reason="System encountered an unexpected error",
                    priority="medium",
                    timeline="immediate",
                    impact="Unable to fulfill current request"
                )],
                business_context="System error occurred during processing",
                follow_up_questions=["Would you like to try a different question?", "Should I check system health?"],
                warnings=[f"Error: {str(e)}"],
                data_sources=[],
                confidence_score=0.0
            )
    
    async def _create_intelligent_execution_plan(self, user_query: str) -> ExecutionPlan:
        """Create an intelligent execution plan with dependency analysis."""
        
        # Build enhanced tools description
        tools_description = self._build_enhanced_tools_description()
        
        # Create advanced system prompt for planning
        system_prompt = f"""You are an expert financial API orchestrator that creates optimal execution plans.

Available Tools:
{tools_description}

User Query: "{user_query}"

Analyze the user's request and create a comprehensive execution plan. Consider:
1. Which tools provide the needed data
2. Dependencies between tools (which results feed into others)
3. What can run in parallel vs sequentially  
4. Priority and urgency of different data
5. Optimal execution order for performance

Respond with a JSON object:
{{
  "reasoning": "Detailed explanation of your planning logic",
  "tool_calls": [
    {{
      "tool_name": "exact_tool_name",
      "arguments": {{"param1": "value1"}},
      "reason": "why this tool is needed",
      "dependencies": ["tool_name_that_must_run_first"],
      "priority": 1,
      "parallel_group": "group_name_for_parallel_execution"
    }}
  ],
  "execution_strategy": "parallel|sequential|hybrid",
  "estimated_complexity": "low|medium|high"
}}

Guidelines:
- Use exact tool names from the available list
- Set dependencies only when tool B needs results from tool A
- Group independent tools in same parallel_group
- Priority 1 = highest, 5 = lowest
- Maximum {self.max_tool_executions} tools allowed
- Extract parameters from user query when possible"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You create optimal API execution plans. Output only valid JSON."},
                    {"role": "user", "content": system_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            logger.info(f"🧠 Planning response: {content[:200]}...")
            
            # Parse JSON response
            if '```json' in content:
                content = content.split('```json', 1)[1].split('```', 1)[0].strip()
            elif '```' in content:
                content = content.split('```', 1)[1].strip()
            
            plan_data = json.loads(content)
            
            # Convert to ToolCall objects
            tool_calls = []
            for call_data in plan_data.get("tool_calls", []):
                tool_name = call_data.get("tool_name")
                
                # Validate tool exists
                if tool_name in self.available_tools:
                    tool_call = ToolCall(
                        tool_name=tool_name,
                        arguments=call_data.get("arguments", {}),
                        reason=call_data.get("reason", ""),
                        dependencies=call_data.get("dependencies", []),
                        priority=call_data.get("priority", 1),
                        parallel_group=call_data.get("parallel_group")
                    )
                    tool_calls.append(tool_call)
                else:
                    logger.warning(f"❌ Unknown tool in plan: {tool_name}")
            
            # Calculate execution order
            execution_order = self._calculate_execution_order(tool_calls)
            
            # Estimate complexity and time
            complexity_score = len(tool_calls) / self.max_tool_executions
            estimated_time = len(execution_order) * 2.0  # Rough estimate
            
            plan = ExecutionPlan(
                tool_calls=tool_calls,
                execution_order=execution_order,
                estimated_time=estimated_time,
                complexity_score=complexity_score
            )
            
            logger.info(f"📋 Created execution plan: {len(tool_calls)} tools, {len(execution_order)} execution groups")
            
            return plan
            
        except Exception as e:
            logger.error(f"❌ Planning failed: {e}")
            # Fallback to simple planning
            return self._create_fallback_plan(user_query)
    
    def _build_enhanced_tools_description(self) -> str:
        """Build enhanced description of available tools with schema info."""
        descriptions = []
        
        for tool_name, tool_info in self.available_tools.items():
            desc_parts = [f"🔧 {tool_name}"]
            desc_parts.append(f"   Description: {tool_info['description']}")
            
            # Add schema information
            schema = self.tool_schemas.get(tool_name, {})
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            if properties:
                desc_parts.append("   Parameters:")
                for prop_name, prop_info in list(properties.items())[:3]:  # Limit for brevity
                    prop_type = prop_info.get('type', 'any')
                    prop_desc = prop_info.get('description', '')
                    is_required = prop_name in required
                    req_indicator = "*" if is_required else ""
                    desc_parts.append(f"     - {prop_name}{req_indicator}: {prop_type} - {prop_desc}")
                
                if len(properties) > 3:
                    desc_parts.append(f"     ... and {len(properties) - 3} more parameters")
            
            descriptions.append("\n".join(desc_parts))
        
        return "\n\n".join(descriptions)
    
    def _calculate_execution_order(self, tool_calls: List[ToolCall]) -> List[List[str]]:
        """Calculate optimal execution order considering dependencies and parallelization."""
        
        # Build dependency graph
        dependency_graph = {}
        tool_map = {tc.tool_name: tc for tc in tool_calls}
        
        for tool_call in tool_calls:
            dependency_graph[tool_call.tool_name] = tool_call.dependencies.copy()
        
        # Topological sort with parallel grouping
        execution_order = []
        remaining_tools = set(tc.tool_name for tc in tool_calls)
        
        while remaining_tools:
            # Find tools with no unresolved dependencies
            ready_tools = []
            for tool_name in remaining_tools:
                dependencies = dependency_graph[tool_name]
                if not any(dep in remaining_tools for dep in dependencies):
                    ready_tools.append(tool_name)
            
            if not ready_tools:
                # Circular dependency - break it
                logger.warning("⚠️ Circular dependency detected, breaking...")
                ready_tools = [list(remaining_tools)[0]]
            
            # Group by parallel_group and priority
            parallel_groups = {}
            for tool_name in ready_tools:
                tool_call = tool_map[tool_name]
                group_key = tool_call.parallel_group or f"priority_{tool_call.priority}"
                
                if group_key not in parallel_groups:
                    parallel_groups[group_key] = []
                parallel_groups[group_key].append(tool_name)
            
            # Sort groups by priority and add to execution order
            sorted_groups = sorted(
                parallel_groups.items(),
                key=lambda x: tool_map[x[1][0]].priority
            )
            
            for group_key, tools_in_group in sorted_groups:
                # Limit parallel execution
                if len(tools_in_group) > self.max_parallel_tools:
                    # Split into smaller groups
                    for i in range(0, len(tools_in_group), self.max_parallel_tools):
                        batch = tools_in_group[i:i + self.max_parallel_tools]
                        execution_order.append(batch)
                else:
                    execution_order.append(tools_in_group)
            
            # Remove processed tools
            remaining_tools -= set(ready_tools)
        
        logger.debug(f"📊 Execution order: {execution_order}")
        return execution_order
    
    def _create_fallback_plan(self, user_query: str) -> ExecutionPlan:
        """Create a simple fallback plan when intelligent planning fails."""
        logger.info("🔄 Creating fallback execution plan...")
        
        # Simple keyword matching
        query_lower = user_query.lower()
        relevant_tools = []
        
        for tool_name, tool_info in self.available_tools.items():
            description = tool_info['description'].lower()
            
            # Simple keyword matching
            if any(keyword in description for keyword in ['payment', 'account', 'balance']) and \
               any(keyword in query_lower for keyword in ['payment', 'account', 'balance', 'show', 'get']):
                relevant_tools.append(tool_name)
        
        # Limit to reasonable number
        relevant_tools = relevant_tools[:3]
        
        if not relevant_tools:
            # Use first few tools as last resort
            relevant_tools = list(self.available_tools.keys())[:2]
        
        tool_calls = [
            ToolCall(
                tool_name=tool_name,
                arguments={},
                reason=f"Fallback selection for query: {user_query}",
                priority=i + 1
            )
            for i, tool_name in enumerate(relevant_tools)
        ]
        
        return ExecutionPlan(
            tool_calls=tool_calls,
            execution_order=[[tc.tool_name] for tc in tool_calls],  # Sequential
            estimated_time=len(tool_calls) * 3.0,
            complexity_score=0.3
        )
    
    async def _validate_and_enhance_arguments(self, user_query: str, plan: ExecutionPlan) -> ExecutionPlan:
        """Validate and enhance tool arguments using schema processor."""
        enhanced_calls = []
        
        for tool_call in plan.tool_calls:
            try:
                # Get enhanced schema
                schema = self.tool_schemas.get(tool_call.tool_name, {})
                
                # Extract arguments from query using LLM if needed
                if not tool_call.arguments:
                    tool_call.arguments = await self._llm_extract_arguments(
                        user_query, tool_call.tool_name, schema
                    )
                
                # Validate arguments against schema
                if self.schema_processor:
                    validation_result = await self.schema_processor.validate_data(
                        tool_call.arguments, schema
                    )
                    
                    if validation_result.valid:
                        # Use cleaned data
                        tool_call.arguments = validation_result.cleaned_data
                        enhanced_calls.append(tool_call)
                        logger.debug(f"✅ Validated arguments for {tool_call.tool_name}")
                    else:
                        logger.warning(f"⚠️ Validation failed for {tool_call.tool_name}: {validation_result.errors}")
                        # Try with empty arguments for optional parameters
                        tool_call.arguments = {}
                        enhanced_calls.append(tool_call)
                else:
                    enhanced_calls.append(tool_call)
                    
            except Exception as e:
                logger.error(f"❌ Argument processing failed for {tool_call.tool_name}: {e}")
                # Include with empty arguments
                tool_call.arguments = {}
                enhanced_calls.append(tool_call)
        
        plan.tool_calls = enhanced_calls
        return plan
    
    async def _llm_extract_arguments(self, user_query: str, tool_name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract arguments for a tool using LLM based on schema."""
        tool_info = self.available_tools.get(tool_name, {})
        description = tool_info.get('description', '')
        
        prompt = f"""Extract the best arguments for this API tool from the user query.

Tool: {tool_name}
Description: {description}
Schema: {json.dumps(schema, indent=2)}

User Query: "{user_query}"

Extract any relevant parameters from the query. If a parameter isn't mentioned, omit it.
Return only a JSON object with the arguments.

Example for a payment query:
{{"status": "pending", "amount_min": 100}}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract API parameters from user queries. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean up response
            if content.startswith('```json'):
                content = content[7:-3].strip()
            elif content.startswith('```'):
                content = content[3:-3].strip()
            
            try:
                arguments = json.loads(content)
                return arguments if isinstance(arguments, dict) else {}
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Failed to parse LLM arguments for {tool_name}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ LLM argument extraction failed for {tool_name}: {e}")
            return {}
    
    async def _execute_parallel_plan(self, plan: ExecutionPlan) -> List[ToolResult]:
        """Execute the plan with parallel execution and dependency management."""
        results = []
        result_map = {}  # tool_name -> result
        
        logger.info(f"🚀 Executing plan: {len(plan.execution_order)} execution groups")
        
        for group_index, tool_group in enumerate(plan.execution_order):
            logger.info(f"📊 Executing group {group_index + 1}/{len(plan.execution_order)}: {tool_group}")
            
            # Create tasks for parallel execution
            tasks = []
            for tool_name in tool_group:
                tool_call = next(tc for tc in plan.tool_calls if tc.tool_name == tool_name)
                task = self._execute_single_tool(tool_call, result_map)
                tasks.append(task)
            
            # Execute tools in parallel
            if len(tasks) == 1:
                # Single tool - no need for gather
                group_results = [await tasks[0]]
            else:
                # Multiple tools - execute in parallel
                group_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(group_results):
                tool_name = tool_group[i]
                
                if isinstance(result, Exception):
                    logger.error(f"❌ Tool {tool_name} failed with exception: {result}")
                    tool_result = ToolResult(
                        tool_name=tool_name,
                        success=False,
                        result=None,
                        error=str(result)
                    )
                else:
                    tool_result = result
                
                results.append(tool_result)
                result_map[tool_name] = tool_result
                
                # Log result
                if tool_result.success:
                    logger.info(f"✅ {tool_name} completed in {tool_result.execution_time:.2f}s")
                else:
                    logger.warning(f"❌ {tool_name} failed: {tool_result.error}")
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"📈 Execution complete: {success_count}/{len(results)} tools successful")
        
        return results
    
    async def _execute_single_tool(self, tool_call: ToolCall, result_map: Dict[str, ToolResult]) -> ToolResult:
        """Execute a single tool with proper error handling and timing."""
        start_time = time.time()
        
        try:
            # Check dependencies
            for dep_tool in tool_call.dependencies:
                if dep_tool not in result_map:
                    raise Exception(f"Dependency {dep_tool} not satisfied")
                if not result_map[dep_tool].success:
                    raise Exception(f"Dependency {dep_tool} failed")
            
            # Enhance arguments with dependency results if needed
            enhanced_args = self._enhance_arguments_with_dependencies(
                tool_call.arguments, tool_call.dependencies, result_map
            )
            
            # Make the API call
            payload = {"name": tool_call.tool_name, "arguments": enhanced_args}
            
            # Add timeout
            response = self.session.post(
                f"{self.server_url}/call_tool", 
                json=payload,
                timeout=self.tool_timeout
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                result_data = response.json()
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    success=True,
                    result=result_data,
                    execution_time=execution_time
                )
            else:
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    success=False,
                    result=None,
                    error=f"HTTP {response.status_code}: {response.text}",
                    execution_time=execution_time
                )
        
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time
            )
    
    def _enhance_arguments_with_dependencies(self, base_args: Dict[str, Any], 
                                           dependencies: List[str], 
                                           result_map: Dict[str, ToolResult]) -> Dict[str, Any]:
        """Enhance arguments with results from dependency tools."""
        enhanced_args = base_args.copy()
        
        # For POC, implement simple result passing
        # In a full implementation, this would be more sophisticated
        for dep_tool in dependencies:
            if dep_tool in result_map and result_map[dep_tool].success:
                dep_result = result_map[dep_tool].result
                
                # Simple strategy: if dependency returned an ID, use it
                if isinstance(dep_result, dict):
                    if 'id' in dep_result and 'id' not in enhanced_args:
                        enhanced_args['id'] = dep_result['id']
                    if 'accountNumber' in dep_result and 'account' not in enhanced_args:
                        enhanced_args['account'] = dep_result['accountNumber']
        
        return enhanced_args
    
    def _update_performance_metrics(self, tool_results: List[ToolResult], execution_time: float):
        """Update performance metrics based on execution results."""
        self.performance_metrics["total_executions"] += 1
        
        successful_tools = sum(1 for r in tool_results if r.success)
        total_tools = len(tool_results)
        
        # Update success rate (rolling average)
        current_success_rate = successful_tools / total_tools if total_tools > 0 else 0
        prev_rate = self.performance_metrics["success_rate"]
        total_executions = self.performance_metrics["total_executions"]
        
        self.performance_metrics["success_rate"] = (
            (prev_rate * (total_executions - 1) + current_success_rate) / total_executions
        )
        
        # Update average execution time
        prev_time = self.performance_metrics["avg_execution_time"]
        self.performance_metrics["avg_execution_time"] = (
            (prev_time * (total_executions - 1) + execution_time) / total_executions
        )
        
        logger.debug(f"📊 Performance: {self.performance_metrics['success_rate']:.1%} success, "
                    f"{self.performance_metrics['avg_execution_time']:.2f}s avg time")


# Usage example and demonstration
async def main():
    """Demonstrate the enhanced MCP client capabilities."""
    
    print("🚀 Enhanced MCP Client POC Demonstration")
    print("=" * 60)
    
    # Test queries demonstrating different capabilities
    test_queries = [
        "Show me my pending payments and account balances",
        "What's the status of my recent transactions?",
        "I need to transfer money from savings to checking for upcoming bills",
        "Are there any failed payments I should know about?"
    ]
    
    async with EnhancedMCPClient() as client:
        print(f"🔗 Enhanced MCP Client initialized")
        print(f"🎯 Testing {len(test_queries)} different query types")
        print()
        
        for i, query in enumerate(test_queries, 1):
            print(f"📝 Test {i}/{len(test_queries)}: {query}")
            print("-" * 40)
            
            try:
                # Process query with all enhancements
                response = await client.enhanced_query_processing(query)
                
                # Display results
                print(f"💬 Direct Answer:")
                print(f"   {response.direct_answer}")
                print()
                
                if response.insights:
                    print(f"💡 Key Insights ({len(response.insights)}):")
                    for insight in response.insights[:2]:  # Show top 2
                        urgency_emoji = "🔴" if insight.urgency == "high" else "🟡" if insight.urgency == "medium" else "🟢"
                        print(f"   {urgency_emoji} {insight.message} ({insight.confidence:.0%} confidence)")
                    print()
                
                if response.recommendations:
                    print(f"🎯 Recommendations ({len(response.recommendations)}):")
                    for rec in response.recommendations[:2]:  # Show top 2
                        priority_emoji = "🚨" if rec.priority == "critical" else "⚠️" if rec.priority == "high" else "💡"
                        print(f"   {priority_emoji} {rec.action}")
                        print(f"      Timeline: {rec.timeline} | Impact: {rec.impact}")
                    print()
                
                if response.warnings:
                    print(f"⚠️ Warnings:")
                    for warning in response.warnings:
                        print(f"   • {warning}")
                    print()
                
                print(f"📊 Response Confidence: {response.confidence_score:.0%}")
                print(f"📋 Data Sources: {len(response.data_sources)} tools")
                
                # Show follow-up questions
                if response.follow_up_questions:
                    print(f"❓ Follow-up suggestions:")
                    for question in response.follow_up_questions[:2]:
                        print(f"   • {question}")
                
                print()
                print("=" * 60)
                print()
                
            except Exception as e:
                print(f"❌ Error processing query: {e}")
                print()
        
        # Show performance metrics
        print("📈 Performance Summary:")
        metrics = client.performance_metrics
        print(f"   Total Executions: {metrics['total_executions']}")
        print(f"   Success Rate: {metrics['success_rate']:.1%}")
        print(f"   Avg Execution Time: {metrics['avg_execution_time']:.2f}s")
        print()
        
        print("🎉 Enhanced MCP Client POC demonstration complete!")
        print()
        print("🔥 Key Features Demonstrated:")
        print("   ✅ External $ref resolution and allOf/oneOf/anyOf schema support")
        print("   ✅ Context-aware response generation like modern AI chat systems")
        print("   ✅ Parallel tool execution with dependency management")
        print("   ✅ Comprehensive business intelligence and insights")
        print("   ✅ Actionable recommendations and follow-up questions")
        print("   ✅ Performance monitoring and optimization")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())
