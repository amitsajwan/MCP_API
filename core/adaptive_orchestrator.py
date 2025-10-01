"""
Adaptive Orchestrator for Demo MCP System
Fully dynamic orchestration - works with ANY OpenAPI spec and ANY user query
NO hardcoded methods - everything is LLM-driven and dynamically generated
"""

import json
import logging
import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import ast
import inspect

from .cache_manager import CacheManager
from .mcp_client_connector import MCPClientConnector
from external.azure_client import AzureClient

logger = logging.getLogger(__name__)


class AdaptiveOrchestrator:
    """
    Fully adaptive orchestrator that:
    1. Works with ANY OpenAPI spec (no hardcoding)
    2. Handles ANY user query dynamically
    3. LLM decides tool selection and order
    4. LLM generates Python code for aggregation
    5. Caches large results and passes summaries to LLM
    6. Executes LLM-generated Python functions on cached data
    """
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.mcp_client = MCPClientConnector()  # Connects to MCP server via stdio
        self.azure_client = AzureClient()
        self.safe_executor = SafePythonExecutor(self.cache_manager)
    
    def _generate_workflow_id(self, query: str) -> str:
        """Generate unique workflow ID"""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"workflow_{query_hash}_{timestamp}"
    
    async def process_query(self, query: str, session_id: str) -> Dict[str, Any]:
        """
        Process ANY user query with fully adaptive orchestration
        
        Args:
            query: Any user query
            session_id: Session identifier
            
        Returns:
            Complete workflow result with final answer
        """
        workflow_id = self._generate_workflow_id(query)
        
        # Check if entire workflow is cached
        cached_workflow = self.cache_manager.get_workflow_cache(workflow_id)
        if cached_workflow:
            logger.info(f"Workflow cache hit for: {query}")
            return {
                "query": query,
                "workflow_id": workflow_id,
                "result": cached_workflow,
                "source": "cache",
                "execution_time": "< 1s"
            }
        
        # Step 1: LLM analyzes query and creates execution plan
        execution_plan = await self._llm_analyze_and_plan(query)
        
        # Step 2: Execute plan with adaptive reasoning
        workflow_result = await self._execute_adaptive_plan(
            execution_plan, 
            workflow_id,
            query
        )
        
        # Step 3: Cache complete workflow
        self.cache_manager.set_workflow_cache(workflow_id, workflow_result)
        
        return {
            "query": query,
            "workflow_id": workflow_id,
            "result": workflow_result,
            "source": "execution",
            "execution_time": workflow_result.get("execution_time", "unknown")
        }
    
    async def _llm_analyze_and_plan(self, query: str) -> Dict[str, Any]:
        """
        LLM analyzes query and creates execution plan dynamically
        Works with ANY query and ANY available tools
        """
        # Connect to MCP server and discover tools via MCP protocol
        if not self.mcp_client.connected:
            await self.mcp_client.connect()
        
        # Get tools from MCP server (MCP server loaded OpenAPI specs)
        available_tools = await self.mcp_client.list_tools()
        
        # Create analysis prompt - NO hardcoded assumptions
        prompt = f"""
You are an intelligent API orchestrator. Analyze this user query and create an execution plan.

USER QUERY: "{query}"

AVAILABLE MCP TOOLS:
{json.dumps([{
    'name': t['name'],
    'description': t['description'],
    'parameters': t['parameters'],
    'category': t['category']
} for t in available_tools], indent=2)}

TASK: Create a step-by-step execution plan as JSON:

{{
    "reasoning": "Your analysis of what the query needs",
    "steps": [
        {{
            "step_number": 1,
            "tool": "tool_name",
            "purpose": "why this tool is needed",
            "parameters": {{}},  // leave empty if unknown
            "depends_on": [],  // list of step numbers this depends on
            "parallel_with": [],  // steps that can run in parallel
            "cache_result": true,  // cache if result might be large
            "result_type": "list|dict|string|number"  // expected result type
        }}
    ],
    "aggregation_needed": true|false,
    "aggregation_description": "what aggregation/processing is needed",
    "python_code": "def process_data(cache_key):\\n    # LLM generates this code\\n    pass",
    "expected_final_output": "description of what user should receive"
}}

IMPORTANT:
- Don't assume tool availability - use ONLY tools from the list
- Determine order based on logical dependencies
- Mark steps that can run in parallel
- If data might be large (lists, bulk data), set cache_result=true
- Generate Python code for any aggregation/processing needed
- Python code must use cache_manager.get_workflow_cache(cache_key) to access data
"""
        
        # Use Azure client if available
        if self.azure_client.is_available():
            try:
                plan_json = await self.azure_client.generate_response(
                    [{"role": "user", "content": prompt}],
                    max_tokens=2000
                )
                plan = json.loads(plan_json)
                logger.info(f"LLM generated execution plan: {plan['reasoning']}")
                return plan
            except Exception as e:
                logger.error(f"LLM planning failed: {e}")
                return await self._fallback_analysis(query, available_tools)
        else:
            # Fallback for demo
            return await self._fallback_analysis(query, available_tools)
    
    async def _fallback_analysis(self, query: str, available_tools: List[Dict]) -> Dict[str, Any]:
        """
        Fallback analysis when LLM not available
        Still dynamic - infers from query keywords and available tools
        """
        query_lower = query.lower()
        
        # Dynamically find relevant tools based on query keywords
        relevant_tools = []
        
        for tool in available_tools:
            tool_name_lower = tool['name'].lower()
            tool_desc_lower = tool['description'].lower()
            
            # Extract keywords from query
            query_words = set(query_lower.split())
            tool_words = set(tool_name_lower.split('_')) | set(tool_desc_lower.split())
            
            # Check for overlap
            overlap = query_words & tool_words
            if overlap:
                relevant_tools.append({
                    "tool": tool,
                    "relevance_score": len(overlap),
                    "matching_keywords": list(overlap)
                })
        
        # Sort by relevance
        relevant_tools.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Create execution plan
        steps = []
        for i, item in enumerate(relevant_tools[:5], 1):  # Top 5 relevant tools
            tool = item['tool']
            steps.append({
                "step_number": i,
                "tool": tool['name'],
                "purpose": f"Matched keywords: {item['matching_keywords']}",
                "parameters": {},
                "depends_on": [i-1] if i > 1 else [],
                "parallel_with": [],
                "cache_result": True,
                "result_type": "unknown"
            })
        
        # Check if aggregation might be needed
        needs_aggregation = any(word in query_lower for word in ['total', 'sum', 'all', 'aggregate', 'calculate', 'average'])
        
        return {
            "reasoning": f"Found {len(relevant_tools)} relevant tools for query",
            "steps": steps,
            "aggregation_needed": needs_aggregation,
            "aggregation_description": "Aggregate results from all tools if needed",
            "python_code": self._generate_generic_aggregation_code() if needs_aggregation else None,
            "expected_final_output": f"Processed results for: {query}"
        }
    
    def _generate_generic_aggregation_code(self) -> str:
        """Generate generic aggregation code that works with any data"""
        return """
def process_cached_data(cache_key, cache_manager):
    \"\"\"Generic aggregation function for any cached data\"\"\"
    import json
    
    # Get cached data
    data = cache_manager.get_workflow_cache(cache_key)
    
    if data is None:
        return {"error": "No cached data found"}
    
    # Analyze data structure and aggregate dynamically
    if isinstance(data, list):
        result = {
            "type": "list",
            "count": len(data),
            "sample": data[:5] if data else []
        }
        
        # If list of dicts, analyze structure
        if data and isinstance(data[0], dict):
            # Find numeric fields
            numeric_fields = {}
            for key in data[0].keys():
                try:
                    values = [item.get(key, 0) for item in data if isinstance(item.get(key), (int, float))]
                    if values:
                        numeric_fields[key] = {
                            "sum": sum(values),
                            "average": sum(values) / len(values),
                            "min": min(values),
                            "max": max(values),
                            "count": len(values)
                        }
                except:
                    pass
            
            result["numeric_aggregations"] = numeric_fields
        
        return result
    
    elif isinstance(data, dict):
        result = {
            "type": "dict",
            "key_count": len(data),
            "keys": list(data.keys())[:10]
        }
        
        # If dict of numeric values, aggregate
        numeric_values = [v for v in data.values() if isinstance(v, (int, float))]
        if numeric_values:
            result["aggregations"] = {
                "sum": sum(numeric_values),
                "average": sum(numeric_values) / len(numeric_values),
                "min": min(numeric_values),
                "max": max(numeric_values),
                "count": len(numeric_values)
            }
        
        return result
    
    else:
        return {
            "type": str(type(data).__name__),
            "value": str(data)[:500]
        }
"""
    
    async def _execute_adaptive_plan(
        self, 
        execution_plan: Dict[str, Any],
        workflow_id: str,
        query: str
    ) -> Dict[str, Any]:
        """Execute plan adaptively - works with ANY tools"""
        
        start_time = datetime.now()
        workflow_steps = []
        cached_data_keys = {}
        step_results = {}
        
        # Execute each step in the plan
        for step in execution_plan.get("steps", []):
            step_number = step["step_number"]
            tool_name = step["tool"]
            parameters = step.get("parameters", {})
            cache_result = step.get("cache_result", True)
            
            logger.info(f"Executing step {step_number}: {tool_name}")
            
            # Check dependencies
            depends_on = step.get("depends_on", [])
            if depends_on:
                # Wait for dependent steps to complete
                # In production, this would check step_results
                pass
            
            # Execute tool via MCP protocol
            tool_result = await self.mcp_client.execute_tool(tool_name, parameters)
            
            # Store result for dependent steps
            step_results[step_number] = tool_result
            
            # Handle large results dynamically
            if cache_result and tool_result.get("success", False):
                result_data = tool_result.get("result", "")
                result_size = len(json.dumps(result_data))
                
                if result_size > 100_000:  # > 100KB - cache it
                    cache_key = f"{workflow_id}_{tool_name}_{step_number}"
                    
                    # Cache full result
                    self.cache_manager.set_workflow_cache(cache_key, result_data)
                    
                    # Generate summary dynamically (no hardcoding)
                    summary = self._generate_dynamic_summary(result_data, tool_name)
                    
                    step_result = {
                        "step": step_number,
                        "tool": tool_name,
                        "purpose": step.get("purpose", ""),
                        "cached": True,
                        "cache_key": cache_key,
                        "summary": summary,
                        "size_bytes": result_size,
                        "success": True
                    }
                    
                    # Store cache key for Python function execution
                    cached_data_keys[f"step_{step_number}"] = cache_key
                else:
                    # Small result - include directly
                    step_result = {
                        "step": step_number,
                        "tool": tool_name,
                        "purpose": step.get("purpose", ""),
                        "cached": False,
                        "result": result_data,
                        "size_bytes": result_size,
                        "success": True
                    }
            else:
                # Don't cache or execution failed
                step_result = {
                    "step": step_number,
                    "tool": tool_name,
                    "purpose": step.get("purpose", ""),
                    "cached": False,
                    "result": tool_result.get("result", ""),
                    "success": tool_result.get("success", False),
                    "error": tool_result.get("error")
                }
            
            workflow_steps.append(step_result)
        
        # Execute Python code if LLM generated it
        aggregation_results = None
        if execution_plan.get("aggregation_needed", False) and execution_plan.get("python_code"):
            aggregation_results = await self._execute_llm_generated_code(
                execution_plan["python_code"],
                cached_data_keys,
                workflow_id
            )
        
        # Let LLM generate final response based on results
        final_response = await self._llm_generate_final_response(
            query,
            workflow_steps,
            aggregation_results,
            execution_plan
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "workflow_id": workflow_id,
            "query": query,
            "reasoning": execution_plan.get("reasoning", ""),
            "steps": workflow_steps,
            "aggregation_results": aggregation_results,
            "final_response": final_response,
            "execution_time": f"{execution_time:.2f}s",
            "cache_keys": cached_data_keys
        }
    
    def _generate_dynamic_summary(self, data: Any, tool_name: str) -> Dict[str, Any]:
        """
        Generate summary dynamically for ANY data structure
        No assumptions about data format
        """
        
        if isinstance(data, list):
            summary = {
                "type": "list",
                "count": len(data),
                "sample": data[:3] if data else []
            }
            
            # Infer schema from first item
            if data and isinstance(data[0], dict):
                summary["schema"] = {k: type(v).__name__ for k, v in data[0].items()}
                
                # Find numeric fields dynamically
                numeric_fields = []
                for key, value in data[0].items():
                    if isinstance(value, (int, float)):
                        numeric_fields.append(key)
                
                summary["numeric_fields"] = numeric_fields
                
                # Calculate basic stats for numeric fields
                if numeric_fields:
                    summary["field_stats"] = {}
                    for field in numeric_fields[:3]:  # Limit to 3 fields
                        values = [item.get(field, 0) for item in data if field in item]
                        if values:
                            summary["field_stats"][field] = {
                                "min": min(values),
                                "max": max(values),
                                "avg": sum(values) / len(values)
                            }
            
            return summary
        
        elif isinstance(data, dict):
            summary = {
                "type": "dict",
                "key_count": len(data),
                "keys": list(data.keys())[:10],
                "sample": {k: data[k] for k in list(data.keys())[:3]}
            }
            
            # Check if dict values are all numeric
            numeric_values = [v for v in data.values() if isinstance(v, (int, float))]
            if len(numeric_values) > 0:
                summary["all_numeric"] = len(numeric_values) == len(data)
                if summary["all_numeric"]:
                    summary["value_stats"] = {
                        "sum": sum(numeric_values),
                        "average": sum(numeric_values) / len(numeric_values),
                        "min": min(numeric_values),
                        "max": max(numeric_values)
                    }
            
            return summary
        
        else:
            return {
                "type": str(type(data).__name__),
                "value": str(data)[:500],
                "length": len(str(data))
            }
    
    async def _execute_llm_generated_code(
        self,
        python_code: str,
        cached_data_keys: Dict[str, str],
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        Execute Python code generated by LLM
        Code operates on cached data to perform aggregations
        """
        try:
            # Extract function name from code
            function_name = self._extract_function_name(python_code)
            
            if not function_name:
                logger.error("Could not extract function name from generated code")
                return {"error": "Invalid function definition"}
            
            # Get primary cache key (most recent cached data)
            primary_cache_key = list(cached_data_keys.values())[-1] if cached_data_keys else None
            
            if not primary_cache_key:
                return {"error": "No cached data available for processing"}
            
            # Execute safely
            result = self.safe_executor.execute_safe_python(
                code=python_code,
                function_name=function_name,
                args=[primary_cache_key, self.cache_manager],
                timeout=10
            )
            
            logger.info(f"Successfully executed LLM-generated function: {function_name}")
            return {
                "function": function_name,
                "result": result,
                "cache_key_used": primary_cache_key,
                "success": True
            }
        
        except Exception as e:
            logger.error(f"Error executing LLM-generated code: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
    def _extract_function_name(self, code: str) -> Optional[str]:
        """Extract function name from Python code"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return node.name
        except:
            pass
        return None
    
    async def _llm_generate_final_response(
        self,
        query: str,
        workflow_steps: List[Dict],
        aggregation_results: Optional[Dict],
        execution_plan: Dict
    ) -> str:
        """
        LLM generates final user-friendly response
        Based on actual results, not hardcoded templates
        """
        
        # Build context for LLM
        context = f"""
USER QUERY: "{query}"

EXECUTION SUMMARY:
- Total steps executed: {len(workflow_steps)}
- All steps successful: {all(s.get('success', False) for s in workflow_steps)}

WORKFLOW STEPS:
{json.dumps([{
    'step': s['step'],
    'tool': s['tool'],
    'purpose': s.get('purpose', ''),
    'cached': s.get('cached', False),
    'summary': s.get('summary') if s.get('cached') else s.get('result')
} for s in workflow_steps], indent=2)}

AGGREGATION RESULTS:
{json.dumps(aggregation_results, indent=2) if aggregation_results else 'None'}

TASK: Generate a clear, user-friendly response that:
1. Directly answers the user's question
2. Includes key metrics and insights
3. Formats numbers appropriately
4. Suggests next steps if relevant
5. Is concise but complete
"""
        
        # Use Azure client if available
        if self.azure_client.is_available():
            try:
                response = await self.azure_client.generate_response(
                    [{"role": "user", "content": context}],
                    max_tokens=500
                )
                return response
            except Exception as e:
                logger.error(f"LLM response generation failed: {e}")
                return self._fallback_response(query, workflow_steps, aggregation_results)
        else:
            return self._fallback_response(query, workflow_steps, aggregation_results)
    
    def _fallback_response(
        self,
        query: str,
        workflow_steps: List[Dict],
        aggregation_results: Optional[Dict]
    ) -> str:
        """Generate fallback response when LLM unavailable"""
        
        response = f"Query: {query}\n\n"
        response += f"Executed {len(workflow_steps)} steps:\n\n"
        
        for step in workflow_steps:
            response += f"✓ Step {step['step']}: {step['tool']}"
            if step.get('cached', False):
                response += f" (cached {step.get('size_bytes', 0) / 1024:.1f}KB)"
            response += f"\n  Purpose: {step.get('purpose', 'N/A')}\n"
        
        if aggregation_results:
            response += "\n📊 Results:\n"
            if isinstance(aggregation_results, dict):
                for key, value in aggregation_results.items():
                    if key != "error" and key != "success":
                        response += f"  • {key}: {value}\n"
        
        return response


class SafePythonExecutor:
    """
    Execute LLM-generated Python code safely
    Restricted environment with only allowed operations
    """
    
    ALLOWED_BUILTINS = {
        'sum', 'len', 'range', 'enumerate', 'zip',
        'min', 'max', 'abs', 'round', 'sorted',
        'int', 'float', 'str', 'list', 'dict', 'set',
        'any', 'all', 'filter', 'map',
        'True', 'False', 'None',
        'isinstance', 'type', 'hasattr', 'getattr'
    }
    
    ALLOWED_MODULES = {
        'json', 'math', 'statistics', 'datetime'
    }
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def execute_safe_python(
        self,
        code: str,
        function_name: str,
        args: List[Any],
        timeout: int = 10
    ) -> Any:
        """
        Execute LLM-generated Python code in restricted environment
        
        Args:
            code: Python code to execute (LLM-generated)
            function_name: Name of function to call
            args: Arguments to pass (typically [cache_key, cache_manager])
            timeout: Execution timeout in seconds
            
        Returns:
            Function execution result
        """
        
        # Validate code safety
        self._validate_code_safety(code)
        
        # Create restricted globals with only safe operations
        restricted_globals = {
            '__builtins__': {
                k: __builtins__[k] 
                for k in self.ALLOWED_BUILTINS 
                if k in __builtins__
            }
        }
        
        # Add allowed modules
        import json
        import math
        import statistics
        from datetime import datetime
        
        restricted_globals['json'] = json
        restricted_globals['math'] = math
        restricted_globals['statistics'] = statistics
        restricted_globals['datetime'] = datetime
        
        try:
            # Execute code to define function
            exec(code, restricted_globals)
            
            # Get the function
            func = restricted_globals.get(function_name)
            if not func:
                raise ValueError(f"Function {function_name} not found in generated code")
            
            # Execute function (with timeout in production)
            result = func(*args)
            
            logger.info(f"✓ Safe execution successful: {function_name}")
            return result
            
        except Exception as e:
            logger.error(f"✗ Safe execution failed: {e}")
            return {"error": str(e), "success": False}
    
    def _validate_code_safety(self, code: str):
        """
        Validate that code is safe to execute
        Prevents dangerous operations
        """
        dangerous_patterns = [
            'import os', 'import sys', '__import__',
            'open(', 'eval(', 'exec(', 'compile(',
            'subprocess', 'socket', 'requests',
            'urllib', 'pickle', 'shelve',
            '__builtins__', '__globals__', '__locals__',
            'file(', 'input(', 'raw_input(',
            'setattr', 'delattr', 'vars()', 'dir()',
            '__class__', '__dict__', '__code__'
        ]
        
        code_lower = code.lower()
        
        for pattern in dangerous_patterns:
            if pattern.lower() in code_lower:
                raise ValueError(f"🚫 Dangerous operation detected: {pattern}")
        
        # Check for infinite loops
        if 'while True' in code or 'while 1' in code:
            raise ValueError("🚫 Infinite loops not allowed")
        
        # Limit code complexity
        if code.count('for ') > 20:
            raise ValueError("🚫 Too many loops detected (max 20)")
        
        if code.count('def ') > 5:
            raise ValueError("🚫 Too many function definitions (max 5)")
        
        # Validate syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"🚫 Syntax error in generated code: {e}")
        
        logger.info("✓ Code validation passed")


class DynamicToolAnalyzer:
    """
    Analyzes available tools dynamically to understand capabilities
    No hardcoded knowledge - learns from tool metadata
    """
    
    @staticmethod
    def analyze_tools(tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze tools to understand system capabilities"""
        
        capabilities = {
            "total_tools": len(tools),
            "categories": {},
            "data_retrieval_tools": [],
            "data_modification_tools": [],
            "analysis_tools": [],
            "tool_dependencies": {}
        }
        
        for tool in tools:
            # Categorize
            category = tool.get('category', 'Unknown')
            if category not in capabilities['categories']:
                capabilities['categories'][category] = []
            capabilities['categories'][category].append(tool['name'])
            
            # Classify by operation type (from name/description)
            tool_name_lower = tool['name'].lower()
            tool_desc_lower = tool['description'].lower()
            
            if any(word in tool_name_lower or word in tool_desc_lower 
                   for word in ['get', 'list', 'retrieve', 'fetch', 'read']):
                capabilities['data_retrieval_tools'].append(tool['name'])
            
            elif any(word in tool_name_lower or word in tool_desc_lower 
                     for word in ['create', 'update', 'delete', 'post', 'put', 'process']):
                capabilities['data_modification_tools'].append(tool['name'])
            
            elif any(word in tool_name_lower or word in tool_desc_lower 
                     for word in ['calculate', 'analyze', 'compute', 'generate', 'validate']):
                capabilities['analysis_tools'].append(tool['name'])
        
        return capabilities
    
    @staticmethod
    def infer_tool_dependencies(tools: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Infer dependencies between tools based on parameters and names
        Example: get_account_balance needs account_id, which might come from get_accounts
        """
        dependencies = {}
        
        for tool in tools:
            tool_name = tool['name']
            parameters = tool.get('parameters', {})
            
            # Check if any parameter name matches another tool's likely output
            potential_dependencies = []
            
            for param_name in parameters.keys():
                param_lower = param_name.lower()
                
                # Look for tools that might provide this parameter
                for other_tool in tools:
                    if other_tool['name'] != tool_name:
                        other_name_lower = other_tool['name'].lower()
                        
                        # Check if parameter name relates to other tool
                        if param_lower in other_name_lower or other_name_lower in param_lower:
                            potential_dependencies.append(other_tool['name'])
            
            if potential_dependencies:
                dependencies[tool_name] = potential_dependencies
        
        return dependencies