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
from openai import AsyncOpenAI

# MCP Protocol imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

# Import config or create default
try:
    from config import config
except ImportError:
    # Create default config if not available
    class DefaultConfig:
        LOG_LEVEL = "INFO"
        AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        USE_AZURE_AD_TOKEN_PROVIDER = False
        AZURE_AD_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"
        MAX_TOOL_EXECUTIONS = 5
        
        def validate(self):
            return True
    
    config = DefaultConfig()


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
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
    """Real MCP Client implementation using official MCP protocol."""
    
    def __init__(self, mcp_server_command: List[str] = None):
        self.mcp_server_command = mcp_server_command or ["python", "mcp_server.py"]
        self.session: Optional[ClientSession] = None
        self._client_context = None
        self._session_context = None
        self._stdio_streams = None
        
        # Initialize OpenAI client based on authentication mode
        if getattr(config, 'USE_AZURE_AD_TOKEN_PROVIDER', False):
            self.openai_client = self._create_azure_ad_client()
        else:
            self.openai_client = self._create_api_key_client()
        
        # Cache for tools and results
        self.available_tools: List[Tool] = []
        self.tool_results: Dict[str, Any] = {}
        

    
    def _create_azure_ad_client(self) -> AsyncOpenAI:
        """Create Azure OpenAI client with Azure AD token provider."""
        try:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            
            # Create token provider
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), 
                config.AZURE_AD_TOKEN_SCOPE
            )
            
            # Create Azure OpenAI client with token provider
            client = AsyncOpenAI(
                base_url=config.AZURE_OPENAI_ENDPOINT,
                azure_ad_token_provider=token_provider
            )
            
            logger.info("✅ Azure OpenAI client created with Azure AD token provider")
            return client
            
        except ImportError:
            logger.error("❌ azure-identity package not found. Install with: pip install azure-identity")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to create Azure AD client: {e}")
            raise
    
    def _create_api_key_client(self) -> AsyncOpenAI:
        """Create Azure OpenAI client with API key authentication."""
        if not config.AZURE_OPENAI_API_KEY or not config.AZURE_OPENAI_ENDPOINT:
            logger.warning("Azure OpenAI credentials not configured, using mock client")
            return self._create_mock_client()
        
        client = AsyncOpenAI(
            api_key=config.AZURE_OPENAI_API_KEY,
            base_url=config.AZURE_OPENAI_ENDPOINT,
            default_headers={'api-key': config.AZURE_OPENAI_API_KEY}
        )
        
        logger.info("✅ Azure OpenAI client created with API key authentication")
        return client
    
    def _create_mock_client(self) -> AsyncOpenAI:
        """Create a mock OpenAI client for testing."""
        # This is a fallback for when credentials aren't configured
        # In production, you should always have proper credentials
        logger.warning("Creating mock OpenAI client - responses may be limited")
        return AsyncOpenAI(
            api_key="sk-mock-key",
            base_url="https://api.openai.com/v1"
        )
    
    async def connect(self):
        """Connect to MCP server using stdio transport."""
        if self.session is not None:
            return
        
        try:
            # Find the MCP server script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            mcp_server_path = os.path.join(current_dir, "mcp_server.py")
            
            # Check if file exists
            if not os.path.exists(mcp_server_path):
                # Try alternative locations
                alternative_paths = [
                    os.path.join(os.getcwd(), "mcp_server.py"),
                    "./mcp_server.py",
                    "mcp_server.py"
                ]
                
                for alt_path in alternative_paths:
                    abs_path = os.path.abspath(alt_path)
                    if os.path.exists(abs_path):
                        mcp_server_path = abs_path
                        break
                else:
                    raise FileNotFoundError(f"Could not find mcp_server.py in {current_dir} or current directory. Available files: {os.listdir('.')}") 
            
            logger.info(f"Using MCP server at: {mcp_server_path}")
            
            # Create server parameters with proper command
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[mcp_server_path],
                env=dict(os.environ)  # Pass current environment
            )
            
            # Connect to the server and get read/write streams
            self._client_context = stdio_client(server_params)
            self._stdio_streams = await self._client_context.__aenter__()
            read, write = self._stdio_streams
            
            # Create client session with the streams
            self._session_context = ClientSession(read, write)
            self.session = await self._session_context.__aenter__()
            
            # Initialize the session (crucial step!)
            await self.session.initialize()
            
            logger.info("✅ Connected to MCP server via stdio transport")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MCP server: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from the MCP server and clean up resources."""
        if not self.session:
            logger.warning("No active session to disconnect.")
            return

        try:
            # Close session first
            if hasattr(self, '_session_context') and self._session_context:
                await self._session_context.__aexit__(None, None, None)
                self._session_context = None
                
            # Then close stdio client
            if hasattr(self, '_client_context') and self._client_context:
                await self._client_context.__aexit__(None, None, None)
                
            logger.info("Session closed successfully.")
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
        finally:
            self.session = None
            self._client_context = None
            self._stdio_streams = None
            logger.info("Disconnected from MCP server.")
    
    async def close(self):
        """Close the MCP client connection. Alias for disconnect."""
        await self.disconnect()
    
    async def list_tools(self) -> List[Tool]:
        """Get list of available tools from MCP server using MCP protocol."""
        if not self.session:
            await self.connect()
        
        try:
            tools_response = await self.session.list_tools()
            self.available_tools = tools_response.tools
            logger.info(f"✅ Retrieved {len(self.available_tools)} tools from MCP server")
            return self.available_tools
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a specific tool on the MCP server using MCP protocol."""
        if not self.session:
            await self.connect()
        
        try:
            print (" ==== >>>>> ")
            # Execute tool via MCP protocol
            result = await self.session.call_tool(
                name=tool_name,
                arguments=kwargs
            )
            print (f" ==== >>>>> {result}")
            # Process result
            if result.isError:
                error_message = ""
                for content in result.content:
                    if hasattr(content, 'text'):
                        error_message += content.text
                
                logger.error(f"Tool call failed: {error_message}")
                return {"status": "error", "message": error_message}
            else:
                # Extract text content from result
                result_text = ""
                for content in result.content:
                    if hasattr(content, 'text'):
                        result_text += content.text
                
                # Try to parse as JSON, fallback to text
                try:
                    result_data = json.loads(result_text)
                except json.JSONDecodeError:
                    result_data = result_text
                
                # Store result for potential chaining
                self.tool_results[tool_name] = result_data
                
                return {
                    "status": "success",
                    "data": result_data
                }
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def plan_tool_execution(self, user_query: str) -> List[ToolCall]:
        """Use LLM to plan which tools to execute for a user query with detailed reasoning."""
        if not self.available_tools:
            await self.list_tools()
        
        # If no tools available, return empty plan
        if not self.available_tools:
            logger.warning("No tools available for planning")
            return []
        
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
            response = await self.openai_client.chat.completions.create(
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
            # Return empty plan if LLM fails
            return []
    
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
                result = await self.call_tool(tool_call.tool_name, **tool_call.arguments)
                
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
            response = await self.openai_client.chat.completions.create(
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
            # Fallback to basic summary
            successful_tools = [r.tool_name for r in tool_results if r.success]
            failed_tools = [r.tool_name for r in tool_results if not r.success]
            
            summary_parts = []
            if successful_tools:
                summary_parts.append(f"Successfully executed: {', '.join(successful_tools)}")
            if failed_tools:
                summary_parts.append(f"Failed to execute: {', '.join(failed_tools)}")
            
            return "\n".join(summary_parts) if summary_parts else "No tools could be executed."
    
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
    """Example usage of MCP Client."""
    client = MCPClient()
    
    try:
        # Test connection
        await client.connect()
        
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        # Process a query
        result = await client.process_query("Show me pending payments")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())