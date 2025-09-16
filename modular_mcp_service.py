#!/usr/bin/env python3
"""
Modular MCP Service - Refactored Service with Modular Components
===============================================================
A clean, modular implementation of the MCP service using separate components
for tool orchestration, LLM communication, conversation management, and capability analysis.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional

# Import modular components
from tool_orchestrator import ToolOrchestrator, ToolResult
from llm_interface import LLMInterface, AzureOpenAIProvider, MockLLMProvider
from conversation_manager import ConversationManager
from capability_analyzer import CapabilityAnalyzer
# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('modular_mcp_service.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

try:
    from mcp_tool_executor import MCPToolExecutor, MockToolExecutor
    from mcp_client import MCPClient, PythonStdioTransport, list_and_prepare_tools, create_azure_client
except ImportError as e:
    logger.warning(f"Some MCP dependencies not available: {e}")
    # Define fallback classes
    class MCPToolExecutor:
        def __init__(self, *args, **kwargs):
            pass
    class MockToolExecutor:
        def __init__(self, *args, **kwargs):
            pass
    class MCPClient:
        def __init__(self, *args, **kwargs):
            pass
    class PythonStdioTransport:
        def __init__(self, *args, **kwargs):
            pass
    def list_and_prepare_tools(*args, **kwargs):
        return []
    def create_azure_client(*args, **kwargs):
        return None

class ModularMCPService:
    """Modular MCP service with separated concerns"""
    
    def __init__(self, mcp_server_cmd: str = "python mcp_server_fastmcp2.py --transport stdio",
                 use_mock: bool = False):
        self.mcp_server_cmd = mcp_server_cmd
        self.use_mock = use_mock
        
        # Initialize components
        self.conversation_manager = ConversationManager()
        self.capability_analyzer = CapabilityAnalyzer()
        
        # Initialize tool executor and orchestrator
        self.tool_executor = None
        self.tool_orchestrator = None
        
        # Initialize LLM interface
        self.llm_interface = None
        
        # Service state
        self._initialized = False
        self._tools = None
    
    async def initialize(self) -> bool:
        """Initialize the modular MCP service"""
        try:
            logger.info("🔄 [MODULAR_SERVICE] Starting initialization...")
            
            # Initialize LLM interface
            if self.use_mock:
                self.llm_interface = LLMInterface(MockLLMProvider())
            else:
                self.llm_interface = LLMInterface(AzureOpenAIProvider())
            
            llm_initialized = await self.llm_interface.initialize()
            if not llm_initialized:
                logger.error("❌ [MODULAR_SERVICE] Failed to initialize LLM interface")
                return False
            
            # Initialize tool executor
            if self.use_mock:
                self.tool_executor = MockToolExecutor()
            else:
                mcp_client = await self._create_mcp_client()
                self.tool_executor = MCPToolExecutor(mcp_client)
            
            # Initialize tool orchestrator
            self.tool_orchestrator = ToolOrchestrator(self.tool_executor)
            
            # Load tools if not using mock
            if not self.use_mock:
                self._tools = await self._load_tools()
            else:
                self._tools = self._get_mock_tools()
            
            self._initialized = True
            logger.info("✅ [MODULAR_SERVICE] Modular MCP service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ [MODULAR_SERVICE] Failed to initialize: {e}")
            self._initialized = False
            return False
    
    async def _create_mcp_client(self) -> MCPClient:
        """Create MCP client connection"""
        try:
            logger.info("🔄 [MODULAR_SERVICE] Creating MCP client...")
            
            # Parse command
            cmd_parts = self.mcp_server_cmd.split()
            script_path = cmd_parts[1]
            args = cmd_parts[2:]
            
            # Create transport and client
            transport = PythonStdioTransport(script_path, args=args)
            mcp_client = MCPClient(transport)
            
            # Connect
            await mcp_client.__aenter__()
            logger.info("✅ [MODULAR_SERVICE] MCP client created and connected")
            
            return mcp_client
            
        except Exception as e:
            logger.error(f"❌ [MODULAR_SERVICE] Failed to create MCP client: {e}")
            raise
    
    async def _load_tools(self) -> List[Dict[str, Any]]:
        """Load tools from MCP server"""
        try:
            logger.info("🔄 [MODULAR_SERVICE] Loading tools...")
            
            # This would use the actual MCP client to load tools
            # For now, return empty list as placeholder
            tools = []
            logger.info(f"✅ [MODULAR_SERVICE] Loaded {len(tools)} tools")
            return tools
            
        except Exception as e:
            logger.error(f"❌ [MODULAR_SERVICE] Failed to load tools: {e}")
            return []
    
    def _get_mock_tools(self) -> List[Dict[str, Any]]:
        """Get mock tools for testing"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_payments",
                    "description": "Get payment information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "description": "Payment status"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_portfolio",
                    "description": "Get portfolio holdings",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string", "description": "Account identifier"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_payment",
                    "description": "Create a new payment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "number", "description": "Payment amount"},
                            "currency": {"type": "string", "description": "Payment currency"}
                        },
                        "required": ["amount", "currency"]
                    }
                }
            }
        ]
    
    async def process_message(self, user_message: str, 
                            conversation_history: List[Dict] = None,
                            session_id: str = "default") -> Dict[str, Any]:
        """Process user message with modular components"""
        if not self._initialized:
            return {"error": "Service not initialized"}
        
        try:
            logger.info(f"🔄 [MODULAR_SERVICE] Processing message for session {session_id}")
            
            # Add user message to conversation
            self.conversation_manager.add_message(
                session_id, "user", user_message
            )
            
            # Get conversation context
            context = self.conversation_manager.get_context_window(session_id)
            
            # Process with LLM interface
            llm_result = await self.llm_interface.process_with_tools(
                user_message=user_message,
                tools=self._tools,
                conversation_history=context
            )
            
            tool_results = []
            
            # Handle tool execution if required
            if llm_result.get("requires_tool_execution", False):
                tool_calls = llm_result["response"].get("tool_calls", [])
                
                if tool_calls:
                    logger.info(f"🔧 [MODULAR_SERVICE] Executing {len(tool_calls)} tool calls")
                    
                    # Execute tools through orchestrator
                    tool_results = await self.tool_orchestrator.execute_tool_calls(
                        tool_calls, execution_strategy="adaptive"
                    )
                    
                    # Add tool results to conversation
                    for result in tool_results:
                        self.conversation_manager.add_message(
                            session_id, "tool", 
                            json.dumps(result.result) if result.success else f"Error: {result.error}",
                            metadata={"tool_name": result.tool_name, "success": result.success}
                        )
                    
                    # Generate final response with tool results
                    messages = llm_result["messages"]
                    self.llm_interface.add_tool_results(messages, [r.to_dict() for r in tool_results])
                    
                    final_response = await self.llm_interface.generate_final_response(messages)
                    llm_result["response"] = final_response
            
            # Analyze capabilities demonstrated
            capabilities = self.capability_analyzer.analyze_tool_execution(
                [r.to_dict() for r in tool_results], user_message, session_id
            )
            
            # Add assistant response to conversation
            response_content = llm_result["response"].get("content", "")
            self.conversation_manager.add_message(
                session_id, "assistant", response_content,
                tool_calls=llm_result["response"].get("tool_calls", [])
            )
            
            # Build final result
            result = {
                "success": True,
                "response": response_content,
                "tool_calls": [r.to_dict() for r in tool_results],
                "capabilities": capabilities,
                "conversation": self.conversation_manager.get_conversation_history(session_id),
                "usage_stats": llm_result["response"].get("usage", {})
            }
            
            logger.info(f"✅ [MODULAR_SERVICE] Message processed successfully for session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ [MODULAR_SERVICE] Error processing message: {e}")
            return {"error": str(e)}
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        if not self._initialized or not self._tools:
            return []
        return self._tools
    
    async def get_conversation_summary(self, session_id: str = "default") -> Dict[str, Any]:
        """Get conversation summary for a session"""
        return self.conversation_manager.get_conversation_summary(session_id)
    
    async def get_capability_analysis(self, session_id: str = None) -> Dict[str, Any]:
        """Get capability analysis"""
        if session_id:
            return self.capability_analyzer.get_session_analysis(session_id)
        else:
            return self.capability_analyzer.get_system_analysis()
    
    async def get_tool_usage_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        return self.capability_analyzer.get_tool_usage_stats()
    
    async def clear_conversation(self, session_id: str = "default"):
        """Clear conversation for a session"""
        self.conversation_manager.clear_conversation(session_id)
        logger.info(f"🧹 [MODULAR_SERVICE] Cleared conversation for session {session_id}")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.tool_executor and hasattr(self.tool_executor, 'mcp_client'):
                await self.tool_executor.mcp_client.__aexit__(None, None, None)
            
            self._initialized = False
            logger.info("✅ [MODULAR_SERVICE] Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ [MODULAR_SERVICE] Error during cleanup: {e}")

# Factory function for easy instantiation
async def create_modular_service(mcp_server_cmd: str = None, use_mock: bool = False) -> ModularMCPService:
    """Factory function to create and initialize a modular MCP service"""
    service = ModularMCPService(mcp_server_cmd, use_mock)
    success = await service.initialize()
    
    if not success:
        raise RuntimeError("Failed to initialize modular MCP service")
    
    return service

# Example usage
if __name__ == "__main__":
    async def main():
        # Create service
        service = await create_modular_service(use_mock=True)
        
        # Process a message
        result = await service.process_message(
            "Show me all pending payments over $1000",
            session_id="test_session"
        )
        
        print("Response:", result["response"])
        print("Tool calls:", len(result["tool_calls"]))
        print("Capabilities:", result["capabilities"]["descriptions"])
        
        # Get analysis
        analysis = await service.get_capability_analysis("test_session")
        print("Session analysis:", analysis)
        
        # Cleanup
        await service.cleanup()
    
    asyncio.run(main())