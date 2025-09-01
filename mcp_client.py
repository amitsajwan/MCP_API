#!/usr/bin/env python3
"""
MCP Client - Real MCP Protocol Implementation
Proper MCP client that follows the official MCP specification:
- Uses MCP protocol for tool discovery and calling
- Connects to MCP server via stdio transport
- Uses LLM for planning and orchestration
- Handles multi-step tool execution with detailed reasoning
"""

import asyncio
import logging
import json
import sys
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import aiohttp
from openai import AzureOpenAI

# MCP types for tool definitions
from mcp.types import Tool

# Import config or create default
try:
    from config import config
except ImportError:
    # Create default config if not available
    class DefaultConfig:
        LOG_LEVEL = "INFO"
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        MAX_TOOL_EXECUTIONS = 5
        
        def validate(self):
            return True
    
    config = DefaultConfig()


# Configure logging
logging.basicConfig(
    level=getattr(logging, getattr(config, 'LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_client")


@dataclass
class ToolCall:
    """Represents a tool call to be executed."""
    tool_name: str
    arguments: Dict[str, Any]
    reason: Optional[str] = None


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None


class MCPClient:
    """MCP Client for connecting to HTTP MCP server."""
    
    def __init__(self, server_host: str = "localhost", server_port: int = 8081):
        """
        Initialize MCP Client for HTTP server connection.
        
        Args:
            server_host: Host of the MCP HTTP server
            server_port: Port of the MCP HTTP server
        """
        self.server_host = server_host
        self.server_port = server_port
        self.server_url = f"http://{server_host}:{server_port}"
        
        # Initialize Azure OpenAI client
        self.openai_client = self._create_azure_client()
        
        # Cache for tools and results
        self.available_tools: List[Tool] = []
        self.tool_results: Dict[str, Any] = {}
        

    
    def _create_azure_client(self) -> Optional[AzureOpenAI]:
        """Create Azure OpenAI client."""
        if not config.AZURE_OPENAI_ENDPOINT:
            logger.warning("Azure OpenAI endpoint not configured - using fallback planning")
            return None
        
        try:
            client = AzureOpenAI(
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_version="2024-02-01"
            )
            logger.info("✅ Azure OpenAI client created")
            return client
        except Exception as e:
            logger.warning(f"Failed to create Azure OpenAI client: {e} - using fallback planning")
            return None
    
    async def connect(self):
        """Connect to MCP server via HTTP."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health") as resp:
                    if resp.status == 200:
                        logger.info(f"✅ Connected to HTTP MCP server at {self.server_url}")
                        return
                    else:
                        raise Exception(f"Server health check failed: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to HTTP MCP server: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from the HTTP MCP server."""
        logger.info("Disconnected from HTTP MCP server")
    
    async def close(self):
        """Close the MCP client connection. Alias for disconnect."""
        await self.disconnect()
    
    async def list_tools(self) -> List[Tool]:
        """Get list of available tools from HTTP MCP server."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/tools") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tools = []
                        for tool_data in data.get("tools", []):
                            tool = Tool(
                                name=tool_data["name"],
                                description=tool_data["description"],
                                inputSchema=tool_data.get("inputSchema", {"type": "object"})
                            )
                            tools.append(tool)
                        self.available_tools = tools
                        logger.info(f"✅ Retrieved {len(tools)} tools from HTTP MCP server")
                        return tools
                    else:
                        raise Exception(f"HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a specific tool on the HTTP MCP server."""
        if arguments is None:
            arguments = {}
        
        try:
            logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
            
            async with aiohttp.ClientSession() as session:
                payload = {"tool_name": tool_name, "arguments": arguments}
                async with session.post(f"{self.server_url}/call_tool", json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return {"status": "success", "data": result}
                    else:
                        error = await resp.text()
                        return {"status": "error", "message": f"HTTP {resp.status}: {error}"}
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"status": "error", "message": str(e)}

    async def perform_login(self) -> Dict[str, Any]:
        """Call the perform_login tool on the MCP server."""
        logger.info("Attempting to perform login via MCP server tool.")
        try:
            result = await self.call_tool("perform_login")
            if result.get("status") == "success":
                logger.info("✅ Login tool call successful.")
                return {"status": "success", "message": "Login successful"}
            else:
                error_message = result.get("message", "Unknown error during login tool call.")
                logger.error(f"❌ Login tool call failed: {error_message}")
                return {"status": "error", "message": error_message}
        except Exception as e:
            logger.error(f"Exception when calling perform_login tool: {e}")
            return {"status": "error", "message": str(e)}
    
    def format_tools_for_openai_functions(self) -> List[Dict[str, Any]]:
        """Format MCP tools for OpenAI function calling (Anthropic Claude style)."""
        functions = []
        for tool in self.available_tools:
            function = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
            functions.append(function)
        return functions
    
    async def chat_with_function_calling(self, user_message: str) -> str:
        """
        Chat with automatic function calling - like Anthropic Claude.
        
        This method:
        1. Lets the LLM analyze the user query
        2. LLM decides which tools to call (if any)
        3. Automatically executes the tools
        4. LLM integrates results into a natural response
        """
        if not self.available_tools:
            await self.list_tools()
        
        if not self.openai_client:
            # Fallback to existing method
            result = await self.process_query(user_message)
            return result.get("summary", "I couldn't process your request.")
        
        # Get tools in OpenAI function format
        functions = self.format_tools_for_openai_functions()
        
        system_prompt = """You are a helpful AI assistant with access to financial API tools.

When users ask questions, analyze what they need and use the available tools to get information.
Be proactive in calling tools when they would help answer the user's question.

You have access to financial systems including:
- Cash management APIs
- CLS (Continuous Linked Settlement) APIs  
- Mailbox/messaging APIs
- Securities trading APIs
- Credential and authentication management

Call tools when needed, then provide a helpful response based on the results."""

        try:
            # Initial LLM call with function calling enabled
            response = self.openai_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                functions=functions,
                function_call="auto",  # Let LLM decide when to call functions
                temperature=0.1,
                max_tokens=1500
            )
            
            message = response.choices[0].message
            
            # Check if LLM wants to call a function
            if message.function_call:
                logger.info(f"LLM called function: {message.function_call.name}")
                
                # Execute the function call
                try:
                    args = json.loads(message.function_call.arguments)
                    tool_result = await self.call_tool(message.function_call.name, args)
                    
                    # Create follow-up conversation with the tool result
                    follow_up_response = self.openai_client.chat.completions.create(
                        model=config.AZURE_OPENAI_DEPLOYMENT,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                            {"role": "assistant", "content": message.content, "function_call": message.function_call},
                            {"role": "function", "name": message.function_call.name, "content": json.dumps(tool_result)}
                        ],
                        temperature=0.1,
                        max_tokens=1500
                    )
                    
                    return follow_up_response.choices[0].message.content
                    
                except Exception as e:
                    logger.error(f"Function call execution failed: {e}")
                    return f"I tried to help by calling {message.function_call.name}, but encountered an error: {e}"
            
            else:
                # LLM provided direct response without needing tools
                return message.content
                
        except Exception as e:
            logger.error(f"Error in function calling: {e}")
            # Fallback to existing method
            result = await self.process_query(user_message)
            return result.get("summary", "I couldn't process your request.")

    async def plan_tool_execution(self, user_query: str) -> List[ToolCall]:
        """Use LLM to plan which tools to execute for a user query with detailed reasoning."""
        if not self.available_tools:
            await self.list_tools()
        
        # If no tools available, return empty plan
        if not self.available_tools:
            logger.warning("No tools available for planning")
            return []
        
        # If no Azure OpenAI client, use simple fallback planning
        if not self.openai_client:
            return self._fallback_planning(user_query)
        
        # Build tools description for LLM
        tools_description = self._build_tools_description()
        
        # Create enhanced system prompt for better reasoning
        system_prompt = f"""You are an AI assistant that helps users interact with financial APIs through MCP tools.

Available tools:
{tools_description}

Your task is to:
1. Analyze the user's query carefully
2. Determine which tools need to be called and why
3. Plan the execution order logically
4. Provide detailed reasoning for each tool call
5. Ensure the plan addresses the user's request completely

Return a JSON array of tool calls with this structure:
[
  {{
    "tool_name": "tool_name_here",
    "arguments": {{"param1": "value1", "param2": "value2"}},
    "reason": "Detailed explanation of why this tool is needed and what information it will provide"
  }}
]

Guidelines for reasoning:
- Be specific about what information each tool will retrieve
- Explain how the tool results will help answer the user's question
- Consider dependencies between tools (e.g., get account info before checking payments)
- Keep the plan focused and efficient
- Maximum {getattr(config, 'MAX_TOOL_EXECUTIONS', 5)} tool calls allowed

Example reasoning:
- "I need to get account information first to understand which accounts are available"
- "Then I'll check pending payments for these accounts to show what's due"
- "Finally, I'll get payment history to provide context about recent activity"

Make your reasoning clear and helpful for the user to understand your thought process."""

        try:
            response = self.openai_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            logger.info(f"LLM planning response: {content}")
            
            # Parse JSON response
            try:
                tool_calls_data = json.loads(content)
                tool_calls = []
                
                for call_data in tool_calls_data:
                    tool_call = ToolCall(
                        tool_name=call_data["tool_name"],
                        arguments=call_data.get("arguments", {}),
                        reason=call_data.get("reason", "No reason provided")
                    )
                    tool_calls.append(tool_call)
                
                return tool_calls[:getattr(config, 'MAX_TOOL_EXECUTIONS', 5)]  # Limit to max executions
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"LLM response was: {content}")
                return []
                
        except Exception as e:
            logger.error(f"LLM planning failed: {e}")
            # Fall back to simple planning
            return self._fallback_planning(user_query)
    
    def _fallback_planning(self, user_query: str) -> List[ToolCall]:
        """Simple rule-based planning when LLM is not available."""
        logger.info("Using fallback planning (no LLM available)")
        
        query_lower = user_query.lower()
        tool_calls = []
        
        # Simple keyword-based matching
        if "pending" in query_lower and "payment" in query_lower:
            tool_calls.append(ToolCall(
                tool_name="cash_api_getPayments",
                arguments={"status": "pending"},
                reason="Getting pending payments based on user request"
            ))
        elif "payment" in query_lower:
            tool_calls.append(ToolCall(
                tool_name="cash_api_getPayments",
                arguments={},
                reason="Getting payments information based on user request"
            ))
        elif "cash" in query_lower and "summary" in query_lower:
            tool_calls.append(ToolCall(
                tool_name="cash_api_getCashSummary",
                arguments={},
                reason="Getting cash summary based on user request"
            ))
        elif "transaction" in query_lower:
            tool_calls.append(ToolCall(
                tool_name="cash_api_getTransactions",
                arguments={},
                reason="Getting transactions based on user request"
            ))
        elif "settlement" in query_lower:
            tool_calls.append(ToolCall(
                tool_name="cls_api_getCLSSettlements",
                arguments={},
                reason="Getting CLS settlements based on user request"
            ))
        elif "portfolio" in query_lower or "position" in query_lower:
            tool_calls.append(ToolCall(
                tool_name="securities_api_getPortfolio",
                arguments={},
                reason="Getting portfolio information based on user request"
            ))
        elif "message" in query_lower or "mailbox" in query_lower:
            tool_calls.append(ToolCall(
                tool_name="mailbox_api_getMessages",
                arguments={},
                reason="Getting messages based on user request"
            ))
        else:
            # Default to cash summary if no specific match
            tool_calls.append(ToolCall(
                tool_name="cash_api_getCashSummary",
                arguments={},
                reason="Getting cash summary as a general overview"
            ))
        
        logger.info(f"Fallback planning created {len(tool_calls)} tool calls")
        return tool_calls
    
    def _build_tools_description(self) -> str:
        """Build a detailed description of available tools for LLM."""
        if not self.available_tools:
            return "No tools available"
        
        descriptions = []
        for tool in self.available_tools:
            desc = f"- {tool.name}: {tool.description}"
            
            # Add input schema information if available
            if tool.inputSchema and "properties" in tool.inputSchema:
                props = tool.inputSchema["properties"]
                if props:
                    param_desc = []
                    for param_name, param_info in props.items():
                        param_type = param_info.get("type", "string")
                        param_desc.append(f"{param_name} ({param_type})")
                    desc += f" [Parameters: {', '.join(param_desc)}]"
            
            descriptions.append(desc)
        
        return "\n".join(descriptions)
    
    async def execute_tool_plan(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute a plan of tool calls with detailed logging."""
        results = []
        
        for i, tool_call in enumerate(tool_calls, 1):
            logger.info(f"Executing tool {i}/{len(tool_calls)}: {tool_call.tool_name}")
            logger.info(f"Reason: {tool_call.reason}")
            logger.info(f"Arguments: {tool_call.arguments}")
            
            try:
                result = await self.call_tool(tool_call.tool_name, tool_call.arguments)
                
                tool_result = ToolResult(
                    tool_name=tool_call.tool_name,
                    success=result.get("status") == "success",
                    result=result.get("data") if result.get("status") == "success" else None,
                    error=result.get("message") if result.get("status") == "error" else None
                )
                
                results.append(tool_result)
                
                if tool_result.success:
                    logger.info(f"✅ Tool {tool_call.tool_name} executed successfully")
                else:
                    logger.error(f"❌ Tool {tool_call.tool_name} failed: {tool_result.error}")
                    # Continue execution even if one tool fails
                    
            except Exception as e:
                logger.error(f"Exception during tool execution: {e}")
                results.append(ToolResult(
                    tool_name=tool_call.tool_name,
                    success=False,
                    result=None,
                    error=str(e)
                ))
        
        return results
    
    async def generate_summary(self, user_query: str, tool_results: List[ToolResult], tool_calls: List[ToolCall]) -> str:
        """Generate a natural language summary of the results with enhanced reasoning."""
        if not tool_results:
            return "No tools were executed to gather information for your request."
        
        # If no OpenAI client, use simple summary
        if not self.openai_client:
            return self._generate_simple_summary(user_query, tool_results, tool_calls)
        
        # Build detailed results summary for LLM
        results_summary = []
        execution_summary = []
        
        for i, (result, tool_call) in enumerate(zip(tool_results, tool_calls), 1):
            if result.success:
                result_preview = str(result.result)[:200] + "..." if len(str(result.result)) > 200 else str(result.result)
                results_summary.append(f"Tool {i}: {result.tool_name}")
                results_summary.append(f"  Reason: {tool_call.reason}")
                results_summary.append(f"  Result: {result_preview}")
                execution_summary.append(f"✅ {result.tool_name}: Success")
            else:
                results_summary.append(f"Tool {i}: {result.tool_name}")
                results_summary.append(f"  Reason: {tool_call.reason}")
                results_summary.append(f"  Error: {result.error}")
                execution_summary.append(f"❌ {result.tool_name}: Failed - {result.error}")
        
        results_text = "\n".join(results_summary)
        execution_status = "\n".join(execution_summary)
        
        system_prompt = """You are a helpful AI assistant. Generate a clear, comprehensive summary of the API results in response to the user's query.

Your response should include:
1. A direct answer to the user's question
2. Key insights from the data retrieved
3. Important details or numbers that are relevant
4. Any errors or issues encountered
5. Suggestions for next steps if relevant

Focus on being:
- Conversational and helpful
- Specific with data and numbers
- Clear about what was found vs. what failed
- Actionable when possible

Use the execution results to provide concrete information rather than generic responses."""

        try:
            response = self.openai_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"""
User Query: {user_query}

Execution Summary:
{execution_status}

Detailed Results:
{results_text}

Please provide a comprehensive response based on this information.
"""}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            # Fallback to simple summary
            return self._generate_simple_summary(user_query, tool_results, tool_calls)
    
    def _generate_simple_summary(self, user_query: str, tool_results: List[ToolResult], tool_calls: List[ToolCall]) -> str:
        """Generate a simple summary without LLM."""
        successful_tools = [r for r in tool_results if r.success]
        failed_tools = [r for r in tool_results if not r.success]
        
        summary_parts = []
        summary_parts.append(f"Query: {user_query}")
        summary_parts.append("")
        
        if successful_tools:
            summary_parts.append("✅ Successfully executed:")
            for result in successful_tools:
                summary_parts.append(f"  - {result.tool_name}")
                if result.result:
                    # Try to show key information from result
                    result_str = str(result.result)
                    if len(result_str) > 300:
                        result_str = result_str[:300] + "..."
                    summary_parts.append(f"    Result: {result_str}")
            summary_parts.append("")
        
        if failed_tools:
            summary_parts.append("❌ Failed to execute:")
            for result in failed_tools:
                summary_parts.append(f"  - {result.tool_name}: {result.error}")
            summary_parts.append("")
        
        summary_parts.append(f"Total: {len(successful_tools)} successful, {len(failed_tools)} failed")
        
        return "\n".join(summary_parts)
    
    async def process_message(self, message: str) -> str:
        """Process a user message and return a response."""
        result = await self.process_query(message)
        if result["status"] == "success":
            return result["summary"]
        else:
            return f"Error: {result['message']}"

    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a user query end-to-end with enhanced reasoning."""
        logger.info(f"Processing query: {user_query}")
        
        try:
            # Ensure we're connected and have tools
            if not self.session:
                await self.connect()
            
            if not self.available_tools:
                await self.list_tools()

            # Step 1: Plan tool execution with detailed reasoning
            tool_calls = await self.plan_tool_execution(user_query)
            
            if not tool_calls:
                return {
                    "status": "error",
                    "message": "Could not plan tool execution for this query",
                    "plan": [],
                    "results": [],
                    "reasoning": "I couldn't determine which tools to use for your request. This might be because the available tools don't match your query, or I need more information to understand what you're looking for.",
                    "summary": "I couldn't determine which tools to use for your request. Please try rephrasing your question or check if the required API endpoints are available."
                }
            
            # Step 2: Execute tools
            tool_results = await self.execute_tool_plan(tool_calls)
            
            # Step 3: Generate enhanced summary with reasoning
            summary = await self.generate_summary(user_query, tool_results, tool_calls)
            
            # Step 4: Create detailed reasoning
            reasoning = self._create_detailed_reasoning(user_query, tool_calls, tool_results)
            
            return {
                "status": "success",
                "plan": [{"tool_name": tc.tool_name, "arguments": tc.arguments, "reason": tc.reason} for tc in tool_calls],
                "results": [{"tool_name": tr.tool_name, "success": tr.success, "result": tr.result, "error": tr.error} for tr in tool_results],
                "reasoning": reasoning,
                "summary": summary
            }
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "status": "error",
                "message": str(e),
                "plan": [],
                "results": [],
                "reasoning": f"An error occurred while processing your request: {str(e)}",
                "summary": f"I encountered an error while processing your request: {str(e)}"
            }
    


    def _create_detailed_reasoning(self, user_query: str, tool_calls: List[ToolCall], tool_results: List[ToolResult]) -> str:
        """Create detailed human-readable reasoning about the execution."""
        reasoning_parts = []
        
        # Overall approach
        reasoning_parts.append(f"I analyzed your request: \"{user_query}\"")
        reasoning_parts.append(f"I planned to execute {len(tool_calls)} tool(s) to gather the necessary information:")
        
        # Tool-by-tool reasoning
        for i, (tool_call, tool_result) in enumerate(zip(tool_calls, tool_results), 1):
            reasoning_parts.append(f"\n{i}. {tool_call.tool_name}")
            reasoning_parts.append(f"   Reason: {tool_call.reason}")
            if tool_result.success:
                reasoning_parts.append(f"   Status: ✅ Success")
                if tool_result.result:
                    result_preview = str(tool_result.result)[:100] + "..." if len(str(tool_result.result)) > 100 else str(tool_result.result)
                    reasoning_parts.append(f"   Data: {result_preview}")
            else:
                reasoning_parts.append(f"   Status: ❌ Failed")
                reasoning_parts.append(f"   Error: {tool_result.error}")
        
        # Execution summary
        successful = sum(1 for r in tool_results if r.success)
        total = len(tool_results)
        reasoning_parts.append(f"\nExecution Summary: {successful}/{total} tools succeeded.")
        
        if successful == total:
            reasoning_parts.append("All tools executed successfully, providing complete information for your query.")
        elif successful > 0:
            reasoning_parts.append("Some tools succeeded, providing partial information for your query.")
        else:
            reasoning_parts.append("No tools succeeded, so I couldn't gather the requested information.")
        
        return "\n".join(reasoning_parts)


async def main():
    """Example usage of MCP Client - stdio only."""
    print("MCP Client Test")
    print("===============")
    print()
    print("🔌 Using stdio connection to MCP server")
    print("📋 Make sure to start the MCP server first:")
    print("   python mcp_server.py")
    print()
    
    # Create stdio-only client
    client = MCPClient()
    
    try:
        print(f"\n🔗 Connecting to MCP server via stdio...")
        await client.connect()
        
        print("📋 Listing available tools...")
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools[:5]]}..." + (f" and {len(tools)-5} more" if len(tools) > 5 else ""))
        
        if tools:
            print("\n🧪 Testing tool execution...")
            result = await client.process_query("Show me pending payments")
            print("Result:")
            print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
        print("\n💡 Make sure the MCP server is running:")
        print("   python mcp_server.py")
    finally:
        await client.disconnect()
        print("\n👋 Disconnected from MCP server")


if __name__ == "__main__":
    asyncio.run(main())