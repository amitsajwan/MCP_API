"""
FastMCP Tool Manager - Dynamic API tool management with automatic OpenAPI conversion
Handles tool discovery, validation, and execution with semantic caching
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import yaml

import httpx
from fastmcp import FastMCP, RouteMap, MCPType
from pydantic import BaseModel, ValidationError
import jsonschema
from jsonschema import validate

logger = logging.getLogger(__name__)


class ToolExecutionResult(BaseModel):
    """Standardized tool execution result"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float
    tool_name: str
    endpoint: str


class ToolManager:
    """
    Dynamic tool management with FastMCP integration
    Automatically converts OpenAPI specs to executable tools with validation
    """
    
    def __init__(self, semantic_state_manager=None):
        """
        Initialize tool manager
        
        Args:
            semantic_state_manager: Semantic state manager for caching results
        """
        self.tools: Dict[str, Any] = {}
        self.route_maps = [
            RouteMap(methods=["GET"], mcp_type=MCPType.TOOL),
            RouteMap(methods=["POST"], mcp_type=MCPType.TOOL),
            RouteMap(methods=["PUT"], mcp_type=MCPType.TOOL),
            RouteMap(methods=["DELETE"], mcp_type=MCPType.TOOL),
        ]
        self.semantic_state = semantic_state_manager
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Tool execution cache
        self.execution_cache: Dict[str, ToolExecutionResult] = {}
        
    async def load_api_spec(self, 
                           openapi_file: Union[str, Path, Dict],
                           api_name: Optional[str] = None) -> int:
        """
        Load and convert OpenAPI specification to executable tools
        
        Args:
            openapi_file: Path to OpenAPI file or dict with spec
            api_name: Optional name for the API
            
        Returns:
            Number of tools loaded
        """
        try:
            # Load OpenAPI specification
            if isinstance(openapi_file, (str, Path)):
                spec = await self._load_spec_from_file(openapi_file)
            else:
                spec = openapi_file
            
            # Extract API name if not provided
            if not api_name:
                api_name = spec.get("info", {}).get("title", "unknown_api")
                api_name = api_name.lower().replace(" ", "_")
            
            # Convert OpenAPI to FastMCP tools
            new_tools = await self._convert_openapi_to_tools(spec, api_name)
            
            # Register tools
            loaded_count = 0
            for tool in new_tools:
                tool_name = f"{api_name}_{tool.name}"
                self.tools[tool_name] = tool
                loaded_count += 1
                logger.info(f"Loaded tool: {tool_name}")
            
            logger.info(f"Loaded {loaded_count} tools from {api_name}")
            return loaded_count
            
        except Exception as e:
            logger.error(f"Failed to load API spec: {e}")
            return 0
    
    async def _load_spec_from_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load OpenAPI spec from file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"OpenAPI file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            else:
                return json.load(f)
    
    async def _convert_openapi_to_tools(self, 
                                       spec: Dict[str, Any], 
                                       api_name: str) -> List[Any]:
        """Convert OpenAPI paths to FastMCP tools"""
        tools = []
        
        try:
            # Create FastMCP instance
            fastmcp = FastMCP(
                openapi_spec=spec,
                route_maps=self.route_maps
            )
            
            # Extract tools from FastMCP
            for route_map in self.route_maps:
                route_tools = fastmcp.get_tools_for_route_map(route_map)
                tools.extend(route_tools)
            
            # Add metadata to tools
            for tool in tools:
                tool.api_name = api_name
                tool.base_url = spec.get("servers", [{}])[0].get("url", "")
                
        except Exception as e:
            logger.error(f"Failed to convert OpenAPI to tools: {e}")
            
        return tools
    
    async def execute_tool(self,
                          tool_name: str,
                          params: Dict[str, Any],
                          cache_key: Optional[str] = None,
                          force_refresh: bool = False) -> ToolExecutionResult:
        """
        Execute a tool with caching and validation
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool
            cache_key: Optional cache key for semantic caching
            force_refresh: Force refresh cache
            
        Returns:
            Tool execution result
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Check cache first
            if not force_refresh and cache_key:
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    logger.debug(f"Using cached result for {tool_name}")
                    return cached_result
            
            # Validate tool exists
            if tool_name not in self.tools:
                raise ValueError(f"Tool not found: {tool_name}")
            
            tool = self.tools[tool_name]
            
            # Validate parameters
            validated_params = await self._validate_tool_params(tool, params)
            
            # Execute tool
            result_data = await self._execute_tool_request(tool, validated_params)
            
            # Create result
            execution_time = asyncio.get_event_loop().time() - start_time
            result = ToolExecutionResult(
                success=True,
                data=result_data,
                execution_time=execution_time,
                tool_name=tool_name,
                endpoint=getattr(tool, 'endpoint', 'unknown')
            )
            
            # Cache result if semantic state manager available
            if self.semantic_state and cache_key:
                await self._cache_result(cache_key, result, params)
            
            # Store in local cache
            self.execution_cache[tool_name] = result
            
            logger.debug(f"Executed {tool_name} in {execution_time:.3f}s")
            return result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Tool execution failed {tool_name}: {e}")
            
            return ToolExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                tool_name=tool_name,
                endpoint="unknown"
            )
    
    async def _validate_tool_params(self, tool: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool parameters against schema"""
        try:
            # Get tool schema if available
            if hasattr(tool, 'schema') and tool.schema:
                validate(instance=params, schema=tool.schema)
            
            # Additional validation for required parameters
            if hasattr(tool, 'required_params'):
                for required_param in tool.required_params:
                    if required_param not in params:
                        raise ValueError(f"Required parameter missing: {required_param}")
            
            return params
            
        except ValidationError as e:
            raise ValueError(f"Parameter validation failed: {e.message}")
        except Exception as e:
            logger.warning(f"Parameter validation skipped: {e}")
            return params
    
    async def _execute_tool_request(self, tool: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual HTTP request for the tool"""
        try:
            # Build request URL
            base_url = getattr(tool, 'base_url', '')
            endpoint = getattr(tool, 'endpoint', '/')
            url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            # Get HTTP method
            method = getattr(tool, 'method', 'GET').upper()
            
            # Prepare request
            request_kwargs = {
                'url': url,
                'timeout': 30.0
            }
            
            if method == 'GET':
                request_kwargs['params'] = params
            else:
                request_kwargs['json'] = params
            
            # Execute request
            response = await self.http_client.request(method, **request_kwargs)
            response.raise_for_status()
            
            # Parse response
            try:
                return response.json()
            except:
                return {"response": response.text}
                
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Request error: {e}")
    
    async def _get_cached_result(self, cache_key: str) -> Optional[ToolExecutionResult]:
        """Get cached result from semantic state manager"""
        try:
            if not self.semantic_state:
                return None
            
            # Query for cached results
            cached_results = await self.semantic_state.query_relevant_state(
                cache_key,
                context_types=["api_result"],
                limit=1,
                score_threshold=0.95  # High threshold for exact matches
            )
            
            if cached_results:
                cached_data = cached_results[0]["data"]
                # Convert back to ToolExecutionResult
                return ToolExecutionResult(**cached_data)
            
        except Exception as e:
            logger.debug(f"Cache lookup failed: {e}")
        
        return None
    
    async def _cache_result(self, 
                           cache_key: str, 
                           result: ToolExecutionResult,
                           params: Dict[str, Any]) -> None:
        """Cache result in semantic state manager"""
        try:
            await self.semantic_state.store_api_result(
                api_name=result.tool_name,
                endpoint=result.endpoint,
                result=result.data or {},
                query_context=cache_key
            )
        except Exception as e:
            logger.debug(f"Failed to cache result: {e}")
    
    def get_tool_context(self) -> str:
        """
        Generate LLM context from available tools
        
        Returns:
            Formatted context string for LLM
        """
        if not self.tools:
            return "No API tools available."
        
        context = "Available API tools:\n\n"
        
        # Group tools by API
        api_groups = {}
        for tool_name, tool in self.tools.items():
            api_name = getattr(tool, 'api_name', 'unknown')
            if api_name not in api_groups:
                api_groups[api_name] = []
            api_groups[api_name].append((tool_name, tool))
        
        # Format each API group
        for api_name, tools in api_groups.items():
            context += f"## {api_name.replace('_', ' ').title()} API\n"
            
            for tool_name, tool in tools:
                description = getattr(tool, 'description', 'No description available')
                endpoint = getattr(tool, 'endpoint', 'unknown')
                method = getattr(tool, 'method', 'GET')
                
                context += f"- **{tool_name}** ({method} {endpoint})\n"
                context += f"  - {description}\n"
                
                # Add parameter info if available
                if hasattr(tool, 'required_params') and tool.required_params:
                    context += f"  - Required params: {', '.join(tool.required_params)}\n"
                
                context += "\n"
        
        return context.strip()
    
    def get_tool_names(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tools.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all tools"""
        health_status = {
            "total_tools": len(self.tools),
            "healthy_tools": 0,
            "failed_tools": [],
            "api_groups": {}
        }
        
        # Group by API
        for tool_name, tool in self.tools.items():
            api_name = getattr(tool, 'api_name', 'unknown')
            if api_name not in health_status["api_groups"]:
                health_status["api_groups"][api_name] = 0
            health_status["api_groups"][api_name] += 1
        
        # Simple health check - just verify tools are loaded
        health_status["healthy_tools"] = len(self.tools)
        
        return health_status
    
    async def close(self):
        """Clean up resources"""
        await self.http_client.aclose()


# Example usage and testing
async def main():
    """Test the tool manager"""
    manager = ToolManager()
    
    # Example OpenAPI spec
    sample_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "servers": [{"url": "https://api.example.com"}],
        "paths": {
            "/accounts/{account_id}/balance": {
                "get": {
                    "summary": "Get account balance",
                    "parameters": [
                        {"name": "account_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {"description": "Account balance"}
                    }
                }
            }
        }
    }
    
    # Load tools
    tools_loaded = await manager.load_api_spec(sample_spec, "test_api")
    print(f"Loaded {tools_loaded} tools")
    
    # Get tool context
    context = manager.get_tool_context()
    print(f"Tool context:\n{context}")
    
    # Clean up
    await manager.close()


if __name__ == "__main__":
    asyncio.run(main())