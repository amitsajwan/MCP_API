#!/usr/bin/env python3
"""
Intelligent MCP Client - Enhanced with LLM Function Calling
Features:
- OpenAI function calling integration with MCP tools
- Intelligent response-based decision making
- Adaptive conversation flow with function results
- Smart argument extraction and validation
- Multi-turn conversation support with context
"""

import logging
import asyncio
import json
import os
import requests
from typing import Dict, Any, List, Optional, Union
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

@dataclass
class ConversationMessage:
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

# Import config or create default
try:
    from config import config
except ImportError:
    class DefaultConfig:
        LOG_LEVEL = "INFO"
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        MAX_FUNCTION_CALLS = 5
        MAX_CONVERSATION_TURNS = 10
        
        def validate(self):
            return True
    
    config = DefaultConfig()

# Configure logging
logging.basicConfig(
    level=getattr(logging, getattr(config, 'LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("intelligent_mcp_client")

class IntelligentMCPClient:
    """Intelligent MCP Client with LLM Function Calling Integration"""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8000", 
                 openai_api_key: str = None, 
                 openai_model: str = "gpt-4o"):
        self.server_url = mcp_server_url
        self.available_tools: List[Tool] = []
        self.session = requests.Session()
        
        # Initialize OpenAI client
        self.openai_client = self._create_openai_client()
        self.model = openai_model
        
        # Conversation state
        self.conversation_history: List[ConversationMessage] = []
        self.function_call_count = 0
        
        logging.info(f"Initialized Intelligent MCP Client connecting to {mcp_server_url}")
        
        # Initialize dynamic tool categorizer
        self.tool_categorizer = DynamicToolCategorizer()
        
        # System prompt for intelligent function calling
        self.system_prompt = """You are an intelligent financial API assistant with access to various financial tools and services.

Your capabilities:
1. Analyze user requests and decide which tools to use
2. Extract parameters intelligently from user queries
3. Handle multi-step workflows by chaining function calls
4. Provide clear, helpful responses based on function results
5. Ask for clarification only when absolutely necessary

Guidelines:
- Use function calls to gather data before responding
- If one function fails, try alternative approaches
- Combine data from multiple sources when beneficial
- Provide detailed, actionable insights from the data
- Handle authentication flows automatically when needed
- Be proactive in suggesting related actions or insights"""

    def _create_openai_client(self) -> AsyncAzureOpenAI:
        """Create Azure OpenAI client with azure_ad_token_provider."""
        azure_endpoint = getattr(config, 'AZURE_OPENAI_ENDPOINT', os.getenv("AZURE_OPENAI_ENDPOINT"))
        
        try:
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
            logging.info(f"🔧 Calling tool: {tool_name} with arguments: {arguments}")
            
            payload = {"name": tool_name, "arguments": arguments}
            response = self.session.post(f"{self.server_url}/call_tool", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                logging.info(f"✅ Tool {tool_name} executed successfully")
                return {"status": "success", "data": result}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logging.error(f"❌ Tool {tool_name} failed: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            logging.error(f"Exception calling tool {tool_name}: {e}")
            return {"status": "error", "message": str(e)}

    def _convert_tools_to_openai_format(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI function calling format."""
        openai_tools = []
        for tool in self.available_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools

    def _build_conversation_messages(self, user_query: str) -> List[Dict[str, Any]]:
        """Build conversation messages for OpenAI API."""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history
        for msg in self.conversation_history:
            message_dict = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            if msg.name:
                message_dict["name"] = msg.name
            messages.append(message_dict)
        
        # Add current user query
        messages.append({"role": "user", "content": user_query})
        
        return messages

    async def _execute_function_calls(self, tool_calls: List[Dict]) -> List[ConversationMessage]:
        """Execute function calls and return tool response messages."""
        tool_responses = []
        
        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])
            
            # Execute the tool
            result = self.call_tool(function_name, function_args)
            
            # Create tool response message
            if result["status"] == "success":
                content = json.dumps(result["data"], indent=2)
                logging.info(f"✅ Function {function_name} returned data")
            else:
                content = f"Error: {result.get('message', 'Unknown error')}"
                logging.error(f"❌ Function {function_name} failed: {content}")
            
            tool_response = ConversationMessage(
                role="tool",
                content=content,
                tool_call_id=tool_call["id"],
                name=function_name
            )
            tool_responses.append(tool_response)
            
            self.function_call_count += 1
        
        return tool_responses

    async def _should_continue_with_functions(self, response_message: Dict) -> bool:
        """Determine if we should continue with more function calls."""
        # Check function call limits
        if self.function_call_count >= getattr(config, 'MAX_FUNCTION_CALLS', 5):
            logging.warning("Maximum function calls reached")
            return False
        
        # Check conversation turn limits
        if len(self.conversation_history) >= getattr(config, 'MAX_CONVERSATION_TURNS', 10):
            logging.warning("Maximum conversation turns reached")
            return False
        
        # Check if assistant wants to make more function calls
        return bool(response_message.get("tool_calls"))

    async def _handle_authentication_flow(self, user_query: str) -> Dict[str, Any]:
        """Handle authentication-related queries with intelligent flow."""
        auth_keywords = ["login", "credential", "authenticate", "password", "username", "auth"]
        if any(keyword in user_query.lower() for keyword in auth_keywords):
            logging.info("🔐 Detected authentication request, attempting auto-login")
            
            # Try perform_login first
            login_result = self.call_tool("perform_login")
            if login_result.get("status") == "success":
                return {
                    "status": "success",
                    "message": "Authentication successful. You can now access your financial data.",
                    "authenticated": True
                }
            else:
                return {
                    "status": "needs_credentials",
                    "message": "Authentication required. Please provide your credentials.",
                    "authenticated": False
                }
        return {"status": "not_auth_request"}

    async def process_query_intelligent(self, user_query: str, reset_conversation: bool = False) -> Dict[str, Any]:
        """
        Intelligent query processing with LLM function calling and adaptive conversation flow.
        """
        logging.info(f"🧠 Processing intelligent query: {user_query}")
        
        # Reset conversation if requested
        if reset_conversation:
            self.conversation_history = []
            self.function_call_count = 0
        
        # Ensure connection and tools
        if not self.connect():
            return {"status": "error", "message": "Failed to connect to MCP server"}
        
        if not self.available_tools:
            self.list_tools()
            if not self.available_tools:
                return {"status": "error", "message": "No tools available"}
        
        # Handle authentication flow
        auth_check = await self._handle_authentication_flow(user_query)
        if auth_check["status"] != "not_auth_request":
            return auth_check
        
        try:
            # Convert tools to OpenAI format
            openai_tools = self._convert_tools_to_openai_format()
            
            # Build conversation messages
            messages = self._build_conversation_messages(user_query)
            
            # Start conversation loop with function calling
            conversation_active = True
            final_response = None
            
            while conversation_active:
                # Make API call with function calling
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto",
                    temperature=0.1,
                    max_tokens=1500
                )
                
                response_message = response.choices[0].message
                
                # Add assistant message to conversation
                assistant_msg = ConversationMessage(
                    role="assistant",
                    content=response_message.content or "",
                    tool_calls=[tc.to_dict() if hasattr(tc, 'to_dict') else tc for tc in (response_message.tool_calls or [])]
                )
                self.conversation_history.append(assistant_msg)
                
                # Check if assistant wants to call functions
                if response_message.tool_calls and self._should_continue_with_functions(response_message.to_dict()):
                    logging.info(f"🔧 Assistant requested {len(response_message.tool_calls)} function calls")
                    
                    # Execute function calls
                    tool_responses = await self._execute_function_calls([tc.to_dict() if hasattr(tc, 'to_dict') else tc for tc in response_message.tool_calls])
                    
                    # Add tool responses to conversation and messages
                    self.conversation_history.extend(tool_responses)
                    for tool_resp in tool_responses:
                        messages.append({
                            "role": "tool",
                            "content": tool_resp.content,
                            "tool_call_id": tool_resp.tool_call_id,
                            "name": tool_resp.name
                        })
                    
                    # Add assistant message to messages for next iteration
                    messages.append({
                        "role": "assistant",
                        "content": assistant_msg.content,
                        "tool_calls": assistant_msg.tool_calls
                    })
                    
                else:
                    # No more function calls, conversation is complete
                    conversation_active = False
                    final_response = response_message.content
                    
                    # If no content but there were function calls, ask for summary
                    if not final_response and self.function_call_count > 0:
                        messages.append({
                            "role": "user", 
                            "content": "Please provide a summary of the results and any insights."
                        })
                        
                        summary_response = await self.openai_client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=0.3,
                            max_tokens=800
                        )
                        final_response = summary_response.choices[0].message.content
            
            # Prepare response data
            executed_functions = [
                {
                    "name": msg.name,
                    "result_preview": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                }
                for msg in self.conversation_history 
                if msg.role == "tool"
            ]
            
            return {
                "status": "success",
                "response": final_response or "Task completed successfully.",
                "functions_executed": executed_functions,
                "function_call_count": self.function_call_count,
                "conversation_length": len(self.conversation_history),
                "has_more_context": len(self.conversation_history) > 0
            }
            
        except Exception as e:
            logging.error(f"Error in intelligent query processing: {e}")
            return {
                "status": "error", 
                "message": f"Failed to process query intelligently: {str(e)}"
            }

    async def continue_conversation(self, user_input: str) -> Dict[str, Any]:
        """Continue an existing conversation with new user input."""
        return await self.process_query_intelligent(user_input, reset_conversation=False)

    def reset_conversation(self):
        """Reset the conversation history and function call count."""
        self.conversation_history = []
        self.function_call_count = 0
        logging.info("🔄 Conversation history reset")

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation state."""
        function_calls = [msg for msg in self.conversation_history if msg.role == "tool"]
        
        return {
            "total_messages": len(self.conversation_history),
            "function_calls_made": len(function_calls),
            "functions_used": list(set(msg.name for msg in function_calls if msg.name)),
            "conversation_active": len(self.conversation_history) > 0
        }

    # Legacy compatibility methods
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Legacy method - redirects to intelligent processing."""
        return await self.process_query_intelligent(user_query, reset_conversation=True)

def main():
    """Example usage of Intelligent MCP Client."""
    print("🧠 Intelligent MCP Client Test")
    print("=" * 50)
    print()
    print("🔌 Using intelligent function calling with MCP server")
    print("📋 Make sure to start the MCP server first:")
    print("   python mcp_server.py")
    print()
    
    # Create intelligent client
    client = IntelligentMCPClient()
    
    async def test_intelligent_features():
        try:
            print(f"\n🔗 Connecting to MCP server...")
            if not client.connect():
                print("Failed to connect to MCP server")
                return
            
            print("📋 Listing available tools...")
            tools = client.list_tools()
            print(f"Available tools: {[tool.name for tool in tools[:5]]}..." + (f" and {len(tools)-5} more" if len(tools) > 5 else ""))
            
            if tools:
                # Test intelligent query processing
                test_queries = [
                    "Show me my account balance and recent transactions",
                    "What are my pending payments?",
                    "Can you help me understand my financial status?"
                ]
                
                for query in test_queries:
                    print(f"\n🧪 Testing intelligent query: '{query}'")
                    result = await client.process_query_intelligent(query, reset_conversation=True)
                    
                    print(f"Status: {result['status']}")
                    if result['status'] == 'success':
                        print(f"Response: {result['response'][:300]}...")
                        print(f"Functions executed: {len(result.get('functions_executed', []))}")
                        print(f"Function calls: {result.get('function_call_count', 0)}")
                    else:
                        print(f"Error: {result.get('message', 'Unknown error')}")
                    
                    print("-" * 40)
            
        except Exception as e:
            logger.error(f"Error in test: {e}")
            print(f"❌ Error: {e}")
            print("\n💡 Make sure the MCP server is running:")
            print("   python mcp_server.py")
        finally:
            print("\n👋 Test completed")
    
    # Run the async test
    asyncio.run(test_intelligent_features())

if __name__ == "__main__":
    main()
