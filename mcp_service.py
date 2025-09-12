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
                            error_msg = f"Invalid parameter: {error_msg}. Please check the tool documentation for correct parameters."
                        elif "validation error" in error_msg:
                            error_msg = f"Parameter validation failed: {error_msg}. Please check parameter types and values."
                        elif "not found" in error_msg.lower():
                            error_msg = f"Tool not found: {tool_name}. This tool may not be available."
                        
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
                "content": "You are a helpful financial API assistant. You can help users with payments, settlements, trading, and mailbox operations. Use the available tools to provide accurate information and perform actions."
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
        """Analyze what capabilities were demonstrated."""
        capabilities = []
        
        for tool_call in tool_calls:
            tool_name = tool_call["tool_name"]
            
            if "payment" in tool_name.lower():
                capabilities.append("Payment processing and management")
            elif "settlement" in tool_name.lower():
                capabilities.append("Settlement and clearing operations")
            elif "trade" in tool_name.lower():
                capabilities.append("Trading and portfolio management")
            elif "mailbox" in tool_name.lower() or "message" in tool_name.lower():
                capabilities.append("Mailbox and notification management")
            elif "alert" in tool_name.lower():
                capabilities.append("Alert and monitoring systems")
            elif "account" in tool_name.lower():
                capabilities.append("Account and balance management")
        
        return {"descriptions": list(set(capabilities))}
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools."""
        if not self._initialized or not self._tools:
            return []
        
        return self._tools
    
    async def cleanup(self):
        """Cleanup resources."""
        if self._mcp_client:
            await self._mcp_client.disconnect()
        self._initialized = False