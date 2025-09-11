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

logger = logging.getLogger(__name__)

class ModernLLMService:
    """Service demonstrating modern LLM tool capabilities"""
    
    def __init__(self, mcp_server_cmd: str = "python mcp_server_fastmcp2.py --transport stdio"):
        self.mcp_server_cmd = mcp_server_cmd
        self._mcp_client = None
        self._azure_client = None
        self._tools = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the MCP connection and load tools"""
        try:
            self._azure_client = await create_azure_client()
            # Parse command: "python mcp_server_fastmcp2.py --transport stdio"
            cmd_parts = self.mcp_server_cmd.split()
            script_path = cmd_parts[1]  # mcp_server_fastmcp2.py
            args = cmd_parts[2:]  # ['--transport', 'stdio']
            transport = PythonStdioTransport(script_path, args=args)
            self._mcp_client = MCPClient(transport)
            await self._mcp_client.__aenter__()
            self._tools = await list_and_prepare_tools(self._mcp_client)
            
            self._initialized = True
            logger.info("✅ Modern LLM Service initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Modern LLM Service: {e}")
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
    
    async def process_message(self, user_message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Process message with modern LLM tool capabilities"""
        if not self._initialized or not self._mcp_client or not self._azure_client or not self._tools:
            return {"error": "Service not initialized"}
        
        try:
            # Build conversation context with modern LLM capabilities
            messages = [
                {"role": "system", "content": (
                    "You are an intelligent assistant with access to powerful tools. "
                    "You can intelligently select which tools to use, chain them in complex sequences, "
                    "adapt your approach based on results, handle errors gracefully, and reason about outputs. "
                    "Use tools when helpful and provide comprehensive responses."
                )}
            ]
            
            if conversation_history:
                messages.extend(conversation_history)
            
            messages.append({"role": "user", "content": user_message})
            
            # Process with modern LLM tool calling
            response = await self._azure_client.chat.completions.create(
                model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o"),
                messages=messages,
                tools=self._tools,
                tool_choice="auto"
            )
            
            choice = response.choices[0]
            tool_calls = []
            
            if choice.finish_reason == "tool_calls":
                # Handle tool calls with modern capabilities
                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments or "{}")
                    
                    try:
                        raw_result = await self._mcp_client.call_tool(tool_name, args)
                        result = safe_truncate(raw_result)
                        
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
                        logger.error(f"❌ Tool call failed: {e}")
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
                response = await self._azure_client.chat.completions.create(
                    model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o"),
                    messages=messages,
                    tools=self._tools,
                    tool_choice="auto"
                )
                
                choice = response.choices[0]
            
            # Analyze capabilities demonstrated
            capabilities = self._analyze_capabilities(tool_calls, user_message)
            
            return {
                "response": choice.message.content or "",
                "tool_calls": tool_calls,
                "conversation": messages[1:],
                "capabilities": capabilities
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {"error": str(e)}
    
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
        """Get list of available tools"""
        if not self._initialized or not self._tools:
            return []
        return self._tools

# Global service instance
mcp_service = ModernLLMService()