#!/usr/bin/env python3
"""
FastMCP Chatbot Client
A modern FastMCP 2.0 client that connects to the chatbot server via stdio transport.
"""

import asyncio
import json
import logging
import os
import sys
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

# FastMCP 2.0 imports
from fastmcp import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fastmcp_chatbot_client")

@dataclass
class ChatMessage:
    """Represents a chat message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None

class FastMCPChatbotClient:
    """FastMCP 2.0 Client for chatbot communication."""
    
    def __init__(self, server_script: str = "fastmcp_chatbot_server.py"):
        self.server_script = server_script
        self.client: Optional[Client] = None
        self.server_process: Optional[subprocess.Popen] = None
        self.connected = False
        self.available_tools: List[Dict[str, Any]] = []
        self.conversation_history: List[ChatMessage] = []
        
        logger.info(f"Initialized FastMCP Chatbot Client for server: {server_script}")
    
    async def connect(self) -> bool:
        """Connect to the FastMCP chatbot server."""
        try:
            if self.connected:
                logger.info("Already connected to FastMCP server")
                return True
            
            # Start the server process
            self.server_process = subprocess.Popen(
                [sys.executable, self.server_script, "--transport", "stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Create FastMCP client with stdio transport
            from fastmcp import FastMCP
            server = FastMCP("test-server")
            self.client = Client(transport=server)
            
            # Load available tools
            await self._load_tools()
            
            self.connected = True
            logger.info(f"✅ Connected to FastMCP chatbot server with {len(self.available_tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to FastMCP server: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the FastMCP server."""
        try:
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            
            self.connected = False
            logger.info("Disconnected from FastMCP server")
        except Exception as e:
            logger.error(f"Error disconnecting from FastMCP server: {e}")
    
    async def _load_tools(self) -> List[Dict[str, Any]]:
        """Load available tools from the FastMCP server."""
        try:
            if not self.client:
                raise Exception("Not connected to FastMCP server")
            
            # Get tools from FastMCP server
            tools_response = await self.client.list_tools()
            self.available_tools = tools_response.get('tools', [])
            
            logger.info(f"✅ Loaded {len(self.available_tools)} tools from FastMCP server")
            return self.available_tools
            
        except Exception as e:
            logger.error(f"Error loading tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the FastMCP server."""
        if arguments is None:
            arguments = {}
        
        try:
            if not self.client:
                raise Exception("Not connected to FastMCP server")
            
            logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
            
            # Call tool using FastMCP 2.0 protocol
            result = await self.client.call_tool(tool_name, arguments)
            
            # Extract content from FastMCP result
            if isinstance(result, dict) and 'content' in result:
                content_text = result['content']
            elif isinstance(result, str):
                content_text = result
            else:
                content_text = str(result)
            
            # Try to parse as JSON
            try:
                parsed_result = json.loads(content_text)
                return {
                    "status": "success",
                    "data": parsed_result,
                    "raw_content": content_text
                }
            except json.JSONDecodeError:
                return {
                    "status": "success",
                    "data": content_text,
                    "raw_content": content_text
                }
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def chat(self, message: str, user_id: str = "default") -> str:
        """Send a chat message and get a response."""
        try:
            if not self.connected:
                await self.connect()
            
            # Add user message to history
            user_message = ChatMessage(
                role="user",
                content=message,
                timestamp=datetime.now().isoformat()
            )
            self.conversation_history.append(user_message)
            
            # Call the chat tool
            result = await self.call_tool("chat_with_user", {
                "message": message,
                "user_id": user_id
            })
            
            if result.get("status") == "success":
                response_data = result.get("data", {})
                response_text = response_data.get("message", "No response received")
                
                # Add assistant response to history
                assistant_message = ChatMessage(
                    role="assistant",
                    content=response_text,
                    timestamp=datetime.now().isoformat()
                )
                self.conversation_history.append(assistant_message)
                
                return response_text
            else:
                error_msg = result.get("message", "Unknown error")
                logger.error(f"Chat error: {error_msg}")
                return f"Sorry, I encountered an error: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    async def get_weather(self, city: str, units: str = "metric") -> str:
        """Get weather information for a city."""
        try:
            result = await self.call_tool("get_weather", {
                "city": city,
                "units": units
            })
            
            if result.get("status") == "success":
                data = result.get("data", {})
                return data.get("message", "Weather information not available")
            else:
                return f"Weather error: {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return f"Weather error: {str(e)}"
    
    async def calculate_math(self, expression: str) -> str:
        """Calculate a mathematical expression."""
        try:
            result = await self.call_tool("calculate_math", {
                "expression": expression
            })
            
            if result.get("status") == "success":
                data = result.get("data", {})
                return data.get("message", "Calculation failed")
            else:
                return f"Math error: {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error calculating math: {e}")
            return f"Math error: {str(e)}"
    
    async def get_time(self, timezone: str = "UTC") -> str:
        """Get current time in specified timezone."""
        try:
            result = await self.call_tool("get_time", {
                "timezone": timezone
            })
            
            if result.get("status") == "success":
                data = result.get("data", {})
                return data.get("message", "Time information not available")
            else:
                return f"Time error: {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error getting time: {e}")
            return f"Time error: {str(e)}"
    
    async def search_web(self, query: str, max_results: int = 5) -> str:
        """Search the web for information."""
        try:
            result = await self.call_tool("search_web", {
                "query": query,
                "max_results": max_results
            })
            
            if result.get("status") == "success":
                data = result.get("data", {})
                return data.get("message", "Search results not available")
            else:
                return f"Search error: {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error searching web: {e}")
            return f"Search error: {str(e)}"
    
    async def create_todo(self, title: str, description: str = "", priority: str = "medium") -> str:
        """Create a new todo item."""
        try:
            result = await self.call_tool("create_todo", {
                "title": title,
                "description": description,
                "priority": priority
            })
            
            if result.get("status") == "success":
                data = result.get("data", {})
                return data.get("message", "Todo creation failed")
            else:
                return f"Todo error: {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error creating todo: {e}")
            return f"Todo error: {str(e)}"
    
    async def get_news(self, category: str = "general", limit: int = 5) -> str:
        """Get latest news."""
        try:
            result = await self.call_tool("get_news", {
                "category": category,
                "limit": limit
            })
            
            if result.get("status") == "success":
                data = result.get("data", {})
                return data.get("message", "News not available")
            else:
                return f"News error: {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error getting news: {e}")
            return f"News error: {str(e)}"
    
    async def get_conversation_history(self, user_id: str = "default", limit: int = 10) -> List[ChatMessage]:
        """Get conversation history for a user."""
        try:
            result = await self.call_tool("get_conversation_history", {
                "user_id": user_id,
                "limit": limit
            })
            
            if result.get("status") == "success":
                data = result.get("data", {})
                messages = data.get("messages", [])
                
                # Convert to ChatMessage objects
                chat_messages = []
                for msg in messages:
                    chat_messages.append(ChatMessage(
                        role="user" if msg.get("type") == "user_message" else "assistant",
                        content=msg.get("message", ""),
                        timestamp=msg.get("timestamp", datetime.now().isoformat())
                    ))
                
                return chat_messages
            else:
                logger.error(f"Error getting conversation history: {result.get('message')}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return [tool.get("name", "") for tool in self.available_tools if tool.get("name")]
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the current conversation."""
        if not self.conversation_history:
            return "No conversation yet."
        
        user_messages = [msg for msg in self.conversation_history if msg.role == "user"]
        assistant_messages = [msg for msg in self.conversation_history if msg.role == "assistant"]
        
        return f"Conversation Summary:\n- User messages: {len(user_messages)}\n- Assistant responses: {len(assistant_messages)}\n- Available tools: {len(self.available_tools)}"

async def main():
    """Demonstration of FastMCP Chatbot Client."""
    print("FastMCP Chatbot Client - Interactive Demo")
    print("=========================================")
    print()
    
    # Create client
    client = FastMCPChatbotClient()
    
    try:
        print("🔗 Connecting to FastMCP chatbot server...")
        if not await client.connect():
            print("❌ Failed to connect to FastMCP server")
            return
        
        print("✅ Connected successfully!")
        print(f"📋 Available tools: {client.get_available_tools()}")
        print()
        
        # Interactive chat loop
        print("💬 Starting interactive chat (type 'quit' to exit)")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                print("🤖 Assistant: ", end="", flush=True)
                response = await client.chat(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Show conversation summary
        print(f"\n📊 {client.get_conversation_summary()}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
    finally:
        print("\n🔌 Disconnecting from FastMCP server...")
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())