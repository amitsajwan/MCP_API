#!/usr/bin/env python3
"""
FastMCP Chatbot Server
A modern FastMCP 2.0 server that provides chatbot capabilities with tool calling.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

# FastMCP 2.0 imports
from fastmcp import FastMCP

# Import configuration
from fastmcp_config import get_config, setup_logging

# Setup logging
setup_logging()
config = get_config()
logger = logging.getLogger("fastmcp_chatbot_server")

# Create FastMCP app
app = FastMCP("chatbot-server")

class ChatbotServer:
    """FastMCP 2.0 Chatbot Server with tool capabilities."""
    
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.user_sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.available_tools = [
            "get_weather",
            "calculate_math",
            "get_time",
            "search_web",
            "send_email",
            "create_todo",
            "get_news"
        ]
        
        logger.info("🚀 Initializing FastMCP Chatbot Server...")
        self._register_tools()
        logger.info(f"✅ FastMCP Chatbot Server initialized with {len(self.available_tools)} tools")
    
    def _register_tools(self):
        """Register all available tools with FastMCP."""
        
        @app.tool()
        async def get_weather(city: str, units: str = "metric") -> str:
            """Get current weather for a specific city."""
            try:
                # Simulate weather API call
                weather_data = {
                    "city": city,
                    "temperature": 22,
                    "condition": "sunny",
                    "humidity": 65,
                    "units": units,
                    "timestamp": datetime.now().isoformat()
                }
                
                response = {
                    "status": "success",
                    "data": weather_data,
                    "message": f"Weather in {city}: {weather_data['temperature']}°C, {weather_data['condition']}"
                }
                
                logger.info(f"Weather requested for {city}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting weather: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)
        
        @app.tool()
        async def calculate_math(expression: str) -> str:
            """Calculate a mathematical expression safely."""
            try:
                # Simple safe math evaluation (in production, use a proper math parser)
                allowed_chars = set('0123456789+-*/.() ')
                if not all(c in allowed_chars for c in expression):
                    raise ValueError("Invalid characters in expression")
                
                result = eval(expression)
                
                response = {
                    "status": "success",
                    "expression": expression,
                    "result": result,
                    "message": f"{expression} = {result}"
                }
                
                logger.info(f"Math calculation: {expression} = {result}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error calculating math: {e}")
                return json.dumps({"status": "error", "message": f"Math error: {str(e)}"}, indent=2)
        
        @app.tool()
        async def get_time(timezone: str = "UTC") -> str:
            """Get current time in specified timezone."""
            try:
                from datetime import datetime
                import pytz
                
                if timezone == "UTC":
                    tz = pytz.UTC
                else:
                    tz = pytz.timezone(timezone)
                
                current_time = datetime.now(tz)
                
                response = {
                    "status": "success",
                    "timezone": timezone,
                    "time": current_time.isoformat(),
                    "formatted": current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                    "message": f"Current time in {timezone}: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                }
                
                logger.info(f"Time requested for {timezone}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting time: {e}")
                return json.dumps({"status": "error", "message": f"Timezone error: {str(e)}"}, indent=2)
        
        @app.tool()
        async def search_web(query: str, max_results: int = 5) -> str:
            """Search the web for information (simulated)."""
            try:
                # Simulate web search results
                search_results = [
                    {
                        "title": f"Search Result 1 for '{query}'",
                        "url": f"https://example.com/result1",
                        "snippet": f"This is a simulated search result for '{query}'. It contains relevant information about the topic."
                    },
                    {
                        "title": f"Search Result 2 for '{query}'",
                        "url": f"https://example.com/result2",
                        "snippet": f"Another simulated result for '{query}' with additional details and context."
                    }
                ]
                
                response = {
                    "status": "success",
                    "query": query,
                    "results": search_results[:max_results],
                    "total_results": len(search_results),
                    "message": f"Found {len(search_results)} results for '{query}'"
                }
                
                logger.info(f"Web search for: {query}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error searching web: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)
        
        @app.tool()
        async def send_email(to: str, subject: str, body: str) -> str:
            """Send an email (simulated)."""
            try:
                # Simulate email sending
                email_data = {
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "timestamp": datetime.now().isoformat(),
                    "status": "sent"
                }
                
                response = {
                    "status": "success",
                    "data": email_data,
                    "message": f"Email sent to {to} with subject '{subject}'"
                }
                
                logger.info(f"Email sent to {to}: {subject}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error sending email: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)
        
        @app.tool()
        async def create_todo(title: str, description: str = "", priority: str = "medium") -> str:
            """Create a new todo item."""
            try:
                todo_id = f"todo_{len(self.conversation_history) + 1}"
                todo_item = {
                    "id": todo_id,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                }
                
                # Store in conversation history
                self.conversation_history.append({
                    "type": "todo_created",
                    "data": todo_item,
                    "timestamp": datetime.now().isoformat()
                })
                
                response = {
                    "status": "success",
                    "data": todo_item,
                    "message": f"Todo created: {title}"
                }
                
                logger.info(f"Todo created: {title}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error creating todo: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)
        
        @app.tool()
        async def get_news(category: str = "general", limit: int = 5) -> str:
            """Get latest news (simulated)."""
            try:
                # Simulate news data
                news_items = [
                    {
                        "title": f"Breaking News: {category.title()} Update",
                        "summary": f"Latest developments in {category} sector",
                        "source": "News Agency",
                        "published_at": datetime.now().isoformat()
                    },
                    {
                        "title": f"Analysis: {category.title()} Trends",
                        "summary": f"Expert analysis of current {category} trends",
                        "source": "Financial Times",
                        "published_at": datetime.now().isoformat()
                    }
                ]
                
                response = {
                    "status": "success",
                    "category": category,
                    "articles": news_items[:limit],
                    "count": len(news_items[:limit]),
                    "message": f"Found {len(news_items[:limit])} news articles in {category}"
                }
                
                logger.info(f"News requested for category: {category}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting news: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)
        
        @app.tool()
        async def chat_with_user(message: str, user_id: str = "default") -> str:
            """Main chat function that processes user messages and provides responses."""
            try:
                # Add message to conversation history
                self.conversation_history.append({
                    "type": "user_message",
                    "user_id": user_id,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Simple response generation based on message content
                message_lower = message.lower()
                
                if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
                    response_text = "Hello! I'm your FastMCP chatbot assistant. How can I help you today?"
                elif any(word in message_lower for word in ["weather", "temperature", "forecast"]):
                    response_text = "I can help you get weather information! Just tell me which city you'd like to know about."
                elif any(word in message_lower for word in ["calculate", "math", "compute", "solve"]):
                    response_text = "I can help with math calculations! Just give me an expression to calculate."
                elif any(word in message_lower for word in ["time", "clock", "date"]):
                    response_text = "I can tell you the current time! Let me know if you want a specific timezone."
                elif any(word in message_lower for word in ["search", "find", "look up"]):
                    response_text = "I can search the web for information! What would you like me to search for?"
                elif any(word in message_lower for word in ["email", "send", "message"]):
                    response_text = "I can help you send emails! Just provide the recipient, subject, and message."
                elif any(word in message_lower for word in ["todo", "task", "reminder"]):
                    response_text = "I can help you create todo items! Just tell me what you need to remember."
                elif any(word in message_lower for word in ["news", "latest", "current events"]):
                    response_text = "I can get you the latest news! What category are you interested in?"
                else:
                    response_text = "I understand you're asking about something. I have several tools available to help you. You can ask me about weather, math calculations, time, web search, emails, todos, or news. What would you like to do?"
                
                # Add response to conversation history
                self.conversation_history.append({
                    "type": "bot_response",
                    "user_id": user_id,
                    "message": response_text,
                    "timestamp": datetime.now().isoformat()
                })
                
                response = {
                    "status": "success",
                    "user_id": user_id,
                    "message": response_text,
                    "available_tools": self.available_tools,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"Chat response generated for user {user_id}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error in chat: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)
        
        @app.tool()
        async def get_conversation_history(user_id: str = "default", limit: int = 10) -> str:
            """Get conversation history for a user."""
            try:
                user_messages = [
                    msg for msg in self.conversation_history 
                    if msg.get("user_id") == user_id
                ][-limit:]
                
                response = {
                    "status": "success",
                    "user_id": user_id,
                    "messages": user_messages,
                    "count": len(user_messages),
                    "message": f"Retrieved {len(user_messages)} messages for user {user_id}"
                }
                
                logger.info(f"Conversation history requested for user {user_id}")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting conversation history: {e}")
                return json.dumps({"status": "error", "message": str(e)}, indent=2)

def main():
    """Main entry point for the FastMCP Chatbot Server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FastMCP Chatbot Server")
    parser.add_argument("--transport", default=config.server.transport, choices=["stdio", "http"])
    parser.add_argument("--host", default=config.server.host)
    parser.add_argument("--port", type=int, default=config.server.port)
    
    args = parser.parse_args()
    
    try:
        # Create server instance
        server = ChatbotServer()
        
        if args.transport == "stdio":
            logger.info("🚀 Starting FastMCP Chatbot Server with stdio transport")
            app.run(transport="stdio")
        elif args.transport == "http":
            logger.info(f"🌐 Starting FastMCP Chatbot Server on http://{args.host}:{args.port}")
            app.run(transport="http", host=args.host, port=args.port)
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())