#!/usr/bin/env python3
"""
FastMCP Web Chatbot Application
A modern web application that provides a beautiful UI for the FastMCP chatbot.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Import our FastMCP client and config
from fastmcp_chatbot_client import FastMCPChatbotClient, ChatMessage
from fastmcp_config import get_config, setup_logging

# Setup logging
setup_logging()

# Get configuration
config = get_config()
logger = logging.getLogger("fastmcp_web_app")

# Create FastAPI app
app = FastAPI(
    title="FastMCP Chatbot",
    description="A modern chatbot powered by FastMCP 2.0",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global FastMCP client
chatbot_client: Optional[FastMCPChatbotClient] = None

class WebSocketManager:
    """Manages WebSocket connections for real-time chat."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_sessions: Dict[str, List[ChatMessage]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str = "default"):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        
        logger.info(f"WebSocket connected for user {user_id}. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected WebSocket clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

# Global WebSocket manager
websocket_manager = WebSocketManager()

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}
    user_id: str = "default"

@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    global chatbot_client
    try:
        logger.info("🚀 Starting FastMCP Web Chatbot Application...")
        
        # Initialize FastMCP client
        chatbot_client = FastMCPChatbotClient()
        await chatbot_client.connect()
        
        logger.info("✅ FastMCP client initialized successfully")
        logger.info("🌐 Web application ready")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global chatbot_client
    if chatbot_client:
        try:
            await chatbot_client.disconnect()
            logger.info("FastMCP client cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

@app.get("/")
async def root():
    """Serve the main UI."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FastMCP Chatbot</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            .chat-container {
                width: 90%;
                max-width: 800px;
                height: 80vh;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .chat-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                text-align: center;
                position: relative;
            }
            
            .chat-header h1 {
                font-size: 24px;
                margin-bottom: 5px;
            }
            
            .chat-header p {
                opacity: 0.9;
                font-size: 14px;
            }
            
            .status-indicator {
                position: absolute;
                top: 20px;
                right: 20px;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #4CAF50;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
            
            .chat-messages {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
                background: #f8f9fa;
            }
            
            .message {
                margin-bottom: 15px;
                display: flex;
                align-items: flex-start;
            }
            
            .message.user {
                justify-content: flex-end;
            }
            
            .message.assistant {
                justify-content: flex-start;
            }
            
            .message-content {
                max-width: 70%;
                padding: 12px 16px;
                border-radius: 18px;
                word-wrap: break-word;
                position: relative;
            }
            
            .message.user .message-content {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-bottom-right-radius: 4px;
            }
            
            .message.assistant .message-content {
                background: white;
                color: #333;
                border: 1px solid #e1e5e9;
                border-bottom-left-radius: 4px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .message-time {
                font-size: 11px;
                opacity: 0.7;
                margin-top: 4px;
            }
            
            .typing-indicator {
                display: none;
                align-items: center;
                color: #666;
                font-style: italic;
                margin-bottom: 15px;
            }
            
            .typing-dots {
                display: inline-block;
                margin-left: 5px;
            }
            
            .typing-dots span {
                display: inline-block;
                width: 4px;
                height: 4px;
                border-radius: 50%;
                background: #666;
                margin: 0 1px;
                animation: typing 1.4s infinite;
            }
            
            .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
            .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
            
            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-10px); }
            }
            
            .chat-input-container {
                padding: 20px;
                background: white;
                border-top: 1px solid #e1e5e9;
            }
            
            .chat-input-wrapper {
                display: flex;
                gap: 10px;
                align-items: center;
            }
            
            .chat-input {
                flex: 1;
                padding: 12px 16px;
                border: 2px solid #e1e5e9;
                border-radius: 25px;
                font-size: 14px;
                outline: none;
                transition: border-color 0.3s;
            }
            
            .chat-input:focus {
                border-color: #667eea;
            }
            
            .send-button {
                padding: 12px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: transform 0.2s;
            }
            
            .send-button:hover {
                transform: translateY(-2px);
            }
            
            .send-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            .tools-panel {
                background: #f8f9fa;
                padding: 15px 20px;
                border-top: 1px solid #e1e5e9;
                display: none;
            }
            
            .tools-panel.show {
                display: block;
            }
            
            .tools-title {
                font-size: 14px;
                font-weight: 600;
                color: #333;
                margin-bottom: 10px;
            }
            
            .tool-buttons {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }
            
            .tool-button {
                padding: 6px 12px;
                background: white;
                border: 1px solid #e1e5e9;
                border-radius: 15px;
                cursor: pointer;
                font-size: 12px;
                color: #666;
                transition: all 0.2s;
            }
            
            .tool-button:hover {
                background: #667eea;
                color: white;
                border-color: #667eea;
            }
            
            .error-message {
                background: #ffebee;
                color: #c62828;
                padding: 10px 15px;
                border-radius: 8px;
                margin-bottom: 15px;
                border-left: 4px solid #c62828;
            }
            
            .success-message {
                background: #e8f5e8;
                color: #2e7d32;
                padding: 10px 15px;
                border-radius: 8px;
                margin-bottom: 15px;
                border-left: 4px solid #2e7d32;
            }
            
            @media (max-width: 600px) {
                .chat-container {
                    width: 95%;
                    height: 90vh;
                }
                
                .message-content {
                    max-width: 85%;
                }
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <div class="status-indicator" id="statusIndicator"></div>
                <h1>FastMCP Chatbot</h1>
                <p>Powered by FastMCP 2.0 • Real-time AI Assistant</p>
            </div>
            
            <div class="chat-messages" id="chatMessages">
                <div class="message assistant">
                    <div class="message-content">
                        <div>Hello! I'm your FastMCP-powered AI assistant. I can help you with various tasks including weather, math calculations, time, web search, todos, and news. How can I assist you today?</div>
                        <div class="message-time" id="welcomeTime"></div>
                    </div>
                </div>
            </div>
            
            <div class="typing-indicator" id="typingIndicator">
                <span>Assistant is typing</span>
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
            
            <div class="tools-panel" id="toolsPanel">
                <div class="tools-title">Quick Actions</div>
                <div class="tool-buttons">
                    <button class="tool-button" onclick="quickAction('weather')">🌤️ Weather</button>
                    <button class="tool-button" onclick="quickAction('time')">🕐 Time</button>
                    <button class="tool-button" onclick="quickAction('math')">🧮 Math</button>
                    <button class="tool-button" onclick="quickAction('news')">📰 News</button>
                    <button class="tool-button" onclick="quickAction('todo')">✅ Todo</button>
                </div>
            </div>
            
            <div class="chat-input-container">
                <div class="chat-input-wrapper">
                    <input type="text" id="messageInput" class="chat-input" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
                    <button id="sendButton" class="send-button" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let isConnected = false;
            let messageCount = 0;
            
            // Initialize
            document.addEventListener('DOMContentLoaded', function() {
                document.getElementById('welcomeTime').textContent = new Date().toLocaleTimeString();
                connectWebSocket();
            });
            
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    isConnected = true;
                    updateStatusIndicator(true);
                    console.log('WebSocket connected');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                };
                
                ws.onclose = function(event) {
                    isConnected = false;
                    updateStatusIndicator(false);
                    console.log('WebSocket disconnected');
                    // Attempt to reconnect after 3 seconds
                    setTimeout(connectWebSocket, 3000);
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    updateStatusIndicator(false);
                };
            }
            
            function updateStatusIndicator(connected) {
                const indicator = document.getElementById('statusIndicator');
                if (connected) {
                    indicator.style.background = '#4CAF50';
                } else {
                    indicator.style.background = '#f44336';
                }
            }
            
            function handleWebSocketMessage(data) {
                hideTypingIndicator();
                
                if (data.type === 'error') {
                    showErrorMessage(data.content);
                } else if (data.type === 'response') {
                    addMessage('assistant', data.content);
                } else if (data.type === 'tool_result') {
                    addMessage('assistant', data.content);
                }
            }
            
            function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                
                if (!message || !isConnected) return;
                
                addMessage('user', message);
                input.value = '';
                
                showTypingIndicator();
                
                // Send via WebSocket
                ws.send(JSON.stringify({
                    type: 'chat',
                    message: message,
                    user_id: 'web_user'
                }));
            }
            
            function handleKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }
            
            function addMessage(role, content) {
                const messagesContainer = document.getElementById('chatMessages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}`;
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                contentDiv.innerHTML = content;
                
                const timeDiv = document.createElement('div');
                timeDiv.className = 'message-time';
                timeDiv.textContent = new Date().toLocaleTimeString();
                
                contentDiv.appendChild(timeDiv);
                messageDiv.appendChild(contentDiv);
                messagesContainer.appendChild(messageDiv);
                
                // Scroll to bottom
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                
                messageCount++;
            }
            
            function showTypingIndicator() {
                document.getElementById('typingIndicator').style.display = 'flex';
                const messagesContainer = document.getElementById('chatMessages');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            
            function hideTypingIndicator() {
                document.getElementById('typingIndicator').style.display = 'none';
            }
            
            function showErrorMessage(message) {
                const messagesContainer = document.getElementById('chatMessages');
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = message;
                messagesContainer.appendChild(errorDiv);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            
            function showSuccessMessage(message) {
                const messagesContainer = document.getElementById('chatMessages');
                const successDiv = document.createElement('div');
                successDiv.className = 'success-message';
                successDiv.textContent = message;
                messagesContainer.appendChild(successDiv);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            
            function quickAction(action) {
                const input = document.getElementById('messageInput');
                switch(action) {
                    case 'weather':
                        input.value = 'What\'s the weather like in New York?';
                        break;
                    case 'time':
                        input.value = 'What time is it in London?';
                        break;
                    case 'math':
                        input.value = 'Calculate 15 * 23 + 45';
                        break;
                    case 'news':
                        input.value = 'Show me the latest technology news';
                        break;
                    case 'todo':
                        input.value = 'Create a todo: Buy groceries';
                        break;
                }
                input.focus();
            }
            
            // Toggle tools panel
            document.addEventListener('keydown', function(event) {
                if (event.ctrlKey && event.key === '/') {
                    event.preventDefault();
                    const toolsPanel = document.getElementById('toolsPanel');
                    toolsPanel.classList.toggle('show');
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            logger.info(f"Received WebSocket message: {message_data}")
            
            if not chatbot_client:
                await websocket_manager.send_personal_message({
                    "type": "error",
                    "content": "Chatbot client not initialized"
                }, websocket)
                continue
            
            try:
                if message_data.get("type") == "chat":
                    # Handle chat message
                    user_message = message_data.get("message", "")
                    user_id = message_data.get("user_id", "default")
                    
                    # Send typing indicator
                    await websocket_manager.send_personal_message({
                        "type": "typing",
                        "content": "Assistant is thinking..."
                    }, websocket)
                    
                    # Process message with FastMCP client
                    response = await chatbot_client.chat(user_message, user_id)
                    
                    # Send response
                    await websocket_manager.send_personal_message({
                        "type": "response",
                        "content": response
                    }, websocket)
                    
                elif message_data.get("type") == "tool_call":
                    # Handle tool call
                    tool_name = message_data.get("tool_name")
                    arguments = message_data.get("arguments", {})
                    
                    result = await chatbot_client.call_tool(tool_name, arguments)
                    
                    if result.get("status") == "success":
                        response_text = result.get("data", {}).get("message", "Tool executed successfully")
                    else:
                        response_text = f"Tool error: {result.get('message', 'Unknown error')}"
                    
                    await websocket_manager.send_personal_message({
                        "type": "tool_result",
                        "content": response_text
                    }, websocket)
                
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket_manager.send_personal_message({
                    "type": "error",
                    "content": f"Processing failed: {str(e)}"
                }, websocket)
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

@app.post("/api/chat")
async def chat_api(request: ChatRequest):
    """REST API endpoint for chat."""
    if not chatbot_client:
        raise HTTPException(status_code=503, detail="Chatbot client not initialized")
    
    try:
        response = await chatbot_client.chat(request.message, request.user_id)
        return {"response": response, "status": "success"}
    except Exception as e:
        logger.error(f"Error in chat API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tool")
async def tool_api(request: ToolRequest):
    """REST API endpoint for tool calls."""
    if not chatbot_client:
        raise HTTPException(status_code=503, detail="Chatbot client not initialized")
    
    try:
        result = await chatbot_client.call_tool(request.tool_name, request.arguments)
        return {"result": result, "status": "success"}
    except Exception as e:
        logger.error(f"Error in tool API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools")
async def list_tools():
    """List available tools."""
    if not chatbot_client:
        raise HTTPException(status_code=503, detail="Chatbot client not initialized")
    
    try:
        tools = chatbot_client.get_available_tools()
        return {"tools": tools, "status": "success"}
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "chatbot_connected": chatbot_client is not None and chatbot_client.connected,
        "websocket_connections": len(websocket_manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "fastmcp_web_app:app",
        host=config.web.host,
        port=config.web.port,
        reload=config.web.debug,
        log_level=config.logging.level.lower()
    )