#!/usr/bin/env python3
"""
MCP LLM Client - Proper MCP Client with Function Calling

This client follows the real-world MCP pattern where:
1. MCP Server provides tools only
2. MCP Client does LLM planning and orchestration with function calling
3. Client handles authentication flow automatically
4. LLM can directly call tools using function calling (like Anthropic/OpenAI)
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import aiohttp
from openai import AsyncOpenAI

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_llm_client")


@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    reason: Optional[str] = None


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None


class MCPLLMClient:
    def __init__(self, mcp_server_url: str = None, llm_model: str = "gpt-4"):
        self.mcp_server_url = mcp_server_url or os.getenv('MCP_SERVER_ENDPOINT', 'http://localhost:9000')
        self.llm_model = llm_model
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            base_url=os.getenv('AZURE_OPENAI_ENDPOINT'),
            default_headers={'api-key': os.getenv('AZURE_OPENAI_API_KEY')}
        )
        
        # Cache for tools and results
        self.available_tools: List[Dict[str, Any]] = []
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
        self.tool_results: Dict[str, Any] = {}
        
    async def _ensure_session(self):
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server."""
        await self._ensure_session()
        try:
            async with self._session.get(f"{self.mcp_server_url}/mcp/tools") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.available_tools = data.get("tools", [])
                    return self.available_tools
                else:
                    logger.error(f"Failed to get tools: HTTP {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []
    
    async def get_tool_metadata(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed metadata for a specific tool including parameters."""
        await self._ensure_session()
        try:
            async with self._session.get(f"{self.mcp_server_url}/mcp/tool_meta/{tool_name}") as resp:
                if resp.status == 200:
                    metadata = await resp.json()
                    self.tool_metadata[tool_name] = metadata
                    return metadata
                else:
                    logger.error(f"Failed to get tool metadata for {tool_name}: HTTP {resp.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting tool metadata for {tool_name}: {e}")
            return {}
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a specific tool on the MCP server."""
        await self._ensure_session()
        try:
            async with self._session.post(
                f"{self.mcp_server_url}/mcp/tools/{tool_name}",
                json={"arguments": kwargs}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    # Store result for potential chaining
                    self.tool_results[tool_name] = result
                    return result
                else:
                    error_text = await resp.text()
                    logger.error(f"Tool call failed: HTTP {resp.status}: {error_text}")
                    return {"status": "error", "message": f"HTTP {resp.status}: {error_text}"}
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def set_credentials(self, username: str, password: str, api_key_name: Optional[str] = None, 
                            api_key_value: Optional[str] = None, login_url: Optional[str] = None) -> Dict[str, Any]:
        """Set credentials for authentication."""
        return await self.call_tool("set_credentials_tool", 
                                   username=username, 
                                   password=password, 
                                   api_key_name=api_key_name,
                                   api_key_value=api_key_value,
                                   login_url=login_url)

    async def login(self) -> Dict[str, Any]:
        """Login using Basic Auth and return session status."""
        return await self.call_tool("login")
    
    def _build_function_definitions(self) -> List[Dict[str, Any]]:
        """Build OpenAI function definitions from available tools."""
        functions = []
        
        for tool in self.available_tools:
            tool_name = tool['name']
            description = tool['description']
            
            # Get metadata if available
            metadata = self.tool_metadata.get(tool_name, {})
            parameters = metadata.get('parameters', [])
            
            # Build properties and required fields
            properties = {}
            required = []
            
            for param in parameters:
                param_name = param.get('name', '')
                param_type = param.get('type', 'string')
                param_desc = param.get('description', '')
                param_required = param.get('required', False)
                
                if param_name:
                    properties[param_name] = {
                        "type": param_type,
                        "description": param_desc
                    }
                    if param_required:
                        required.append(param_name)
            
            function_def = {
                "name": tool_name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
            functions.append(function_def)
        
        return functions
    
    async def execute_query_with_function_calling(self, user_query: str) -> Dict[str, Any]:
        """Execute a user query using OpenAI function calling."""
        logger.info(f"Executing query with function calling: {user_query}")
        
        # Get available tools if not cached
        if not self.available_tools:
            await self.list_tools()
        
        # Get metadata for all tools
        for tool in self.available_tools:
            await self.get_tool_metadata(tool['name'])
        
        # Build function definitions
        functions = self._build_function_definitions()
        logger.info(f"Built {len(functions)} function definitions")
        
        # Prepare messages
        messages = [
            {
                "role": "system", 
                "content": """You are an intelligent assistant that can call MCP server tools to help users.

Available tools are provided as functions. You can call these functions directly to:
1. Get data from APIs (payments, transactions, securities, etc.)
2. Handle authentication when needed
3. Provide comprehensive answers based on the data

Instructions:
- Analyze the user's request and call appropriate functions
- If authentication is required, call set_credentials_tool() then login()
- Use the results to provide a natural language answer
- Handle errors gracefully and suggest solutions

Remember: You have direct access to call any of the provided functions."""
            },
            {"role": "user", "content": user_query}
        ]
        
        # Track tool calls and results
        tool_calls_made = []
        tool_results = []
        
        try:
            # First call - let the model decide what to do
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                tools=functions,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=2000
            )
            
            response_message = response.choices[0].message
            messages.append(response_message)
            
            # Handle tool calls if any
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"LLM calling tool: {tool_name} with args: {arguments}")
                    tool_calls_made.append({
                        "tool": tool_name,
                        "arguments": arguments,
                        "reason": "LLM function call"
                    })
                    
                    # Execute the tool
                    result = await self.call_tool(tool_name, **arguments)
                    tool_results.append(ToolResult(
                        tool_name=tool_name,
                        success=result.get("status") == "success",
                        result=result,
                        error=result.get("message") if result.get("status") != "success" else None
                    ))
                    
                    # Handle authentication errors
                    if result.get("status") == "auth_required":
                        logger.info("Authentication required, returning auth_required status")
                        return {
                            "status": "auth_required",
                            "message": "Please set credentials first using set_credentials_tool",
                            "spec_name": result.get("spec_name"),
                            "tool_calls": tool_calls_made
                        }
                    
                    # Add tool result to messages for next iteration
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, indent=2)
                    })
                
                # Second call - let the model process the results
                final_response = await self.openai_client.chat.completions.create(
                    model=self.llm_model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=1000
                )
                
                final_answer = final_response.choices[0].message.content
            else:
                # No tool calls made, use the direct response
                final_answer = response_message.content
            
            return {
                "status": "success",
                "query": user_query,
                "tool_calls": tool_calls_made,
                "results": [r.result for r in tool_results if r.success],
                "answer": final_answer
            }
            
        except Exception as e:
            logger.error(f"Error in function calling execution: {e}")
            return {
                "status": "error",
                "query": user_query,
                "message": str(e),
                "tool_calls": tool_calls_made,
                "results": [r.result for r in tool_results if r.success]
            }
    
    async def execute_query(self, user_query: str) -> Dict[str, Any]:
        """Execute a user query using function calling (preferred method)."""
        return await self.execute_query_with_function_calling(user_query)


# Example usage
async def main():
    client = MCPLLMClient()
    
    # Set credentials first
    await client.set_credentials("testuser", "testpass", "cash_api")
    
    # Execute a query
    result = await client.execute_query("Show me pending payments")
    print(json.dumps(result, indent=2))
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
