#!/usr/bin/env python3
"""
LLM Interface - Modular AI Communication
=======================================
Handles communication with Large Language Models for tool selection and response generation.
Provides a clean interface for different LLM providers.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_response(self, messages: List[Dict[str, str]], 
                              tools: List[Dict[str, Any]] = None,
                              tool_choice: str = "auto") -> Dict[str, Any]:
        """Generate response from LLM with optional tool calling"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM provider is available"""
        pass

class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI implementation"""
    
    def __init__(self, deployment_name: str = None, api_version: str = "2024-02-15-preview"):
        self.deployment_name = deployment_name or os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")
        self.api_version = api_version
        self._client = None
    
    async def _get_client(self):
        """Get or create Azure OpenAI client"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                api_key = os.getenv("AZURE_OPENAI_API_KEY")
                endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                
                if not api_key or not endpoint:
                    raise ValueError("AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be set")
                
                self._client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=f"{endpoint}/openai/deployments/{self.deployment_name}",
                    api_version=self.api_version
                )
            except Exception as e:
                logger.error(f"❌ [LLM_INTERFACE] Failed to create Azure client: {e}")
                raise
        return self._client
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              tools: List[Dict[str, Any]] = None,
                              tool_choice: str = "auto") -> Dict[str, Any]:
        """Generate response using Azure OpenAI"""
        try:
            client = await self._get_client()
            
            logger.info(f"🔄 [LLM_INTERFACE] Generating response with {len(messages)} messages")
            if tools:
                logger.info(f"🔄 [LLM_INTERFACE] Using {len(tools)} tools with choice: {tool_choice}")
            
            response = await client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice
            )
            
            choice = response.choices[0]
            
            result = {
                "content": choice.message.content or "",
                "finish_reason": choice.finish_reason,
                "tool_calls": [],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
            }
            
            # Extract tool calls if present
            if choice.message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments or "{}"
                        }
                    }
                    for tool_call in choice.message.tool_calls
                ]
            
            logger.info(f"✅ [LLM_INTERFACE] Response generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ [LLM_INTERFACE] Failed to generate response: {e}")
            raise
    
    async def is_available(self) -> bool:
        """Check if Azure OpenAI is available"""
        try:
            await self._get_client()
            return True
        except Exception as e:
            logger.error(f"❌ [LLM_INTERFACE] Azure OpenAI not available: {e}")
            return False

class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing"""
    
    def __init__(self):
        self.responses = [
            "I can help you with that!",
            "Let me process your request.",
            "I'll use the available tools to assist you."
        ]
        self.response_index = 0
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              tools: List[Dict[str, Any]] = None,
                              tool_choice: str = "auto") -> Dict[str, Any]:
        """Generate mock response"""
        # Simple mock that sometimes requests tools
        last_message = messages[-1]["content"].lower() if messages else ""
        
        if tools and any(keyword in last_message for keyword in ["payment", "portfolio", "account", "trade"]):
            # Mock tool call
            tool_name = tools[0]["function"]["name"] if tools else "mock_tool"
            return {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{
                    "id": "mock_call_123",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": '{"status": "pending"}'
                    }
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            }
        else:
            # Mock regular response
            response = self.responses[self.response_index % len(self.responses)]
            self.response_index += 1
            return {
                "content": response,
                "finish_reason": "stop",
                "tool_calls": [],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            }
    
    async def is_available(self) -> bool:
        """Mock is always available"""
        return True

class LLMInterface:
    """Main interface for LLM communication"""
    
    def __init__(self, provider: LLMProvider = None):
        self.provider = provider or AzureOpenAIProvider()
        self.conversation_context = []
    
    async def initialize(self) -> bool:
        """Initialize the LLM interface"""
        try:
            logger.info("🔄 [LLM_INTERFACE] Initializing LLM interface...")
            is_available = await self.provider.is_available()
            
            if is_available:
                logger.info("✅ [LLM_INTERFACE] LLM interface initialized successfully")
                return True
            else:
                logger.error("❌ [LLM_INTERFACE] LLM provider not available")
                return False
                
        except Exception as e:
            logger.error(f"❌ [LLM_INTERFACE] Failed to initialize: {e}")
            return False
    
    async def process_with_tools(self, user_message: str, 
                               tools: List[Dict[str, Any]],
                               conversation_history: List[Dict[str, str]] = None,
                               system_prompt: str = None) -> Dict[str, Any]:
        """Process user message with tool calling capability"""
        try:
            # Build conversation context
            messages = self._build_conversation_context(
                user_message, conversation_history, system_prompt
            )
            
            logger.info(f"🔄 [LLM_INTERFACE] Processing message with {len(tools)} available tools")
            
            # Generate initial response
            response = await self.provider.generate_response(
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            # If tool calls were requested, we need to handle them
            if response["finish_reason"] == "tool_calls":
                logger.info(f"🔄 [LLM_INTERFACE] LLM requested {len(response['tool_calls'])} tool calls")
                
                # Add assistant message with tool calls to conversation
                assistant_message = {
                    "role": "assistant",
                    "content": response["content"],
                    "tool_calls": response["tool_calls"]
                }
                messages.append(assistant_message)
                
                return {
                    "response": response,
                    "messages": messages,
                    "requires_tool_execution": True
                }
            else:
                logger.info("ℹ️ [LLM_INTERFACE] No tool calls requested")
                return {
                    "response": response,
                    "messages": messages,
                    "requires_tool_execution": False
                }
                
        except Exception as e:
            logger.error(f"❌ [LLM_INTERFACE] Failed to process message: {e}")
            raise
    
    async def generate_final_response(self, messages: List[Dict[str, str]], 
                                    tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate final response after tool execution"""
        try:
            logger.info("🔄 [LLM_INTERFACE] Generating final response...")
            
            response = await self.provider.generate_response(
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            logger.info("✅ [LLM_INTERFACE] Final response generated")
            return response
            
        except Exception as e:
            logger.error(f"❌ [LLM_INTERFACE] Failed to generate final response: {e}")
            raise
    
    def _build_conversation_context(self, user_message: str, 
                                  conversation_history: List[Dict[str, str]] = None,
                                  system_prompt: str = None) -> List[Dict[str, str]]:
        """Build conversation context for LLM"""
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system", 
                "content": (
                    "You are an intelligent assistant with access to powerful tools. "
                    "You can intelligently select which tools to use, chain them in complex sequences, "
                    "adapt your approach based on results, handle errors gracefully, and reason about outputs. "
                    "Use tools when helpful and provide comprehensive responses."
                )
            })
        
        # Add conversation history
        if conversation_history:
            # Keep last 10 messages to avoid context overflow
            recent_history = conversation_history[-10:]
            messages.extend(recent_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def add_tool_results(self, messages: List[Dict[str, str]], 
                        tool_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Add tool execution results to conversation context"""
        for tool_result in tool_results:
            if tool_result.get("success", False):
                content = json.dumps(tool_result.get("result", {}))
            else:
                content = f"Error: {tool_result.get('error', 'Unknown error')}"
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_result.get("tool_call_id", ""),
                "content": content
            })
        
        return messages
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics (if available)"""
        # This would be implemented based on the specific provider
        return {"provider": type(self.provider).__name__}