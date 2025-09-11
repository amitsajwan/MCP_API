#!/usr/bin/env python3
"""
Azure OpenAI Client Implementation
Provides Azure 4o integration with AsyncAzureOpenAI and createopen API client functionality.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

try:
    from openai import AsyncAzureOpenAI
    from azure.identity.aio import DefaultAzureCredential
    from azure.identity import ClientSecretCredential
except ImportError as e:
    logging.error(f"Azure OpenAI dependencies not installed: {e}")
    AsyncAzureOpenAI = None
    DefaultAzureCredential = None
    ClientSecretCredential = None

from config import config

logger = logging.getLogger("azure_openai_client")

@dataclass
class ToolCall:
    """Represents a tool call to be executed."""
    tool_name: str
    arguments: Dict[str, Any]
    reason: Optional[str] = None

@dataclass
class CreateOpenAPIClient:
    """CreateOpen API client for enhanced tool planning and execution."""
    
    def __init__(self, azure_client: 'AzureOpenAIClient'):
        self.azure_client = azure_client
        self.logger = logging.getLogger("createopen_client")
    
    async def create_tool_plan(self, user_query: str, available_tools: List[Dict[str, Any]]) -> List[ToolCall]:
        """
        Create an intelligent tool plan using Azure 4o.
        
        Args:
            user_query: The user's query
            available_tools: List of available tools from MCP server
            
        Returns:
            List of ToolCall objects representing the planned execution
        """
        try:
            # Build tools description for the AI
            tools_description = self._build_tools_description(available_tools)
            
            # Create the system prompt for tool planning
            system_prompt = f"""You are an intelligent tool planning assistant. Your job is to analyze user queries and create a plan of tool calls to fulfill the request.

Available tools:
{tools_description}

Instructions:
1. Analyze the user query carefully and identify the intent
2. Match the user's intent to the most appropriate tools based on:
   - Method (GET for reading data, POST for creating, PUT/PATCH for updating, DELETE for removing)
   - Path patterns (look for relevant endpoints)
   - Category and tags (group related functionality)
   - Required parameters (ensure you can provide them)
3. Create a logical sequence of tool calls considering:
   - Authentication tools first (set_credentials, perform_login)
   - Dependencies between tools
   - Data flow (output from one tool as input to another)
4. Provide clear reasoning for each tool call
5. Only suggest tools that are actually available
6. Use the API properties (method, path, category) to make better tool selections

Return your response as a JSON array of tool calls with this structure:
[
  {{
    "tool_name": "exact_tool_name",
    "arguments": {{"param1": "value1", "param2": "value2"}},
    "reason": "Why this tool call is needed based on method, path, and category"
  }}
]

If no tools are needed, return an empty array [].
"""

            # Create the user message
            user_message = f"User query: {user_query}\n\nPlease create a tool execution plan."

            # Call Azure 4o for intelligent planning
            response = await self.azure_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,  # Low temperature for consistent planning
                max_tokens=2000
            )

            # Parse the response
            if response and "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                
                # Try to extract JSON from the response
                try:
                    # Look for JSON array in the response
                    import re
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        tool_calls_data = json.loads(json_str)
                        
                        # Convert to ToolCall objects
                        tool_calls = []
                        for tool_data in tool_calls_data:
                            if isinstance(tool_data, dict) and "tool_name" in tool_data:
                                tool_calls.append(ToolCall(
                                    tool_name=tool_data["tool_name"],
                                    arguments=tool_data.get("arguments", {}),
                                    reason=tool_data.get("reason", "")
                                ))
                        
                        self.logger.info(f"Created {len(tool_calls)} tool calls using Azure 4o")
                        return tool_calls
                    else:
                        self.logger.warning("No JSON array found in Azure 4o response")
                        return []
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse Azure 4o response as JSON: {e}")
                    self.logger.debug(f"Response content: {content}")
                    return []
            else:
                self.logger.error("Invalid response from Azure 4o")
                return []

        except Exception as e:
            self.logger.error(f"Error in create_tool_plan: {e}")
            return []
    
    def _build_tools_description(self, available_tools: List[Dict[str, Any]]) -> str:
        """Build a comprehensive description of available tools for the AI."""
        descriptions = []
        
        for tool in available_tools:
            tool_name = tool.get('name', 'Unknown')
            description = tool.get('description', 'No description')
            
            desc_parts = [f"🔧 {tool_name}"]
            desc_parts.append(f"   Description: {description}")
            
            # Add API-specific properties if available
            api_props = tool.get('api_properties', {})
            if api_props:
                desc_parts.append(f"   Method: {api_props.get('method', 'N/A')}")
                desc_parts.append(f"   Path: {api_props.get('path', 'N/A')}")
                desc_parts.append(f"   Category: {api_props.get('category', 'general')}")
                if api_props.get('tags'):
                    desc_parts.append(f"   Tags: {', '.join(api_props['tags'])}")
                if api_props.get('summary'):
                    desc_parts.append(f"   Summary: {api_props['summary']}")
                desc_parts.append(f"   Parameters: {api_props.get('parameters_count', 0)} total")
                if api_props.get('required_parameters'):
                    desc_parts.append(f"   Required: {', '.join(api_props['required_parameters'])}")
            
            # Add schema information
            schema = tool.get('inputSchema', {})
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            if properties:
                desc_parts.append("   Parameter Details:")
                for prop_name, prop_info in properties.items():
                    prop_type = prop_info.get('type', 'any')
                    prop_desc = prop_info.get('description', '')
                    is_required = prop_name in required
                    req_indicator = "*" if is_required else ""
                    desc_parts.append(f"     - {prop_name}{req_indicator}: {prop_type} - {prop_desc}")
            
            descriptions.append("\n".join(desc_parts))
        
        return "\n\n".join(descriptions)

class AzureOpenAIClient:
    """Azure OpenAI client with AsyncAzureOpenAI and bearer token authentication."""
    
    def __init__(self):
        self.client: Optional[AsyncAzureOpenAI] = None
        self.credential = None
        self.logger = logging.getLogger("azure_openai_client")
        self.createopen_client = None
        
        # Initialize the client
        self._initialized = False
    
    async def _initialize(self):
        """Initialize the Azure OpenAI client with proper authentication."""
        try:
            if not AsyncAzureOpenAI or not DefaultAzureCredential:
                self.logger.error("Azure OpenAI dependencies not available")
                return False
            
            # Get Azure configuration
            endpoint = config.AZURE_OPENAI_ENDPOINT
            deployment = config.AZURE_OPENAI_DEPLOYMENT
            api_version = config.AZURE_OPENAI_API_VERSION
            
            if not endpoint:
                self.logger.error("AZURE_OPENAI_ENDPOINT not configured")
                return False
            
            # Set up authentication
            if config.USE_AZURE_AD_TOKEN_PROVIDER:
                # Use Azure AD token provider (recommended)
                self.credential = DefaultAzureCredential()
                self.logger.info("Using Azure AD Token Provider for authentication")
            else:
                # Use API key (legacy)
                api_key = config.AZURE_OPENAI_API_KEY
                if not api_key:
                    self.logger.error("AZURE_OPENAI_API_KEY not configured")
                    return False
                self.logger.info("Using API Key for authentication")
            
            # Create the Azure OpenAI client
            if config.USE_AZURE_AD_TOKEN_PROVIDER:
                self.client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_deployment=deployment,
                    api_version=api_version,
                    azure_ad_token_provider=self._get_token_provider()
                )
            else:
                self.client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_deployment=deployment,
                    api_version=api_version,
                    api_key=api_key
                )
            
            # Initialize the createopen client
            self.createopen_client = CreateOpenAPIClient(self)
            
            self.logger.info(f"✅ Azure OpenAI client initialized with deployment: {deployment}")
            self._initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Azure OpenAI client: {e}")
            return False
    
    async def _get_token_provider(self):
        """Get Azure AD token provider for authentication."""
        if not self.credential:
            return None
        
        async def token_provider():
            token = await self.credential.get_token(config.AZURE_AD_TOKEN_SCOPE)
            return token.token
        
        return token_provider
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make a chat completion request to Azure OpenAI.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters for the completion
            
        Returns:
            Response from Azure OpenAI or None if failed
        """
        try:
            if not self.client:
                self.logger.error("Azure OpenAI client not initialized")
                return None
            
            # Set default parameters
            default_params = {
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            default_params.update(kwargs)
            
            # Make the request
            response = await self.client.chat.completions.create(
                messages=messages,
                **default_params
            )
            
            # Convert to dictionary
            result = {
                "id": response.id,
                "object": response.object,
                "created": response.created,
                "model": response.model,
                "choices": [
                    {
                        "index": choice.index,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None
            }
            
            self.logger.info(f"Azure OpenAI completion successful: {result['usage']['total_tokens']} tokens used")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in Azure OpenAI chat completion: {e}")
            return None
    
    async def create_tool_plan(self, user_query: str, available_tools: List[Dict[str, Any]]) -> List[ToolCall]:
        """
        Create an intelligent tool plan using Azure 4o.
        
        Args:
            user_query: The user's query
            available_tools: List of available tools from MCP server
            
        Returns:
            List of ToolCall objects representing the planned execution
        """
        # Ensure client is initialized
        if not self._initialized:
            await self._initialize()
        
        if not self.createopen_client:
            self.logger.error("CreateOpen client not initialized")
            return []
        
        return await self.createopen_client.create_tool_plan(user_query, available_tools)
    
    async def close(self):
        """Close the Azure OpenAI client and clean up resources."""
        try:
            if self.credential and hasattr(self.credential, 'close'):
                await self.credential.close()
            self.logger.info("Azure OpenAI client closed")
        except Exception as e:
            self.logger.error(f"Error closing Azure OpenAI client: {e}")

# Global instance
azure_client = AzureOpenAIClient()