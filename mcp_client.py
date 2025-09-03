#!/usr/bin/env python3
"""
MCP Client - Production HTTP-Only Implementation
Optimized MCP client for production use:
- HTTP-only communication with MCP server
- Synchronous OpenAI client for better reliability
- Preserved authentication and login logic
- Streamlined tool execution flow
"""

import logging
import json
import os
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from tool_categorizer import DynamicToolCategorizer

# Tool type definition
@dataclass
class Tool:
    name: str
    description: str
    inputSchema: Dict[str, Any]

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
    """Production MCP Client with HTTP-only communication"""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8000", 
                 openai_api_key: str = None, 
                 openai_model: str = "gpt-4o"):
        self.server_url = mcp_server_url
        self.available_tools: List[Tool] = []
        self.session = requests.Session()
        
        # Initialize OpenAI client - assume GPT-4o is available
        self.openai_client = self._create_openai_client()
        self.model = openai_model
        
        logging.info(f"Initialized MCP Client connecting to {mcp_server_url}")
        
        # Cache for tools and results
        self.tool_results: Dict[str, Any] = {}
        
        # Initialize dynamic tool categorizer
        self.tool_categorizer = DynamicToolCategorizer()
        

    
    def _create_openai_client(self) -> AsyncAzureOpenAI:
        """Create Azure OpenAI client with azure_ad_token_provider."""
        azure_endpoint = getattr(config, 'AZURE_OPENAI_ENDPOINT', os.getenv("AZURE_OPENAI_ENDPOINT"))
        
        # Assume GPT-4o client is available - no fallback
        try:
            # Create Azure AD token provider
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            
            client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint or "https://your-resource.openai.azure.com/",
                azure_ad_token_provider=token_provider,
                api_version="2024-02-01"
            )
            logging.info("✅ Azure OpenAI client created with Azure AD authentication")
            return client
        except Exception as e:
            logging.error(f"Failed to create Azure OpenAI client: {e}")
            raise e
    

    
    def connect(self):
         """Connect to MCP server via HTTP."""
         try:
             response = self.session.get(f"{self.server_url}/health")
             if response.status_code == 200:
                 logging.info(f"✅ Connected to HTTP MCP server at {self.server_url}")
                 return True
             else:
                 raise Exception(f"Server health check failed: {response.status_code}")
         except Exception as e:
             logging.error(f"❌ Failed to connect to HTTP MCP server: {e}")
             return False
    
    def disconnect(self):
         """Disconnect from the HTTP MCP server."""
         logging.info("Disconnected from HTTP MCP server")
         if self.session:
             self.session.close()
    
    def close(self):
        """Close the MCP client connection. Alias for disconnect."""
        self.disconnect()
    
    def list_tools(self) -> List[Tool]:
         """Get list of available tools from HTTP MCP server."""
         try:
             response = self.session.get(f"{self.server_url}/tools")
             if response.status_code == 200:
                 data = response.json()
                 tools = []
                 for tool_data in data.get("tools", []):
                     tool = Tool(
                         name=tool_data["name"],
                         description=tool_data["description"],
                         inputSchema=tool_data.get("inputSchema", {"type": "object"})
                     )
                     tools.append(tool)
                 self.available_tools = tools
                 logging.info(f"✅ Retrieved {len(tools)} tools from HTTP MCP server")
                 return tools
             else:
                 raise Exception(f"HTTP {response.status_code}")
         except Exception as e:
             logging.error(f"Error listing tools: {e}")
             return []
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
         """Call a tool on the MCP server."""
         if arguments is None:
             arguments = {}
             
         try:
             logging.info(f"Calling tool: {tool_name} with arguments: {arguments}")
             
             payload = {"name": tool_name, "arguments": arguments}
             response = self.session.post(f"{self.server_url}/call_tool", json=payload)
             
             if response.status_code == 200:
                 result = response.json()
                 return {"status": "success", "data": result}
             else:
                 return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
                 
         except Exception as e:
             logging.error(f"Error calling tool {tool_name}: {e}")
             return {"status": "error", "message": str(e)}

    def perform_login(self) -> Dict[str, Any]:
        """Call the perform_login tool on the MCP server."""
        logger.info("Attempting to perform login via MCP server tool.")
        try:
            result = self.call_tool("perform_login")
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
    
    def set_credentials(self, username: str = None, password: str = None, api_key: str = None) -> Dict[str, Any]:
        """Set credentials using the set_credentials tool."""
        credentials = {}
        if username:
            credentials["username"] = username
        if password:
            credentials["password"] = password
        if api_key:
            credentials["api_key"] = api_key
            
        return self.call_tool("set_credentials", credentials)
    

    



    async def plan_tool_execution(self, user_query: str) -> List[ToolCall]:
        """Enhanced tool execution planning with intelligent analysis."""
        if not self.available_tools:
            self.list_tools()
        
        # If no tools available, return empty plan
        if not self.available_tools:
            logger.warning("No tools available for planning")
            return []
        
        # Check if this is an authentication-related query
        auth_keywords = ["login", "credential", "authenticate", "password", "username", "auth"]
        if any(keyword in user_query.lower() for keyword in auth_keywords):
            return self._plan_authentication_tools(user_query)
        
        # Assume OpenAI client is always available - no fallback planning needed
        
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
            # Generate summary using Azure OpenAI client
            return await self._generate_ai_summary(user_query, tool_results, tool_calls)
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return self._generate_simple_summary(user_query, tool_results)
    
    async def _generate_ai_summary(self, user_query: str, tool_results: List[ToolResult], tool_calls: List[ToolCall]) -> str:
        """Generate summary using Azure OpenAI client."""
        try:
            # Prepare messages for OpenAI API
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful financial assistant. Provide clear, concise summaries of financial data and operations."
                },
                {
                    "role": "user",
                    "content": f"User query: {user_query}\n\nTool results: {json.dumps([result.to_dict() for result in tool_results], indent=2)}\n\nPlease provide a helpful summary."
                }
            ]
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error in AI summary generation: {e}")
            return self._generate_simple_summary(user_query, tool_results)
    

    
    def _old_generate_summary_with_llm(self, user_query: str, tool_results: List[ToolResult], tool_calls: List[ToolCall]) -> str:
        """Original LLM-based summary generation (kept for reference)."""
        try:
            # This would be the actual OpenAI API call
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
                    logger.info("Enhanced LLM planning returned no valid tool calls")
                    return []
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse enhanced LLM response as JSON: {e}")
                logger.error(f"LLM response was: {content}")
                return []
                
        except Exception as e:
            logger.error(f"Enhanced LLM planning failed: {e}")
            return []
    

    
    def _build_enhanced_tools_description(self) -> str:
        """Build an enhanced description of available tools for LLM with dynamic categorization."""
        if not self.available_tools:
            return "No tools available"
        
        # Convert MCP tools to dict format for categorizer
        tools_dict = []
        for tool in self.available_tools:
            tools_dict.append({
                'name': tool.name,
                'description': tool.description,
                'inputSchema': tool.inputSchema
            })
        
        # Use dynamic tool categorizer
        categorized = self.tool_categorizer.categorize_tools(tools_dict)
        
        # Build final description
        result = []
        # Sort categories by priority
        sorted_categories = sorted(
            categorized.items(),
            key=lambda x: self.tool_categorizer.get_category_info(x[0]).priority,
            reverse=True
        )
        
        for category_id, tools in sorted_categories:
            if tools:
                category_info = self.tool_categorizer.get_category_info(category_id)
                result.append(f"\n{category_info.name}:")
                result.append(f"  {category_info.description}")
                
                for tool in tools:
                    # Build detailed description
                    desc = f"  • {tool['name']}: {tool['description']}"
                    
                    # Add parameter information
                    input_schema = tool.get('inputSchema', {})
                    if input_schema and "properties" in input_schema:
                        props = input_schema["properties"]
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
                    
                    result.append(desc)
        
        return "\n".join(result)
    
    def _check_authentication_status(self) -> tuple[bool, str]:
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
                    test_result = self.call_tool(test_tools[0].name, {})
                    if test_result.get("status") == "error" and "authentication" in str(test_result.get("message", "")).lower():
                        return False, "Authentication required"
                    else:
                        return True, "Successfully called API"
            
            return False, "No API tools available to test"
        except Exception as e:
            logger.error(f"Error checking authentication status: {e}")
            return False, f"Error: {str(e)}"
    
    def _handle_authentication_flow(self, user_query: str) -> str:
        """Handle authentication flow when needed."""
        try:
            # Check if login tool is available
            login_tools = [tool for tool in self.available_tools if "login" in tool.name.lower()]
            if login_tools:
                logger.info("Attempting automatic login...")
                login_result = self.call_tool(login_tools[0].name, {})
                
                if login_result.get("status") == "success":
                    return "Successfully logged in! You can now access your financial data."
                else:
                    return f"Login failed: {login_result.get('message', 'Unknown error')}. Please check your credentials."
            else:
                return "Authentication is required, but no login tools are available. Please set your credentials first."
        except Exception as e:
            logger.error(f"Authentication flow error: {e}")
            return f"Authentication error: {str(e)}"
    
    def _plan_authentication_tools(self, user_query: str) -> List[ToolCall]:
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

    async def chat_with_mcp_planning(self, user_message: str) -> str:
        """MCP Planning approach: LLM is the navigator, we are the driver.
        
        This method:
        1. LLM analyzes the query and creates an execution plan
        2. We execute the planned tools step by step
        3. LLM synthesizes the results into a natural response
        """
        if not self.available_tools:
            self.list_tools()
        
        # Check authentication status if needed
        auth_keywords = ['login', 'authenticate', 'credential', 'balance', 'account', 'portfolio']
        needs_auth = any(keyword in user_message.lower() for keyword in auth_keywords)
        
        if needs_auth:
            is_authenticated, auth_message = self._check_authentication_status()
            if not is_authenticated:
                # Try to handle authentication flow
                auth_result = self._handle_authentication_flow(user_message)
                if auth_result:
                    return auth_result
                else:
                    return f"Authentication required: {auth_message}. Please use the 'Login & Configure' button to set up your credentials first."
        
        # Step 1: LLM creates execution plan (Navigator role)
        logger.info(f"Planning tool execution for query: {user_message}")
        tool_plan = await self.plan_tool_execution(user_message)
        
        if not tool_plan:
            # If no tools planned, provide a direct response
            if self.openai_client:
                return await self._generate_direct_response(user_message)
            else:
                return "I couldn't find any relevant tools to help with your request."
        
        # Step 2: We execute the plan (Driver role)
        logger.info(f"Executing {len(tool_plan)} planned tools")
        tool_results = self.execute_tool_plan(tool_plan)
        
        # Step 3: LLM synthesizes results into natural response
        if self.openai_client:
            return await self._synthesize_results(user_message, tool_plan, tool_results)
        else:
            # Fallback: format results directly
            return self._format_results_simple(user_message, tool_results)

    async def _generate_direct_response(self, user_message: str) -> str:
        """Generate a direct response when no tools are needed."""
        try:
            response = await self.openai_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful financial assistant. Provide a direct, informative response to the user's query."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating direct response: {e}")
            return "I'm sorry, I couldn't process your request at the moment."

    async def _synthesize_results(self, user_message: str, tool_plan: List[ToolCall], tool_results: List[ToolResult]) -> str:
        """Synthesize tool results into a natural response using LLM."""
        try:
            # Prepare context about executed tools and their results
            execution_context = []
            for tool_call, result in zip(tool_plan, tool_results):
                execution_context.append({
                    "tool": tool_call.tool_name,
                    "reason": tool_call.reason,
                    "arguments": tool_call.arguments,
                    "success": result.success,
                    "result": result.result if result.success else result.error
                })
            
            context_text = json.dumps(execution_context, indent=2)
            
            response = await self.openai_client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a financial assistant that synthesizes API results into natural, helpful responses.
                        
Your task:
1. Analyze the tool execution results provided
2. Create a natural, conversational response that directly answers the user's question
3. Present data in a clear, organized way
4. If there were errors, explain them helpfully
5. Be concise but informative
                        """
                    },
                    {
                        "role": "user",
                        "content": f"Original question: {user_message}\n\nTool execution results:\n{context_text}\n\nPlease provide a natural response based on these results."
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error synthesizing results: {e}")
            return self._format_results_fallback(user_message, tool_results)

    def _format_results_simple(self, user_message: str, tool_results: List[ToolResult]) -> str:
        """Simple method to format results when LLM processing fails."""
        if not tool_results:
            return "No results were obtained from the tools."
        
        response_parts = [f"Results for: {user_message}\n"]
        
        for i, result in enumerate(tool_results, 1):
            if result.success:
                response_parts.append(f"✅ {result.tool_name}:")
                if isinstance(result.result, dict):
                    # Format dict results nicely
                    for key, value in result.result.items():
                        response_parts.append(f"  • {key}: {value}")
                else:
                    response_parts.append(f"  {result.result}")
            else:
                response_parts.append(f"❌ {result.tool_name}: {result.error}")
            
            if i < len(tool_results):
                response_parts.append("")
        
        return "\n".join(response_parts)

    async def process_message(self, user_message: str) -> str:
        """Process a user message with MCP planning approach.
        LLM acts as navigator, we are the driver executing the plan.
        """
        try:
            return await self.chat_with_mcp_planning(user_message)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Error processing your request: {str(e)}"



    def execute_tool_plan(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute a plan of tool calls with detailed logging."""
        results = []
        
        for i, tool_call in enumerate(tool_calls, 1):
            logger.info(f"Executing tool {i}/{len(tool_calls)}: {tool_call.tool_name}")
            logger.info(f"Reason: {tool_call.reason}")
            logger.info(f"Arguments: {tool_call.arguments}")
            
            try:
                result = self.call_tool(tool_call.tool_name, tool_call.arguments)
                
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
        """Generate a natural language summary of the results using Azure OpenAI."""
        if not tool_results:
            return "No tools were executed to gather information for your request."
        
        # Use real Azure OpenAI client
        try:
            return await self._generate_ai_summary(user_query, tool_results, tool_calls)
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
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
    
    def _generate_simple_summary_fallback(self, user_query: str, tool_results: List[dict], tool_calls: List[dict]) -> str:
        """Generate a simple summary without OpenAI when using dict format."""
        summary_parts = [f"Processed query: {user_query}"]
        
        if tool_calls:
            summary_parts.append(f"Executed {len(tool_calls)} tools:")
            for i, call in enumerate(tool_calls):
                tool_name = call.get('name', 'unknown')
                result = tool_results[i] if i < len(tool_results) else {}
                if result.get('success', False):
                    summary_parts.append(f"✅ {tool_name}: Success")
                else:
                    summary_parts.append(f"❌ {tool_name}: Failed")
        else:
            summary_parts.append("No tools were executed")
        
        return "\n".join(summary_parts)
    
    def process_message(self, message: str) -> str:
        """Process a user message and return a response."""
        result = self.process_query(message)
        if result["status"] == "success":
            return result["summary"]
        else:
            return f"Error: {result['message']}"

    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a user query end-to-end with enhanced reasoning."""
        logger.info(f"Processing query: {user_query}")
        
        try:
            # Ensure we're connected and have tools
            if not self.connect():
                return {
                    "status": "error",
                    "message": "Failed to connect to MCP server",
                    "summary": "I couldn't connect to the MCP server."
                }
            
            if not self.available_tools:
                self.list_tools()

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
            tool_results = self.execute_tool_plan(tool_calls)
            
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


def main():
    """Example usage of MCP Client - HTTP only."""
    print("MCP Client Test")
    print("===============")
    print()
    print("🔌 Using HTTP connection to MCP server")
    print("📋 Make sure to start the MCP server first:")
    print("   python mcp_server.py")
    print()
    
    # Create HTTP-only client
    client = MCPClient()
    
    try:
        print(f"\n🔗 Connecting to MCP server via HTTP...")
        if not client.connect():
            print("Failed to connect to MCP server")
            return
        
        print("📋 Listing available tools...")
        tools = client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools[:5]]}..." + (f" and {len(tools)-5} more" if len(tools) > 5 else ""))
        
        if tools:
            print("\n🧪 Testing tool execution...")
            result = client.process_query("Show me pending payments")
            print("Result:")
            print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
        print("\n💡 Make sure the MCP server is running:")
        print("   python mcp_server.py")
    finally:
        print("\n👋 Disconnected from MCP server")


if __name__ == "__main__":
    main()