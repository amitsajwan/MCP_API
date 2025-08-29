#!/usr/bin/env python3
"""
Chatbot Application - WebSocket-based UI with Real MCP Protocol
FastAPI application serving the web UI with WebSocket support for real-time communication.
Uses proper MCP protocol for tool calling.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from config import config
from mcp_client import MCPClient


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chatbot_app")

app = FastAPI(title="MCP Chatbot", version="1.0")

# CORS middleware
if config.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Global MCP client
mcp_client: Optional[MCPClient] = None


class ChatMessage(BaseModel):
    """Chat message model."""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    status: str
    message: str
    reasoning: Optional[str] = None
    plan: Optional[List[Dict[str, Any]]] = None
    results: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None


class WebSocketManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket client."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSocket clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Global WebSocket manager
websocket_manager = WebSocketManager()


@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    global mcp_client
    mcp_client = MCPClient()
    
    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed")
        raise RuntimeError("Invalid configuration")
    
    logger.info("✅ Chatbot application started")
    logger.info(f"🔧 Configuration: {config.get_chatbot_url()}")
    logger.info(f"🔌 MCP Server: Using stdio transport")
    logger.info(f"🎭 Mock API: {config.get_mock_url()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global mcp_client
    if mcp_client:
        await mcp_client.disconnect()
    logger.info("🛑 Chatbot application shutdown")


@app.get("/")
async def root():
    """Serve the main chat interface."""
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Chatbot - Real-time AI Assistant</title>
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
            align-items: center;
            justify-content: center;
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
        }
        
        .chat-header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        
        .chat-header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease-in;
        }
        
        .message.user {
            text-align: right;
        }
        
        .message.assistant {
            text-align: left;
        }
        
        .message-content {
            display: inline-block;
            max-width: 70%;
            padding: 15px 20px;
            border-radius: 20px;
            word-wrap: break-word;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .message.assistant .message-content {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
        }
        
        .reasoning-section {
            margin-top: 15px;
            padding: 15px;
            background: #f0f8ff;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        
        .reasoning-title {
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
            font-size: 14px;
        }
        
        .plan-section {
            margin-top: 10px;
            padding: 10px;
            background: #fff3cd;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }
        
        .plan-title {
            font-weight: bold;
            color: #856404;
            margin-bottom: 8px;
            font-size: 13px;
        }
        
        .plan-item {
            margin: 5px 0;
            padding: 5px 10px;
            background: white;
            border-radius: 5px;
            font-size: 12px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-connecting {
            background: #ffc107;
            animation: pulse 1s infinite;
        }
        
        .status-connected {
            background: #28a745;
        }
        
        .status-disconnected {
            background: #dc3545;
        }
        
        .chat-input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        
        .chat-input-form {
            display: flex;
            gap: 10px;
        }
        
        .chat-input {
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .chat-input:focus {
            border-color: #667eea;
        }
        
        .send-button {
            padding: 15px 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
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
        
        .typing-indicator {
            display: none;
            padding: 15px 20px;
            background: white;
            border-radius: 20px;
            border: 1px solid #e0e0e0;
            margin-bottom: 20px;
            text-align: left;
        }
        
        .typing-dots {
            display: inline-block;
        }
        
        .typing-dots span {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #667eea;
            margin: 0 2px;
            animation: typing 1.4s infinite ease-in-out;
        }
        
        .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
        .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        @keyframes typing {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #f5c6cb;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>🤖 MCP AI Assistant</h1>
            <p>
                <span class="status-indicator" id="statusIndicator"></span>
                <span id="statusText">Connecting...</span>
            </p>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message assistant">
                <div class="message-content">
                    👋 Hello! I'm your AI assistant powered by MCP (Model Context Protocol). 
                    I can help you interact with financial APIs and provide intelligent responses. 
                    What would you like to know?
                </div>
            </div>
        </div>
        
        <div class="chat-input-container">
            <form class="chat-input-form" id="chatForm">
                <input type="text" class="chat-input" id="messageInput" 
                       placeholder="Ask me anything about your financial data..." 
                       autocomplete="off" disabled>
                <button type="submit" class="send-button" id="sendButton" disabled>
                    Send
                </button>
            </form>
        </div>
    </div>

    <script>
        let ws = null;
        let isConnected = false;
        
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const chatForm = document.getElementById('chatForm');
        
        function updateStatus(status, text) {
            statusIndicator.className = 'status-indicator status-' + status;
            statusText.textContent = text;
        }
        
        function addMessage(content, type, reasoning = null, plan = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            
            let html = `<div class="message-content">${content}</div>`;
            
            if (reasoning) {
                html += `
                    <div class="reasoning-section">
                        <div class="reasoning-title">🤔 Reasoning</div>
                        <div>${reasoning}</div>
                    </div>
                `;
            }
            
            if (plan && plan.length > 0) {
                html += `
                    <div class="plan-section">
                        <div class="plan-title">📋 Execution Plan</div>
                        ${plan.map(item => `
                            <div class="plan-item">
                                <strong>${item.tool_name}</strong>: ${item.reason || 'No reason provided'}
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            
            messageDiv.innerHTML = html;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function showTypingIndicator() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'typing-indicator';
            typingDiv.id = 'typingIndicator';
            typingDiv.innerHTML = `
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                AI is thinking...
            `;
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function hideTypingIndicator() {
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                isConnected = true;
                updateStatus('connected', 'Connected');
                messageInput.disabled = false;
                sendButton.disabled = false;
                messageInput.focus();
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'typing_start') {
                    showTypingIndicator();
                } else if (data.type === 'typing_end') {
                    hideTypingIndicator();
                } else if (data.type === 'message') {
                    hideTypingIndicator();
                    addMessage(data.content, 'assistant', data.reasoning, data.plan);
                } else if (data.type === 'error') {
                    hideTypingIndicator();
                    addMessage(`❌ Error: ${data.content}`, 'assistant');
                }
            };
            
            ws.onclose = function() {
                isConnected = false;
                updateStatus('disconnected', 'Disconnected');
                messageInput.disabled = true;
                sendButton.disabled = true;
                
                // Try to reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateStatus('disconnected', 'Connection Error');
            };
        }
        
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const message = messageInput.value.trim();
            if (!message || !isConnected) return;
            
            // Add user message
            addMessage(message, 'user');
            
            // Send message via WebSocket
            ws.send(JSON.stringify({
                type: 'message',
                content: message
            }));
            
            // Clear input
            messageInput.value = '';
        });
        
        // Initialize connection
        updateStatus('connecting', 'Connecting...');
        connectWebSocket();
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'visible' && !isConnected) {
                connectWebSocket();
            }
        });
    </script>
</body>
</html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "message":
                await process_chat_message(websocket, message_data.get("content", ""))
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


async def process_chat_message(websocket: WebSocket, message: str):
    """Process a chat message and send response via WebSocket."""
    global mcp_client
    
    if not mcp_client:
        await websocket_manager.send_personal_message(
            json.dumps({"type": "error", "content": "MCP client not initialized"}),
            websocket
        )
        return
    
    try:
        # Send typing indicator
        await websocket_manager.send_personal_message(
            json.dumps({"type": "typing_start"}),
            websocket
        )
        
        # Process the message
        result = await mcp_client.process_query(message)
        
        # Stop typing indicator
        await websocket_manager.send_personal_message(
            json.dumps({"type": "typing_end"}),
            websocket
        )
        
        if result.get("status") == "success":
            # Send success response with reasoning and plan
            response_data = {
                "type": "message",
                "content": result.get("summary", "No response generated"),
                "reasoning": format_reasoning(result),
                "plan": result.get("plan", [])
            }
        else:
            # Send error response
            response_data = {
                "type": "error",
                "content": result.get("message", "Unknown error occurred")
            }
        
        await websocket_manager.send_personal_message(
            json.dumps(response_data),
            websocket
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        await websocket_manager.send_personal_message(
            json.dumps({"type": "error", "content": f"Error: {str(e)}"}),
            websocket
        )


def format_reasoning(result: Dict[str, Any]) -> str:
    """Format the reasoning in a human-readable way."""
    reasoning_parts = []
    
    # Add plan summary
    plan = result.get("plan", [])
    if plan:
        reasoning_parts.append(f"I analyzed your request and planned to execute {len(plan)} tool(s):")
        for i, tool_call in enumerate(plan, 1):
            reasoning_parts.append(f"{i}. {tool_call.get('tool_name', 'Unknown tool')}: {tool_call.get('reason', 'No reason provided')}")
    
    # Add execution results
    results = result.get("results", [])
    if results:
        successful = sum(1 for r in results if r.get("success"))
        total = len(results)
        reasoning_parts.append(f"\nExecution completed: {successful}/{total} tools succeeded.")
        
        if successful < total:
            failed_tools = [r.get("tool_name") for r in results if not r.get("success")]
            reasoning_parts.append(f"Failed tools: {', '.join(failed_tools)}")
    
    return "\n".join(reasoning_parts) if reasoning_parts else "No detailed reasoning available."


@app.get("/status")
async def get_status():
    """Get application status."""
    return {
        "status": "running",
        "mcp_server": "stdio transport",
        "mock_api": config.get_mock_url(),
        "websocket_connections": len(websocket_manager.active_connections),
        "auth_mode": "Azure AD Token Provider" if config.USE_AZURE_AD_TOKEN_PROVIDER else "API Key"
    }


@app.get("/tools")
async def get_tools():
    """Get available tools."""
    global mcp_client
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    try:
        tools = await mcp_client.list_tools()
        # Convert MCP Tool objects to dict format for JSON serialization
        tools_data = []
        for tool in tools:
            tools_data.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })
        return {"tools": tools_data}
    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/assistant/chat")
async def chat_endpoint(request: ChatMessage):
    """Legacy REST endpoint for chat (for backward compatibility)."""
    global mcp_client
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    try:
        result = await mcp_client.process_query(request.message)
        
        return ChatResponse(
            status=result.get("status", "error"),
            message=result.get("summary", "No response generated"),
            reasoning=format_reasoning(result),
            plan=result.get("plan", []),
            results=result.get("results", []),
            session_id=request.session_id
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Chatbot Application")
    parser.add_argument("--host", default=config.CHATBOT_HOST)
    parser.add_argument("--port", type=int, default=config.CHATBOT_PORT)
    
    args = parser.parse_args()
    
    # Validate configuration
    if not config.validate():
        print("❌ Configuration validation failed")
        return 1
    
    print(f"🚀 Starting Chatbot Application on {args.host}:{args.port}")
    print(f"🔧 Configuration: {config.get_chatbot_url()}")
    print(f"🔌 MCP Server: Using stdio transport")
    print(f"🎭 Mock API: {config.get_mock_url()}")
    print(f"🌐 WebSocket: ws://{args.host}:{args.port}/ws")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=config.LOG_LEVEL.lower()
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
