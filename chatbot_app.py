#!/usr/bin/env python3
"""
Chatbot Application - WebSocket-based UI with Real MCP Protocol
FastAPI application serving the web UI with WebSocket support for real-time communication.
Uses proper MCP protocol for tool calling.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

# Import config or create default
try:
    from config import config
except ImportError:
    # Create default config if not available
    class DefaultConfig:
        LOG_LEVEL = "INFO"
        ENABLE_CORS = True
        CHATBOT_HOST = "localhost"
        CHATBOT_PORT = 8000
        
        def validate(self):
            return True
        
        def get_chatbot_url(self):
            return f"http://{self.CHATBOT_HOST}:{self.CHATBOT_PORT}"
        
        def get_mock_url(self):
            return "http://localhost:8080"
    
    config = DefaultConfig()

from mcp_client_proper_working import ProperMCPClient


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chatbot_app")

app = FastAPI(title="MCP Chatbot", version="1.0")

# CORS middleware
if getattr(config, 'ENABLE_CORS', True):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Global MCP client
mcp_client: Optional[ProperMCPClient] = None


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
    try:
        logger.info("Starting chatbot application...")
        logger.info("🔌 Connecting to MCP server via stdio transport...")
        
        # Create proper MCP client with stdio transport
        mcp_client = ProperMCPClient()
        await mcp_client.connect()
        logger.info("✅ Connected to MCP server via stdio transport")
        
        logger.info("MCP client initialized successfully")
        logger.info(f"Chatbot server starting on {config.get_chatbot_url()}")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global mcp_client
    if mcp_client:
        try:
            await mcp_client.disconnect()
            logger.info("MCP client cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


@app.get("/")
async def root():
    """Serve the main UI."""
    try:
        with open("simple_ui.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        # Fallback simple HTML if file not found
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP Chatbot</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .chat-container { max-width: 800px; margin: 0 auto; }
                .messages { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; }
                .input-area { margin-top: 10px; }
                input[type="text"] { width: 70%; padding: 5px; }
                button { padding: 5px 10px; margin-left: 10px; }
            </style>
        </head>
        <body>
            <div class="chat-container">
                <h1>MCP Chatbot</h1>
                <div id="messages" class="messages"></div>
                <div class="input-area">
                    <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
                    <button onclick="sendMessage()">Send</button>
                </div>
            </div>
            <script>
                const ws = new WebSocket(`ws://${window.location.host}/ws`);
                const messagesDiv = document.getElementById('messages');
                
                ws.onmessage = function(event) {
                    const messageDiv = document.createElement('div');
                    messageDiv.textContent = event.data;
                    messagesDiv.appendChild(messageDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                };
                
                function sendMessage() {
                    const input = document.getElementById('messageInput');
                    if (input.value.trim()) {
                        ws.send(input.value);
                        input.value = '';
                    }
                }
                
                function handleKeyPress(event) {
                    if (event.key === 'Enter') {
                        sendMessage();
                    }
                }
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "mcp_connected": mcp_client is not None}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received message: {data}")
            
            # Parse message data
            try:
                message_data = json.loads(data)
                # Handle different message formats
                if "content" in message_data:
                    user_message = message_data["content"]
                elif "message" in message_data:
                    user_message = message_data["message"]
                else:
                    user_message = str(message_data)
            except json.JSONDecodeError:
                user_message = data
            
            # Ensure user_message is a string
            if not isinstance(user_message, str):
                user_message = str(user_message)
            
            # Send acknowledgment
            await websocket_manager.send_personal_message(
                json.dumps({"type": "user_message", "content": user_message}),
                websocket
            )
            
            if not mcp_client:
                await websocket_manager.send_personal_message(
                    json.dumps({"type": "error", "content": "MCP client not initialized"}),
                    websocket
                )
                continue
            
            try:
                # Check if this is an authentication-related query
                auth_keywords = ['login', 'authenticate', 'credential', 'password', 'username', 'connect', 'setup']
                is_auth_query = any(keyword in user_message.lower() for keyword in auth_keywords)
                
                # Use the new asynchronous query processing
                response = await mcp_client.process_query(user_message)
                
                # Extract the summary from the response dictionary
                response_content = response.get("summary", str(response))
                response_status = response.get("status", "unknown")
                
                # Determine response type based on content
                response_type = "mcp_response"
                if is_auth_query and ("successfully" in response_content.lower() or "authenticated" in response_content.lower()):
                    response_type = "authentication_success"
                elif response_status == "error" or "error" in response_content.lower() or "failed" in response_content.lower():
                    response_type = "error_response"
                
                # Send response back to client
                await websocket_manager.send_personal_message(
                    json.dumps({"type": response_type, "content": response_content}),
                    websocket
                )
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket_manager.send_personal_message(
                    json.dumps({"type": "error", "error": f"Processing failed: {str(e)}"}),
                    websocket
                )
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


@app.get("/api/tools")
async def list_tools():
    """List available MCP tools via MCP client."""
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    try:
        # Use MCP client to list tools
        tools = await mcp_client.list_tools()
        tools_info = []
        for tool in tools:
            tools_info.append({
                "name": getattr(tool, "name", None) or (tool.get("name") if isinstance(tool, dict) else None),
                "description": getattr(tool, "description", None) or (tool.get("description") if isinstance(tool, dict) else None),
                "input_schema": getattr(tool, "inputSchema", None) or (tool.get("inputSchema") if isinstance(tool, dict) else {})
            })
        return {"tools": tools_info}
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CredentialsRequest(BaseModel):
    """Credentials configuration request (values sourced from environment variables)."""
    username: str
    password: str



@app.post("/credentials")
async def set_credentials(credentials: CredentialsRequest):
    """Set API credentials via MCP client."""
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    try:
        # Use MCP client to set credentials
        result = await mcp_client.set_credentials(
            username=credentials.username,
            password=credentials.password,
            api_key=getattr(config, 'DEFAULT_API_KEY_VALUE', None)
        )
        
        if result.get('status') == 'success':
            return {"status": "success", "message": "Credentials stored successfully"}
        else:
            raise ValueError(f"Failed to set credentials: {result.get('message')}")
            
    except Exception as e:
        logger.error(f"Error setting credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/login")
async def login():
    """Perform login via MCP client."""
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    try:
        # Use MCP client to perform login
        result = await mcp_client.perform_login()
        if result.get("status") == "success":
            return {"status": "success", "message": "Login successful"}
        else:
            return {"status": "error", "message": result.get("message", "Login failed")}
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Validate configuration
    try:
        config.validate()
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        exit(1)
    
    # Start server
    # host and port are now derived from argparse and config globally
    
    # logger.info(f"Starting chatbot server on {CHATBOT_HOST}:{CHATBOT_PORT}")
    # uvicorn.run(
    #     "chatbot_app:app",
    #     host=CHATBOT_HOST,
    #     port=CHATBOT_PORT,
    #     log_level=config.LOG_LEVEL.lower(),
    #     reload=False
    # )

    logger.info(f"Starting uvicorn for chatbot_app on {config.CHATBOT_HOST}:{config.CHATBOT_PORT}")
    uvicorn.run("chatbot_app:app", host=config.CHATBOT_HOST, port=config.CHATBOT_PORT, reload=True, log_level="info")
