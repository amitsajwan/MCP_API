#!/usr/bin/env python3
"""
MCP Client - Fixed Version with Robust Connection Handling
Critical fixes:
- Robust server path resolution
- Proper connection health monitoring
- Better error handling and debugging
- Connection retry logic
"""

import asyncio
import logging
import json
import sys
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from openai import AzureOpenAI

# MCP Protocol imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

# Import config or create default
try:
    from config import config
except ImportError:
    class DefaultConfig:
        LOG_LEVEL = "INFO"
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        MAX_TOOL_EXECUTIONS = 5
        USE_AZURE_AD_TOKEN_PROVIDER = True
        
        def validate(self):
            return True
    
    config = DefaultConfig()

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_client")


class MCPConnectionError(Exception):
    """Specific MCP connection error with debugging info"""
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


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


class MCPClient:
    """Fixed MCP Client implementation with robust connection handling."""
    
    def __init__(self, mcp_server_command: List[str] = None):
        self.mcp_server_command = mcp_server_command or ["python", self._find_mcp_server()]
        self.session: Optional[ClientSession] = None
        self._client_context = None
        self._session_context = None
        self._stdio_streams = None
        self._connection_healthy = False
        
        # Initialize Azure OpenAI client
        self.openai_client = self._create_azure_client()
        
        # Cache for tools and results
        self.available_tools: List[Tool] = []
        self.tool_results: Dict[str, Any] = {}
    
    def _find_mcp_server(self) -> str:
        """Robust server path resolution - CRITICAL FIX"""
        possible_paths = [
            # Same directory as this file
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py"),
            # Current working directory
            os.path.join(os.getcwd(), "mcp_server.py"),
            # Relative paths
            "./mcp_server.py",
            "mcp_server.py",
            # Parent directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp_server.py")
        ]
        
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path) and os.access(abs_path, os.R_OK):
                logger.info(f"Found MCP server at: {abs_path}")
                return abs_path
        
        # List available files for debugging
        current_files = []
        try:
            current_files = [f for f in os.listdir('.') if f.endswith('.py')]
        except:
            pass
            
        error_details = {
            "searched_paths": possible_paths,
            "current_directory": os.getcwd(),
            "available_python_files": current_files,
            "script_directory": os.path.dirname(os.path.abspath(__file__))
        }
        
        raise FileNotFoundError(f"mcp_server.py not found. Searched: {possible_paths}. Available .py files: {current_files}")
    
    def _create_azure_client(self) -> AzureOpenAI:
        """Create Azure OpenAI client with proper error handling"""
        if not config.AZURE_OPENAI_ENDPOINT:
            logger.warning("Azure OpenAI endpoint not configured - LLM features disabled")
            return None
        
        try:
            if getattr(config, 'USE_AZURE_AD_TOKEN_PROVIDER', True):
                # Use Azure AD Token Provider (recommended)
                from azure.identity import DefaultAzureCredential
                
                client = AzureOpenAI(
                    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                    azure_ad_token_provider=DefaultAzureCredential().get_token("https://cognitiveservices.azure.com/.default"),
                    api_version="2024-02-01"
                )
            else:
                # Use API key (legacy)
                client = AzureOpenAI(
                    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                    api_key=config.AZURE_OPENAI_API_KEY,
                    api_version="2024-02-01"
                )
            
            logger.info("✅ Azure OpenAI client created successfully")
            return client
        except Exception as e:
            logger.error(f"❌ Failed to create Azure OpenAI client: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check if MCP connection is healthy"""
        try:
            if not self.session:
                return False
            
            # Try to list tools as a health check
            tools_response = await self.session.list_tools()
            self._connection_healthy = True
            return True
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            self._connection_healthy = False
            return False
    
    async def connect_with_retry(self, max_retries: int = 3) -> bool:
        """Connect with retry logic"""
        for attempt in range(max_retries):
            try:
                await self.connect()
                if await self.health_check():
                    logger.info(f"✅ Connected to MCP server (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"Connection unhealthy on attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
        
        return False
    
    async def connect(self):
        """Connect to MCP server using stdio transport with better error handling"""
        if self.session is not None:
            return
        
        try:
            mcp_server_path = self._find_mcp_server()
            
            logger.info(f"Starting MCP server: {sys.executable} {mcp_server_path}")
            
            # Create server parameters with proper environment
            env = dict(os.environ)
            env.update({
                'PYTHONPATH': os.pathsep.join([os.path.dirname(mcp_server_path)] + sys.path),
                'PYTHONUNBUFFERED': '1'  # Ensure immediate output
            })
            
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[mcp_server_path],
                env=env
            )
            
            # Connect to the server
            self._client_context = stdio_client(server_params)
            self._stdio_streams = await self._client_context.__aenter__()
            read, write = self._stdio_streams
            
            # Create client session
            self._session_context = ClientSession(read, write)
            self.session = await self._session_context.__aenter__()
            
            # Initialize the session
            await self.session.initialize()
            
            # Verify connection health
            if await self.health_check():
                logger.info("✅ MCP server connected and healthy")
            else:
                raise MCPConnectionError("Connection established but health check failed")
            
        except Exception as e:
            error_details = {
                "server_path": getattr(self, '_find_mcp_server', lambda: 'unknown')(),
                "current_dir": os.getcwd(),
                "python_executable": sys.executable,
                "python_path": sys.path,
                "error_type": type(e).__name__
            }
            
            # Clean up on failure
            await self._cleanup_connection()
            
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}", error_details)
    
    async def _cleanup_connection(self):
        """Clean up connection resources"""
        try:
            if hasattr(self, '_session_context') and self._session_context:
                await self._session_context.__aexit__(None, None, None)
        except:
            pass
        
        try:    
            if hasattr(self, '_client_context') and self._client_context:
                await self._client_context.__aexit__(None, None, None)
        except:
            pass
            
        self.session = None
        self._client_context = None
        self._session_context = None
        self._stdio_streams = None
        self._connection_healthy = False
    
    async def disconnect(self):
        """Disconnect from the MCP server and clean up resources"""
        if not self.session:
            logger.debug("No active session to disconnect")
            return

        logger.info("Disconnecting from MCP server...")
        await self._cleanup_connection()
        logger.info("✅ Disconnected from MCP server")
    
    async def close(self):
        """Close the MCP client connection. Alias for disconnect."""
        await self.disconnect()
    
    async def list_tools(self) -> List[Tool]:
        """Get list of available tools from MCP server"""
        if not self.session:
            if not await self.connect_with_retry():
                raise MCPConnectionError("Failed to connect for listing tools")
        
        try:
            tools_response = await self.session.list_tools()
            self.available_tools = tools_response.tools
            logger.info(f"✅ Retrieved {len(self.available_tools)} tools from MCP server")
            return self.available_tools
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            # Try to reconnect once
            if await self.connect_with_retry():
                try:
                    tools_response = await self.session.list_tools()
                    self.available_tools = tools_response.tools
                    return self.available_tools
                except:
                    pass
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a specific tool on the MCP server"""
        if not self.session:
            if not await self.connect_with_retry():
                return {"status": "error", "message": "Failed to connect to MCP server"}
        
        if arguments is None:
            arguments = {}
        
        try:
            logger.debug(f"Calling tool {tool_name} with arguments: {arguments}")
            
            # Execute tool via MCP protocol
            result = await self.session.call_tool(
                name=tool_name,
                arguments=arguments
            )
            
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
                
                logger.debug(f"Tool {tool_name} executed successfully")
                return {
                    "status": "success",
                    "data": result_data
                }
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            
            # Try to reconnect and retry once
            if "connection" in str(e).lower() or "session" in str(e).lower():
                logger.info("Connection error detected, attempting to reconnect...")
                if await self.connect_with_retry():
                    try:
                        return await self.call_tool(tool_name, arguments)
                    except:
                        pass
            
            return {"status": "error", "message": str(e)}
    
    async def perform_login(self) -> Dict[str, Any]:
        """Perform authentication login using stored credentials"""
        logger.info("Attempting to perform login via MCP server tool")
        try:
            result = await self.call_tool("perform_login")
            if result.get("status") == "success":
                logger.info("✅ Login successful")
                return {"status": "success", "message": "Login successful"}
            else:
                error_message = result.get("message", "Unknown error during login")
                logger.error(f"❌ Login failed: {error_message}")
                return {"status": "error", "message": error_message}
        except Exception as e:
            logger.error(f"Exception during login: {e}")
            return {"status": "error", "message": str(e)}
    
    async def plan_tool_execution(self, user_query: str) -> List[ToolCall]:
        """Use LLM to plan which tools to execute for a user query"""
        if not self.openai_client:
            logger.warning("No LLM client available - using simple fallback planning")
            return self._fallback_planning(user_query)
        
        if not self.available_tools:
            await self.list_tools()
        
        if not self.available_tools:
            logger.warning("No tools available for planning")
            return []
        
        # Build tools description for LLM
        tools_description = self._build_tools_description()
        
        system_prompt = f"""You are an AI assistant that helps users interact with APIs through MCP tools.

Available tools:
{tools_description}

Plan which tools to execute for the user's query. Return a JSON array with this structure:
[
  {{
    "tool_name": "exact_tool_name",
    "arguments": {{"param": "value"}},
    "reason": "why this tool is needed"
  }}
]

Maximum {getattr(config, 'MAX_TOOL_EXECUTIONS', 5)} tool calls allowed."""

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
                
                return tool_calls[:getattr(config, 'MAX_TOOL_EXECUTIONS', 5)]
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                return self._fallback_planning(user_query)
                
        except Exception as e:
            logger.error(f"LLM planning failed: {e}")
            return self._fallback_planning(user_query)
    
    def _fallback_planning(self, user_query: str) -> List[ToolCall]:
        """Simple fallback planning when LLM is not available"""
        # Simple keyword-based tool selection
        query_lower = user_query.lower()
        tool_calls = []
        
        # Map keywords to likely tools
        keyword_mappings = {
            "payment": ["get_payments", "list_payments"],
            "account": ["get_accounts", "account_info"],
            "balance": ["get_balance", "account_balance"],
            "transaction": ["get_transactions", "transaction_history"]
        }
        
        for keyword, tool_names in keyword_mappings.items():
            if keyword in query_lower:
                for tool_name in tool_names:
                    # Check if tool exists
                    if any(tool.name == tool_name for tool in self.available_tools):
                        tool_calls.append(ToolCall(
                            tool_name=tool_name,
                            arguments={},
                            reason=f"Detected keyword '{keyword}' in query"
                        ))
                        break
        
        # If no specific tools found, try first available tool
        if not tool_calls and self.available_tools:
            first_tool = self.available_tools[0]
            tool_calls.append(ToolCall(
                tool_name=first_tool.name,
                arguments={},
                reason="Fallback: using first available tool"
            ))
        
        return tool_calls[:2]  # Limit fallback planning
    
    def _build_tools_description(self) -> str:
        """Build a detailed description of available tools for LLM"""
        if not self.available_tools:
            return "No tools available"
        
        descriptions = []
        for tool in self.available_tools:
            desc = f"- {tool.name}: {tool.description}"
            
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
        """Execute a plan of tool calls"""
        results = []
        
        for i, tool_call in enumerate(tool_calls, 1):
            logger.info(f"Executing tool {i}/{len(tool_calls)}: {tool_call.tool_name}")
            
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
        """Generate a natural language summary of the results"""
        if not tool_results:
            return "No tools were executed to gather information for your request."
        
        # Simple fallback summary if no LLM
        if not self.openai_client:
            return self._generate_simple_summary(tool_results, tool_calls)
        
        # Build results summary
        results_summary = []
        for result, tool_call in zip(tool_results, tool_calls):
            if result.success:
                result_preview = str(result.result)[:200] + "..." if len(str(result.result)) > 200 else str(result.result)
                results_summary.append(f"✅ {result.tool_name}: {result_preview}")
            else:
                results_summary.append(f"❌ {result.tool_name}: {result.error}")
        
        results_text = "\n".join(results_summary)
        
        system_prompt = """Generate a helpful summary of the API results for the user's query. Be specific with data and clear about any errors."""

        try:
            response = self.openai_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {user_query}\n\nResults:\n{results_text}"}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return self._generate_simple_summary(tool_results, tool_calls)
    
    def _generate_simple_summary(self, tool_results: List[ToolResult], tool_calls: List[ToolCall]) -> str:
        """Generate simple summary without LLM"""
        successful = [r for r in tool_results if r.success]
        failed = [r for r in tool_results if not r.success]
        
        summary_parts = []
        
        if successful:
            summary_parts.append(f"✅ Successfully executed {len(successful)} tool(s):")
            for result in successful[:3]:  # Show first 3 results
                data_preview = str(result.result)[:100] + "..." if result.result and len(str(result.result)) > 100 else str(result.result)
                summary_parts.append(f"  • {result.tool_name}: {data_preview}")
        
        if failed:
            summary_parts.append(f"❌ Failed to execute {len(failed)} tool(s):")
            for result in failed:
                summary_parts.append(f"  • {result.tool_name}: {result.error}")
        
        return "\n".join(summary_parts) if summary_parts else "No results to display."
    
    async def process_message(self, message: str) -> str:
        """Process a user message and return a response"""
        try:
            # Ensure we have tools available
            if not self.available_tools:
                await self.list_tools()
            
            # Plan execution
            tool_calls = await self.plan_tool_execution(message)
            
            if not tool_calls:
                return "I couldn't determine which tools to use for your request. Please try rephrasing your question."
            
            # Execute tools
            tool_results = await self.execute_tool_plan(tool_calls)
            
            # Generate summary
            summary = await self.generate_summary(message, tool_results, tool_calls)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a user query end-to-end"""
        logger.info(f"Processing query: {user_query}")
        
        try:
            # Plan tool execution
            tool_calls = await self.plan_tool_execution(user_query)
            
            if not tool_calls:
                return {
                    "status": "error",
                    "message": "Could not plan tool execution for this query",
                    "plan": [],
                    "results": [],
                    "summary": "I couldn't determine which tools to use for your request."
                }
            
            # Execute tools
            tool_results = await self.execute_tool_plan(tool_calls)
            
            # Generate summary
            summary = await self.generate_summary(user_query, tool_results, tool_calls)
            
            return {
                "status": "success",
                "plan": [{"tool_name": tc.tool_name, "arguments": tc.arguments, "reason": tc.reason} for tc in tool_calls],
                "results": [{"tool_name": tr.tool_name, "success": tr.success, "result": tr.result, "error": tr.error} for tr in tool_results],
                "summary": summary
            }
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "status": "error",
                "message": str(e),
                "plan": [],
                "results": [],
                "summary": f"I encountered an error while processing your request: {str(e)}"
            }


async def main():
    """Example usage of MCP Client"""
    client = MCPClient()
    
    try:
        # Test connection
        success = await client.connect_with_retry()
        if not success:
            print("❌ Failed to connect to MCP server")
            return
        
        # List available tools
        tools = await client.list_tools()
        print(f"✅ Available tools: {[tool.name for tool in tools]}")
        
        # Test simple query
        result = await client.process_query("Show me available information")
        print(f"✅ Query result: {result['summary']}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
