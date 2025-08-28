#!/usr/bin/env python3
"""
MCP LLM Client - Proper MCP Client with LLM Planning

This client follows the real-world MCP pattern where:
1. MCP Server provides tools only
2. MCP Client does LLM planning and orchestration
3. Client handles authentication flow automatically
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
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview'),
            default_headers={'api-key': os.getenv('AZURE_OPENAI_API_KEY')}
        )
        
        # Cache for tools and results
        self.available_tools: List[Dict[str, Any]] = []
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
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with available tools."""
        tools_info = []
        for tool in self.available_tools:
            tools_info.append(f"- {tool['name']}: {tool['description']}")
        
        return f"""You are an intelligent assistant that can call MCP server tools to help users.

Available MCP server tools:
{chr(10).join(tools_info)}

Instructions:
1. Analyze the user's request and determine which MCP server tools to call
2. Call MCP server tools in the correct order to fulfill the request
3. Use results from previous MCP server tools as inputs to subsequent tools when needed
4. Handle authentication: if a tool fails with auth_required, call set_credentials_tool() then login()
5. Provide a natural language summary of the results

Tool calling format:
- Use the exact tool names from the MCP server tools list above
- Provide all required parameters
- Handle authentication errors by calling set_credentials_tool() then login()
- NEVER call external APIs directly - only use MCP server tools

Example workflow:
1. User asks for "pending payments"
2. If auth_required, call set_credentials_tool() then login()
3. Call cash_api_getPayments MCP server tool with status=pending
4. Summarize the results in natural language

Remember: You ONLY call MCP server tools, never external APIs directly."""
    
    async def _plan_tool_calls(self, user_query: str) -> List[ToolCall]:
        """Use LLM to plan which tools to call."""
        system_prompt = self._build_system_prompt()
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Plan the tool calls needed for: {user_query}"}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse the response to extract tool calls
            content = response.choices[0].message.content
            logger.info(f"LLM planning response: {content}")
            
            # Simple parsing - in a real implementation, you'd want more sophisticated parsing
            # For now, we'll use a basic approach
            tool_calls = []
            
            # Look for tool names in the response
            for tool in self.available_tools:
                if tool['name'].lower() in content.lower():
                    # Extract parameters from the response
                    args = {}
                    if 'status=' in content:
                        args['status'] = 'pending'  # Default for payment queries
                    
                    tool_calls.append(ToolCall(
                        tool_name=tool['name'],
                        arguments=args,
                        reason=f"Detected {tool['name']} in query"
                    ))
            
            return tool_calls
            
        except Exception as e:
            logger.error(f"Error in LLM planning: {e}")
            return []
    
    async def execute_query(self, user_query: str) -> Dict[str, Any]:
        """Execute a user query using LLM planning and tool execution."""
        logger.info(f"Executing query: {user_query}")
        
        # Get available tools if not cached
        if not self.available_tools:
            await self.list_tools()
        
        # Plan tool calls
        tool_calls = await self._plan_tool_calls(user_query)
        logger.info(f"Planned {len(tool_calls)} tool calls")
        
        results = []
        final_answer = ""
        
        for tool_call in tool_calls:
            try:
                logger.info(f"Executing {tool_call.tool_name} with args: {tool_call.arguments}")
                result = await self.call_tool(tool_call.tool_name, **tool_call.arguments)
                
                # Handle authentication errors
                if result.get("status") == "auth_required":
                    logger.info("Authentication required, prompting for credentials")
                    return {
                        "status": "auth_required",
                        "message": "Please set credentials first using set_credentials_tool",
                        "spec_name": result.get("spec_name")
                    }
                
                results.append(ToolResult(
                    tool_name=tool_call.tool_name,
                    success=result.get("status") == "success",
                    result=result,
                    error=result.get("message") if result.get("status") != "success" else None
                ))
                
            except Exception as e:
                logger.error(f"Error executing {tool_call.tool_name}: {e}")
                results.append(ToolResult(
                    tool_name=tool_call.tool_name,
                    success=False,
                    result=None,
                    error=str(e)
                ))
        
        # Generate final answer using LLM
        if results:
            final_answer = await self._generate_answer(user_query, results)
        
        return {
            "status": "success",
            "query": user_query,
            "tool_calls": [{"tool": r.tool_name, "success": r.success, "error": r.error} for r in results],
            "results": [r.result for r in results if r.success],
            "answer": final_answer
        }
    
    async def _generate_answer(self, user_query: str, results: List[ToolResult]) -> str:
        """Generate a natural language answer from tool results."""
        try:
            # Build context from successful results
            context = []
            for result in results:
                if result.success and result.result:
                    context.append(f"{result.tool_name}: {json.dumps(result.result, indent=2)}")
            
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Summarize the API results in natural language."},
                    {"role": "user", "content": f"User asked: {user_query}\n\nResults:\n{chr(10).join(context)}\n\nProvide a clear, natural language summary:"}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"Query executed successfully. {len([r for r in results if r.success])} tools completed successfully."


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