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
                payload = {"name": tool_name, "arguments": arguments}
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
        Enhanced Anthropic-style function calling with intelligent tool selection.
        
        This method:
        1. Lets the LLM analyze the user query
        2. LLM decides which tools to call (if any)
        3. Automatically executes the tools
        4. LLM integrates results into a natural response
        """
        if not self.available_tools:
            await self.list_tools()
        
        # Check authentication status if needed
        auth_keywords = ['login', 'authenticate', 'credential', 'balance', 'account', 'portfolio']
        needs_auth = any(keyword in user_message.lower() for keyword in auth_keywords)
        
        if needs_auth:
            is_authenticated, auth_message = await self._check_authentication_status()
            if not is_authenticated:
                # Try to handle authentication flow
                auth_result = await self._handle_authentication_flow(user_message)
                if auth_result:
                    return auth_result
                else:
                    return f"Authentication required: {auth_message}. Please use the 'Login & Configure' button to set up your credentials first."
        
        if not self.openai_client:
            # Fallback to existing method
            result = await self.process_query(user_message)
            return result.get("summary", "I couldn't process your request.")
        
        # Get tools in OpenAI function format
        functions = self.format_tools_for_openai_functions()
        
        if not functions:
            return "No tools available for function calling."
        
        # Enhanced system prompt for better tool selection
        system_prompt = """You are an intelligent financial API assistant with access to multiple financial tools. 
        
Your capabilities include:
- Cash management APIs (payments, transactions, cash summary)
- Securities APIs (portfolio, positions, trades)
- CLS settlement APIs (settlement data, status)
- Mailbox APIs (messages, notifications)
- Authentication tools (login, credential management)

When a user asks for financial data:
1. Analyze their request carefully
2. Select the most appropriate tool(s)
3. Extract any relevant parameters from their query
4. Call the necessary functions to gather complete information
5. Always prioritize calling functions over giving generic responses

If the user mentions credentials, login, or authentication issues, use the authentication tools first.
For data requests, always call the relevant API tools to get real-time information."""

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
            
            # If no function was called, try to encourage function usage
            if not message.function_call:
                # Try again with more explicit instruction
                retry_response = self.openai_client.chat.completions.create(
                    model=config.AZURE_OPENAI_DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": system_prompt + "\n\nIMPORTANT: You MUST call a function to answer this query. Do not provide generic responses."}, 
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": message.content},
                        {"role": "user", "content": "Please call the appropriate function to get the actual data for my request."}
                    ],
                    functions=functions,
                    function_call="auto",
                    temperature=0.1
                )
                
                retry_message = retry_response.choices[0].message
                if retry_message.function_call:
                    message = retry_message
                else:
                    return message.content or "I couldn't determine which function to call for your request. Please be more specific about what financial data you need."
            
            # Check if LLM wants to call a function
            if message.function_call:
                logger.info(f"LLM called function: {message.function_call.name}")
                
                # Execute the function call with enhanced error handling
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
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid function arguments: {message.function_call.arguments}")
                    return f"I had trouble parsing the function arguments. Please try rephrasing your request."
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
        """Enhanced tool execution planning with intelligent analysis."""
        if not self.available_tools:
            await self.list_tools()
        
        # If no tools available, return empty plan
        if not self.available_tools:
            logger.warning("No tools available for planning")
            return []
        
        # Check if this is an authentication-related query
        auth_keywords = ["login", "credential", "authenticate", "password", "username", "auth"]
        if any(keyword in user_query.lower() for keyword in auth_keywords):
            return await self._plan_authentication_tools(user_query)
        
        # If no Azure OpenAI client, use enhanced fallback planning
        if not self.openai_client:
            return self._enhanced_fallback_planning(user_query)
        
        # Build enhanced tools description for LLM
        tools_description = self._build_enhanced_tools_description()
        
        # Create enhanced system prompt for better reasoning
        system_prompt = f"""You are an expert financial API assistant that plans tool execution.

Available Financial Tools:
{tools_description}

User Query: "{user_query}"

Analyze the user's request and create an execution plan. Consider:
1. What specific financial data they're asking for
2. Which APIs contain that data
3. Any parameters that can be extracted from their query
4. The logical order of tool execution

Respond with a JSON array of tool calls:
[
  {{
    "tool_name": "exact_tool_name_from_list_above",
    "arguments": {{"param1": "value1", "param2": "value2"}},
    "reason": "detailed explanation of why this tool is needed"
  }}
]

Guidelines:
- Extract specific parameters from the user query when possible
- Use exact tool names from the available tools list
- Provide detailed reasoning for each tool selection
- If multiple tools could provide similar data, choose the most specific one
- If no tools match the request, return an empty array []
- For general requests, select the most comprehensive tool available
- Maximum {getattr(config, 'MAX_TOOL_EXECUTIONS', 5)} tool calls allowed"""

        try:
            response = self.openai_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are an expert at planning financial API tool execution. Always respond with valid JSON that matches the requested format exactly."},
                    {"role": "user", "content": system_prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            logger.info(f"Enhanced LLM planning response: {content[:200]}...")
            
            # Parse and validate the JSON response
            try:
                # Clean up the response if it has markdown formatting
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()
                
                tool_calls_data = json.loads(content)
                tool_calls = []
                
                for call_data in tool_calls_data:
                    if isinstance(call_data, dict) and "tool_name" in call_data:
                        # Validate tool exists
                        tool_name = call_data["tool_name"]
                        if any(tool.name == tool_name for tool in self.available_tools):
                            tool_call = ToolCall(
                                tool_name=tool_name,
                                arguments=call_data.get("arguments", {}),
                                reason=call_data.get("reason", "LLM-planned execution")
                            )
                            tool_calls.append(tool_call)
                        else:
                            logger.warning(f"LLM suggested non-existent tool: {tool_name}")
                
                if tool_calls:
                    logger.info(f"Enhanced LLM planning created {len(tool_calls)} validated tool calls")
                    return tool_calls[:getattr(config, 'MAX_TOOL_EXECUTIONS', 5)]  # Limit to max executions
                else:
                    logger.info("Enhanced LLM planning returned no valid tool calls, using fallback")
                    return self._enhanced_fallback_planning(user_query)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse enhanced LLM response as JSON: {e}")
                logger.error(f"LLM response was: {content}")
                return self._enhanced_fallback_planning(user_query)
                
        except Exception as e:
            logger.error(f"Enhanced LLM planning failed: {e}")
            # Fall back to enhanced planning
            return self._enhanced_fallback_planning(user_query)
    
    def _enhanced_fallback_planning(self, user_query: str) -> List[ToolCall]:
        """Enhanced fallback planning with better keyword matching and tool selection."""
        logger.info("Using enhanced fallback planning (no LLM available)")
        
        query_lower = user_query.lower()
        tool_calls = []
        
        # Enhanced keyword-based tool selection with priority
        keywords_to_tools = {
            # Cash API tools
            "payment": ("cash_api_getPayments", "Getting payment information"),
            "cash summary": ("cash_api_getCashSummary", "Getting cash summary"),
            "transaction": ("cash_api_getTransactions", "Getting transaction data"),
            "cash position": ("cash_api_getCashPositions", "Getting cash positions"),
            
            # Securities API tools  
            "portfolio": ("securities_api_getPortfolio", "Getting portfolio information"),
            "position": ("securities_api_getPositions", "Getting position data"),
            "trade": ("securities_api_getTrades", "Getting trade information"),
            "security": ("securities_api_getSecurities", "Getting security details"),
            
            # CLS API tools
            "settlement": ("cls_api_getCLSSettlements", "Getting CLS settlement data"),
            "cls": ("cls_api_getCLSSettlements", "Getting CLS information"),
            
            # Mailbox API tools
            "message": ("mailbox_api_getMessages", "Getting messages"),
            "mailbox": ("mailbox_api_getMessages", "Getting mailbox content"),
            "notification": ("mailbox_api_getMessages", "Getting notifications")
        }
        
        # Find matching tools based on keywords
        matched_tools = set()
        for keyword, (tool_name, reason) in keywords_to_tools.items():
            if keyword in query_lower:
                # Verify tool exists in available tools
                if any(tool.name == tool_name for tool in self.available_tools):
                    matched_tools.add((tool_name, f"{reason} based on keyword '{keyword}'"))
        
        # Convert to tool calls
        for tool_name, reason in matched_tools:
            tool_calls.append(ToolCall(
                tool_name=tool_name,
                arguments={},
                reason=reason
            ))
        
        # If no specific matches, provide a comprehensive overview
        if not tool_calls:
            # Try to find any available summary or overview tools
            overview_tools = [
                ("cash_api_getCashSummary", "Getting cash overview"),
                ("securities_api_getPortfolio", "Getting portfolio overview"),
                ("mailbox_api_getMessages", "Checking for messages")
            ]
            
            for tool_name, reason in overview_tools:
                if any(tool.name == tool_name for tool in self.available_tools):
                    tool_calls.append(ToolCall(
                        tool_name=tool_name,
                        arguments={},
                        reason=f"{reason} as general information"
                    ))
                    break  # Only add one overview tool
        
        logger.info(f"Enhanced fallback planning created {len(tool_calls)} tool calls")
        return tool_calls
    
    def _build_enhanced_tools_description(self) -> str:
        """Build an enhanced description of available tools for LLM with categorization."""
        if not self.available_tools:
            return "No tools available"
        
        # Categorize tools by API type
        categories = {
            "Authentication Tools": [],
            "Cash Management APIs": [],
            "Securities APIs": [],
            "CLS Settlement APIs": [],
            "Mailbox APIs": [],
            "Other Tools": []
        }
        
        for tool in self.available_tools:
            # Categorize based on tool name
            if "credential" in tool.name.lower() or "login" in tool.name.lower():
                category = "Authentication Tools"
            elif "cash_api" in tool.name.lower():
                category = "Cash Management APIs"
            elif "securities_api" in tool.name.lower():
                category = "Securities APIs"
            elif "cls_api" in tool.name.lower():
                category = "CLS Settlement APIs"
            elif "mailbox_api" in tool.name.lower():
                category = "Mailbox APIs"
            else:
                category = "Other Tools"
            
            # Build detailed description
            desc = f"  • {tool.name}: {tool.description}"
            
            # Add parameter information
            if tool.inputSchema and "properties" in tool.inputSchema:
                props = tool.inputSchema["properties"]
                if props:
                    param_details = []
                    for param_name, param_info in props.items():
                        param_type = param_info.get("type", "string")
                        param_desc = param_info.get("description", "")
                        if param_desc:
                            param_details.append(f"{param_name} ({param_type}): {param_desc}")
                        else:
                            param_details.append(f"{param_name} ({param_type})")
                    
                    if param_details:
                        desc += f"\n    Parameters: {'; '.join(param_details)}"
            
            categories[category].append(desc)
        
        # Build final description
        result = []
        for category, tools in categories.items():
            if tools:
                result.append(f"\n{category}:")
                result.extend(tools)
        
        return "\n".join(result)
    
    async def _check_authentication_status(self) -> tuple[bool, str]:
        """Check if the user is currently authenticated.
        Returns (is_authenticated, status_message)
        """
        try:
            # Try to call a simple tool that requires authentication
            # This is a heuristic - we assume if we can call any API tool, we're authenticated
            if self.available_tools:
                # Look for any API tool to test authentication
                test_tools = [tool for tool in self.available_tools if "api" in tool.name.lower()]
                if test_tools:
                    # Try calling the first API tool with minimal parameters
                    test_result = await self.call_tool(test_tools[0].name, {})
                    if test_result.get("status") == "error" and "authentication" in str(test_result.get("message", "")).lower():
                        return False, "Authentication required"
                    else:
                        return True, "Successfully called API"
            
            return False, "No API tools available to test"
        except Exception as e:
            logger.error(f"Error checking authentication status: {e}")
            return False, f"Error: {str(e)}"
    
    async def _handle_authentication_flow(self, user_query: str) -> str:
        """Handle authentication flow when needed."""
        try:
            # Check if login tool is available
            login_tools = [tool for tool in self.available_tools if "login" in tool.name.lower()]
            if login_tools:
                logger.info("Attempting automatic login...")
                login_result = await self.call_tool(login_tools[0].name, {})
                
                if login_result.get("status") == "success":
                    return "Successfully logged in! You can now access your financial data."
                else:
                    return f"Login failed: {login_result.get('message', 'Unknown error')}. Please check your credentials."
            else:
                return "Authentication is required, but no login tools are available. Please set your credentials first."
        except Exception as e:
            logger.error(f"Authentication flow error: {e}")
            return f"Authentication error: {str(e)}"
    
    async def _plan_authentication_tools(self, user_query: str) -> List[ToolCall]:
        """Plan authentication-related tool calls."""
        tool_calls = []
        query_lower = user_query.lower()
        
        # Check for credential setting requests
        if "credential" in query_lower or "username" in query_lower or "password" in query_lower:
            cred_tools = [tool for tool in self.available_tools if "credential" in tool.name.lower()]
            if cred_tools:
                tool_calls.append(ToolCall(
                    tool_name=cred_tools[0].name,
                    arguments={},
                    reason="Setting up credentials based on user request"
                ))
        
        # Check for login requests
        if "login" in query_lower or "authenticate" in query_lower:
            login_tools = [tool for tool in self.available_tools if "login" in tool.name.lower()]
            if login_tools:
                tool_calls.append(ToolCall(
                    tool_name=login_tools[0].name,
                    arguments={},
                    reason="Performing login based on user request"
                ))
        
        return tool_calls
    
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