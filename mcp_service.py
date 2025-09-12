#!/usr/bin/env python3
"""
MCP Service - Modern LLM Service Implementation
==============================================
Handles MCP tool calls and Azure OpenAI integration
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from mcp_client import MCPClient, PythonStdioTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_service.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("mcp_service")

class ModernLLMService:
    """Modern LLM Service that handles MCP tool calls and Azure OpenAI integration."""
    
    def __init__(self):
        self._initialized = False
        self._mcp_client = None
        self._azure_client = None
        self._tools = []
        
    async def initialize(self) -> bool:
        """Initialize the MCP service and Azure OpenAI client."""
        try:
            logger.info("[MCP_SERVICE] Initializing MCP service...")
            
            # Initialize Azure OpenAI client
            self._azure_client = AsyncAzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            
            # Initialize MCP client
            self._mcp_client = MCPClient(PythonStdioTransport())
            await self._mcp_client.connect()
            
            # Get available tools
            self._tools = await self._mcp_client.list_tools()
            
            self._initialized = True
            logger.info(f"[MCP_SERVICE] MCP service initialized with {len(self._tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"[MCP_SERVICE] Failed to initialize MCP service: {e}")
            return False
    
    async def process_message(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process a user message and return response with tool calls."""
        if not self._initialized:
            return {
                "response": "❌ MCP service not initialized",
                "tool_calls": [],
                "capabilities": {"descriptions": []}
            }
        
        try:
            logger.info(f"[MCP_SERVICE] Processing message: '{user_message[:100]}...'")
            
            # Build conversation context
            messages = self._build_conversation_context(user_message, conversation_history or [])
            
            # Call Azure OpenAI
            logger.info("[MCP_SERVICE] Calling Azure Openai...")
            response = await self._azure_client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                messages=messages,
                tools=self._tools,
                tool_choice="auto",
                temperature=0.1
            )
            
            logger.info("[MCP_SERVICE] Azure Openai response received")
            
            # Process response
            message = response.choices[0].message
            tool_calls = []
            
            if message.tool_calls:
                logger.info(f"[MCP_SERVICE] LLM requested {len(message.tool_calls)} tool calls")
                
                # Execute tool calls
                for i, tool_call in enumerate(message.tool_calls, 1):
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id
                    
                    logger.info(f"[MCP_SERVICE] Executing tool {i}/{len(message.tool_calls)}: {tool_name}")
                    logger.info(f"[MCP_SERVICE] Tool args: {tool_args}")
                    
                    try:
                        # Validate tool exists before calling
                        if not await self.validate_tool_exists(tool_name):
                            similar_tools = await self.suggest_similar_tools(tool_name)
                            error_msg = f"Tool '{tool_name}' not found. "
                            if similar_tools:
                                error_msg += f"Did you mean one of these: {', '.join(similar_tools)}?"
                            else:
                                error_msg += "Please check the available tools list."
                            
                            tool_calls.append({
                                "tool_name": tool_name,
                                "args": tool_args,
                                "success": False,
                                "error": error_msg,
                                "tool_call_id": tool_call_id
                            })
                            continue
                        
                        # Call MCP tool
                        result = await self._mcp_client.call_tool(tool_name, tool_args)
                        
                        tool_calls.append({
                            "tool_name": tool_name,
                            "args": tool_args,
                            "success": True,
                            "result": result,
                            "tool_call_id": tool_call_id
                        })
                        
                        logger.info(f"[MCP_SERVICE] Tool {tool_name} completed successfully")
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"[MCP_SERVICE] Tool call failed: {tool_name} - {error_msg}")
                        
                        # Provide more helpful error messages for common issues
                        if "unexpected_keyword_argument" in error_msg:
                            error_msg = f"Invalid parameter: {error_msg}. The tool '{tool_name}' doesn't accept the provided parameters. Please check the tool documentation for correct parameters."
                        elif "validation error" in error_msg:
                            error_msg = f"Parameter validation failed: {error_msg}. Please check parameter types and values according to the API specification."
                        elif "not found" in error_msg.lower():
                            error_msg = f"Tool not found: {tool_name}. This tool may not be available or the tool name may be incorrect."
                        elif "enum" in error_msg.lower():
                            error_msg = f"Invalid enum value: {error_msg}. Please check the allowed values for this parameter."
                        elif "required" in error_msg.lower():
                            error_msg = f"Missing required parameter: {error_msg}. Please provide all required parameters."
                        else:
                            error_msg = f"Tool execution failed: {error_msg}. Please check the tool parameters and try again."
                        
                        tool_calls.append({
                            "tool_name": tool_name,
                            "args": tool_args,
                            "success": False,
                            "error": error_msg,
                            "tool_call_id": tool_call_id
                        })
                
                # Get final response from LLM with tool results
                logger.info("[MCP_SERVICE] Getting final response from LLM...")
                final_messages = messages + [message] + self._build_tool_messages(tool_calls)
                
                try:
                    final_response = await self._azure_client.chat.completions.create(
                        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                        messages=final_messages,
                        temperature=0.1
                    )
                except Exception as e:
                    logger.error(f"[MCP_SERVICE] Error getting final response: {e}")
                    # If the final response fails, return the tool results directly
                    response_text = f"I executed {len(tool_calls)} tools. Here are the results:\n\n"
                    for tool_call in tool_calls:
                        if tool_call["success"]:
                            response_text += f"✅ {tool_call['tool_name']}: {json.dumps(tool_call['result'], indent=2)}\n\n"
                        else:
                            response_text += f"❌ {tool_call['tool_name']}: {tool_call['error']}\n\n"
                    return {
                        "response": response_text,
                        "tool_calls": tool_calls,
                        "capabilities": self._analyze_capabilities(tool_calls, user_message)
                    }
                
                response_text = final_response.choices[0].message.content
            else:
                response_text = message.content or "I don't have a response for that."
            
            # Analyze capabilities
            capabilities = self._analyze_capabilities(tool_calls, user_message)
            
            logger.info(f"[MCP_SERVICE] Getting final response: {len(response_text)} chars")
            
            return {
                "response": response_text,
                "tool_calls": tool_calls,
                "capabilities": capabilities
            }
            
        except Exception as e:
            logger.error(f"[MCP_SERVICE] Error processing message: {e}")
            return {
                "response": f"❌ Error processing message: {str(e)}",
                "tool_calls": [],
                "capabilities": {"descriptions": []}
            }
    
    def _build_conversation_context(self, user_message: str, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Build conversation context for Azure OpenAI."""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful API assistant that can work with any OpenAPI specification. You have access to various API tools and can help users with data retrieval, creation, modification, and deletion operations. Always use the available tools to provide accurate information and perform actions. If a tool call fails, provide helpful error messages and suggest alternatives when possible."
            }
        ]
        
        # Add conversation history
        for msg in conversation_history[-10:]:  # Keep last 10 messages
            if msg.get("role") in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        logger.info(f"[MCP_SERVICE] Building conversation context...")
        logger.info(f"[MCP_SERVICE] Adding {len(conversation_history)} conversation history messages")
        logger.info(f"[MCP_SERVICE] Total messages: {len(messages)}")
        
        return messages
    
    def _build_tool_messages(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Build tool result messages for Azure OpenAI."""
        tool_messages = []
        
        for tool_call in tool_calls:
            if tool_call["success"]:
                tool_messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_call["result"]),
                    "tool_call_id": tool_call.get("tool_call_id", "")
                })
            else:
                tool_messages.append({
                    "role": "tool",
                    "content": f"Error: {tool_call['error']}",
                    "tool_call_id": tool_call.get("tool_call_id", "")
                })
        
        return tool_messages
    
    def _analyze_capabilities(self, tool_calls: List[Dict[str, Any]], user_message: str) -> Dict[str, List[str]]:
        """Analyze what capabilities were demonstrated based on tool names and API patterns."""
        capabilities = []
        
        for tool_call in tool_calls:
            tool_name = tool_call["tool_name"]
            
            # Generic capability detection based on common API patterns
            if any(keyword in tool_name.lower() for keyword in ["payment", "cash", "transaction"]):
                capabilities.append("Payment processing and cash management")
            elif any(keyword in tool_name.lower() for keyword in ["settlement", "cls", "clearing"]):
                capabilities.append("Settlement and clearing operations")
            elif any(keyword in tool_name.lower() for keyword in ["trade", "portfolio", "position", "security"]):
                capabilities.append("Trading and portfolio management")
            elif any(keyword in tool_name.lower() for keyword in ["mailbox", "message", "notification", "alert"]):
                capabilities.append("Mailbox and notification management")
            elif any(keyword in tool_name.lower() for keyword in ["account", "balance", "user"]):
                capabilities.append("Account and user management")
            elif any(keyword in tool_name.lower() for keyword in ["get", "list", "retrieve"]):
                capabilities.append("Data retrieval and querying")
            elif any(keyword in tool_name.lower() for keyword in ["create", "add", "post"]):
                capabilities.append("Data creation and submission")
            elif any(keyword in tool_name.lower() for keyword in ["update", "modify", "put", "patch"]):
                capabilities.append("Data modification and updates")
            elif any(keyword in tool_name.lower() for keyword in ["delete", "remove", "cancel"]):
                capabilities.append("Data deletion and cancellation")
            else:
                # Generic capability based on tool name structure
                if "_" in tool_name:
                    parts = tool_name.split("_")
                    if len(parts) >= 2:
                        api_domain = parts[0] if parts[0] not in ["com", "api", "key"] else parts[1]
                        capabilities.append(f"{api_domain.title()} API operations")
                else:
                    capabilities.append("API operations")
        
        return {"descriptions": list(set(capabilities))}
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools."""
        if not self._initialized or not self._tools:
            return []
        
        return self._tools
    
    async def validate_tool_exists(self, tool_name: str) -> bool:
        """Check if a tool exists in the available tools list."""
        if not self._tools:
            return False
        
        return any(tool.get("function", {}).get("name") == tool_name for tool in self._tools)
    
    async def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool."""
        if not self._tools:
            return None
        
        for tool in self._tools:
            if tool.get("function", {}).get("name") == tool_name:
                return tool
        
        return None
    
    async def suggest_similar_tools(self, tool_name: str) -> List[str]:
        """Suggest similar tool names if a tool is not found."""
        if not self._tools:
            return []
        
        available_tools = [tool.get("function", {}).get("name") for tool in self._tools if tool.get("function", {}).get("name")]
        
        # Simple similarity matching
        similar_tools = []
        tool_name_lower = tool_name.lower()
        
        for available_tool in available_tools:
            if available_tool:
                # Check for partial matches
                if any(part in available_tool.lower() for part in tool_name_lower.split("_")):
                    similar_tools.append(available_tool)
                elif any(part in tool_name_lower for part in available_tool.lower().split("_")):
                    similar_tools.append(available_tool)
        
        return similar_tools[:5]  # Return top 5 suggestions
    
    async def get_api_summary(self) -> Dict[str, Any]:
        """Get a summary of all available APIs and their capabilities."""
        if not self._initialized or not self._tools:
            return {"apis": [], "total_tools": 0}
        
        # Group tools by API domain
        api_groups = {}
        for tool in self._tools:
            tool_name = tool.get("function", {}).get("name", "")
            if tool_name:
                # Extract API domain from tool name
                parts = tool_name.split("_")
                api_domain = parts[0] if parts else "unknown"
                
                if api_domain not in api_groups:
                    api_groups[api_domain] = {
                        "domain": api_domain,
                        "tools": [],
                        "capabilities": []
                    }
                
                api_groups[api_domain]["tools"].append(tool_name)
                
                # Determine capability based on tool name
                if any(keyword in tool_name.lower() for keyword in ["get", "list", "retrieve"]):
                    api_groups[api_domain]["capabilities"].append("Data Retrieval")
                elif any(keyword in tool_name.lower() for keyword in ["create", "add", "post"]):
                    api_groups[api_domain]["capabilities"].append("Data Creation")
                elif any(keyword in tool_name.lower() for keyword in ["update", "modify", "put", "patch"]):
                    api_groups[api_domain]["capabilities"].append("Data Modification")
                elif any(keyword in tool_name.lower() for keyword in ["delete", "remove", "cancel"]):
                    api_groups[api_domain]["capabilities"].append("Data Deletion")
        
        # Remove duplicates from capabilities
        for api_domain in api_groups:
            api_groups[api_domain]["capabilities"] = list(set(api_groups[api_domain]["capabilities"]))
        
        return {
            "apis": list(api_groups.values()),
            "total_tools": len(self._tools),
            "total_apis": len(api_groups)
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self._mcp_client:
            await self._mcp_client.disconnect()
        self._initialized = False