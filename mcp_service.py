#!/usr/bin/env python3
"""
Modern LLM Tool Capabilities Service
===================================
Core service demonstrating modern LLM tool usage:
- Intelligent tool selection
- Complex tool chaining
- Adaptive tool usage
- Error handling and retry logic
- Reasoning about tool outputs
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from mcp_client import MCPClient, PythonStdioTransport, list_and_prepare_tools, create_azure_client, safe_truncate

# Configure comprehensive logging for MCP service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_service.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class ModernLLMService:
    """Service demonstrating modern LLM tool capabilities"""
    
    def __init__(self, mcp_server_cmd: str = "python mcp_server_fastmcp2.py --transport stdio"):
        self.mcp_server_cmd = mcp_server_cmd
        self._mcp_client = None
        self._azure_client = None
        self._tools = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the MCP connection and load tools - synchronous version"""
        logger.info("🔄 [MCP_SERVICE] Starting initialization...")
        try:
            # Use asyncio.run to handle the async initialization
            result = asyncio.run(self._async_initialize())
            return result
        except Exception as e:
            logger.error(f"❌ [MCP_SERVICE] Failed to initialize Modern LLM Service: {e}")
            self._initialized = False
            return False
    
    async def _async_initialize(self):
        """Async initialization helper"""
        try:
            logger.info("🔄 [MCP_SERVICE] Creating Azure client...")
            self._azure_client = await create_azure_client()
            logger.info("✅ [MCP_SERVICE] Azure client created")
            
            # Parse command: "python mcp_server_fastmcp2.py --transport stdio"
            logger.info(f"🔄 [MCP_SERVICE] Parsing MCP server command: {self.mcp_server_cmd}")
            cmd_parts = self.mcp_server_cmd.split()
            script_path = cmd_parts[1]  # mcp_server_fastmcp2.py
            args = cmd_parts[2:]  # ['--transport', 'stdio']
            logger.info(f"🔄 [MCP_SERVICE] Script path: {script_path}, Args: {args}")
            
            logger.info("🔄 [MCP_SERVICE] Creating PythonStdioTransport...")
            transport = PythonStdioTransport(script_path, args=args)
            logger.info("✅ [MCP_SERVICE] Transport created")
            
            logger.info("🔄 [MCP_SERVICE] Creating MCP client...")
            self._mcp_client = MCPClient(transport)
            logger.info("✅ [MCP_SERVICE] MCP client created")
            
            logger.info("🔄 [MCP_SERVICE] Connecting to MCP server...")
            await self._mcp_client.__aenter__()
            logger.info("✅ [MCP_SERVICE] Connected to MCP server")
            
            logger.info("🔄 [MCP_SERVICE] Loading tools...")
            self._tools = await list_and_prepare_tools(self._mcp_client)
            logger.info(f"✅ [MCP_SERVICE] Loaded {len(self._tools)} tools")
            
            self._initialized = True
            logger.info("✅ [MCP_SERVICE] Modern LLM Service initialized successfully")
            return True
                    
        except Exception as e:
            logger.error(f"❌ [MCP_SERVICE] Failed to initialize Modern LLM Service: {e}")
            self._initialized = False
            return False
    
    async def initialize_with_cmd(self, mcp_server_cmd):
        """Initialize with a specific MCP server command"""
        try:
            self.mcp_server_cmd = mcp_server_cmd
            self._azure_client = await create_azure_client()
            # Parse command: "python mcp_server_fastmcp2.py --transport stdio"
            cmd_parts = mcp_server_cmd.split()
            script_path = cmd_parts[1]  # mcp_server_fastmcp2.py
            args = cmd_parts[2:]  # ['--transport', 'stdio']
            transport = PythonStdioTransport(script_path, args=args)
            self._mcp_client = MCPClient(transport)
            await self._mcp_client.__aenter__()
            self._tools = await list_and_prepare_tools(self._mcp_client)
            
            self._initialized = True
            logger.info("✅ Modern LLM Service reinitialized with new credentials")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reinitialize Modern LLM Service: {e}")
            self._initialized = False
            return False
    
    async def cleanup(self):
        """Clean up MCP connection"""
        if self._mcp_client:
            try:
                await self._mcp_client.__aexit__(None, None, None)
                self._mcp_client = None
                self._initialized = False
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
    
    def process_message(self, user_message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Process message with modern LLM tool capabilities - synchronous version"""
        logger.info(f"🔄 [MCP_SERVICE] Processing message: '{user_message[:100]}...'")
        
        if not self._initialized or not self._mcp_client or not self._azure_client or not self._tools:
            logger.error("❌ [MCP_SERVICE] Service not initialized")
            return {"error": "Service not initialized"}
        
        try:
            # Use asyncio.run to handle the async processing
            result = asyncio.run(self._async_process_message(user_message, conversation_history))
            return result
        except Exception as e:
            logger.error(f"❌ [MCP_SERVICE] Error processing message: {e}")
            return {"error": str(e)}
    
    async def _async_process_message(self, user_message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Async message processing helper"""
        try:
            # Build conversation context with modern LLM capabilities
            logger.info("🔄 [MCP_SERVICE] Building conversation context...")
            messages = [
                {"role": "system", "content": (
                    "You are an intelligent assistant with access to powerful tools. "
                    "You can intelligently select which tools to use, chain them in complex sequences, "
                    "adapt your approach based on results, handle errors gracefully, and reason about outputs. "
                    "Use tools when helpful and provide comprehensive responses."
                )}
            ]
            
            if conversation_history:
                logger.info(f"🔄 [MCP_SERVICE] Adding {len(conversation_history)} conversation history messages")
                messages.extend(conversation_history)
            
            messages.append({"role": "user", "content": user_message})
            logger.info(f"🔄 [MCP_SERVICE] Total messages: {len(messages)}")
            
            # Process with modern LLM tool calling
            logger.info("🔄 [MCP_SERVICE] Calling Azure OpenAI...")
            response = await self._azure_client.chat.completions.create(
                model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o"),
                messages=messages,
                tools=self._tools,
                tool_choice="auto"
            )
            logger.info("✅ [MCP_SERVICE] Azure OpenAI response received")
            
            choice = response.choices[0]
            tool_calls = []
        
            if choice.finish_reason == "tool_calls":
                logger.info(f"🔄 [MCP_SERVICE] LLM requested {len(choice.message.tool_calls)} tool calls")
                # Handle tool calls with modern capabilities
                for i, tool_call in enumerate(choice.message.tool_calls, 1):
                    tool_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments or "{}")
                    
                    logger.info(f"🔧 [MCP_SERVICE] Executing tool {i}/{len(choice.message.tool_calls)}: {tool_name}")
                    logger.info(f"🔧 [MCP_SERVICE] Tool args: {args}")
                    
                    try:
                        logger.info(f"🔄 [MCP_SERVICE] Calling MCP tool: {tool_name}")
                        raw_result = await self._mcp_client.call_tool(tool_name, args)
                        logger.info(f"✅ [MCP_SERVICE] Tool {tool_name} completed successfully")
                        
                        result = safe_truncate(raw_result)
                        logger.info(f"🔄 [MCP_SERVICE] Tool result truncated: {len(str(result))} chars")
                        
                        tool_calls.append({
                            "tool_call_id": tool_call.id,
                            "tool_name": tool_name,
                            "args": args,
                            "result": result
                        })
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result)
                        })
                    
                    except Exception as e:
                        logger.error(f"❌ [MCP_SERVICE] Tool call failed: {tool_name} - {e}")
                        tool_calls.append({
                            "tool_call_id": tool_call.id,
                            "tool_name": tool_name,
                            "args": args,
                            "error": str(e)
                        })
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: {e}"
                        })
                
                # Continue conversation to get final response
                logger.info("🔄 [MCP_SERVICE] Getting final response from LLM...")
                response = await self._azure_client.chat.completions.create(
                    model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o"),
                    messages=messages,
                    tools=self._tools,
                    tool_choice="auto"
                )
                logger.info("✅ [MCP_SERVICE] Final response received")
                
                choice = response.choices[0]
            else:
                logger.info("ℹ️ [MCP_SERVICE] No tool calls requested by LLM")
            
            # Analyze capabilities demonstrated
            logger.info("🔄 [MCP_SERVICE] Analyzing capabilities...")
            capabilities = self._analyze_capabilities(tool_calls, user_message)
            logger.info(f"✨ [MCP_SERVICE] Capabilities: {capabilities.get('descriptions', [])}")
            
            result = {
                "success": True,
                "response": choice.message.content or "",
                "tool_calls": tool_calls,
                "conversation": messages[1:],
                "capabilities": capabilities
            }
            
            logger.info(f"✅ [MCP_SERVICE] Message processing completed successfully")
            return result
                    
        except Exception as e:
            logger.error(f"❌ [MCP_SERVICE] Error processing message: {e}")
            return {"error": str(e)}
    
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
    
    def _analyze_capabilities(self, tool_calls: List[Dict], user_message: str) -> Dict[str, Any]:
        """Analyze which modern LLM capabilities were demonstrated"""
        capabilities = {
            "intelligent_selection": len(tool_calls) > 0,
            "tool_chaining": len(tool_calls) > 1,
            "error_handling": any(tc.get('error') for tc in tool_calls),
            "adaptive_usage": len(tool_calls) > 0 and not any(tc.get('error') for tc in tool_calls),
            "reasoning": len(tool_calls) > 0
        }
        
        # Add capability descriptions
        capability_descriptions = []
        if capabilities["intelligent_selection"]:
            capability_descriptions.append("🧠 Intelligent Tool Selection")
        if capabilities["tool_chaining"]:
            capability_descriptions.append("🔗 Complex Tool Chaining")
        if capabilities["error_handling"]:
            capability_descriptions.append("🛡️ Error Handling & Retry")
        if capabilities["adaptive_usage"]:
            capability_descriptions.append("🔄 Adaptive Tool Usage")
        if capabilities["reasoning"]:
            capability_descriptions.append("🧩 Reasoning About Outputs")
        
        capabilities["descriptions"] = capability_descriptions
        capabilities["tool_count"] = len(tool_calls)
        capabilities["success_rate"] = len([tc for tc in tool_calls if not tc.get('error')]) / max(len(tool_calls), 1)
        
        return capabilities
    
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

# Global service instance
mcp_service = ModernLLMService()