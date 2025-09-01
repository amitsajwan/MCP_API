#!/usr/bin/env python3
"""
Chatbot Application - Fixed Version with Better Error Handling
Critical fixes:
- Proper credentials handling and validation
- Better error messages and debugging
- Connection monitoring and retry logic
- Fixed API endpoints
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
    class DefaultConfig:
        LOG_LEVEL = "INFO"
        ENABLE_CORS = True
        CHATBOT_HOST = "0.0.0.0"
        CHATBOT_PORT = 8080
        DEFAULT_API_KEY_NAME = None
        DEFAULT_API_KEY_VALUE = None
        DEFAULT_LOGIN_URL = "http://localhost:8080/auth/login"
        
        def validate(self):
            return True
        
        def get_chatbot_url(self):
            return f"http://{self.CHATBOT_HOST}:{self.CHATBOT_PORT}"
    
    config = DefaultConfig()

from mcp_client import MCPClient, MCPConnectionError

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
mcp_client: Optional[MCPClient] = None
connection_status = {"healthy": False, "last_check": None, "error": None}


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    status: str
    message: str
    reasoning: Optional[str] = None
    plan: Optional[List[Dict[str, Any]]] = None
    results: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None


class CredentialsRequest(BaseModel):
    username: str
    password: str


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)


websocket_manager = WebSocketManager()


async def ensure_mcp_client():
    """Ensure MCP client is available and connected"""
    global mcp_client, connection_status
    
    if mcp_client is None:
        mcp_client = MCPClient()
    
    # Check if connection is healthy
    if not await mcp_client.health_check():
        logger.info("MCP connection unhealthy, attempting to reconnect...")
        try:
            success = await mcp_client.connect_with_retry(max_retries=3)
            connection_status["healthy"] = success
            connection_status["last_check"] = asyncio.get_event_loop().time()
            
            if not success:
                connection_status["error"] = "Failed to connect to MCP server"
                raise MCPConnectionError("Failed to establish MCP connection")
            else:
                connection_status["error"] = None
                logger.info("✅ MCP connection restored")
                
        except Exception as e:
            connection_status["healthy"] = False
            connection_status["error"] = str(e)
            logger.error(f"Failed to restore MCP connection: {e}")
            raise
    
    return mcp_client


@app.on_event("startup")
async def startup_event():
    """Initialize the application with better error handling"""
    global mcp_client
    
    try:
        logger.info("🚀 Starting chatbot application...")
        
        # Initialize MCP client with retry logic
        mcp_client = MCPClient()
        success = await mcp_client.connect_with_retry(max_retries=3)
        
        if success:
            # Test by listing tools
            tools = await mcp_client.list_tools()
            logger.info(f"✅ MCP client initialized with {len(tools)} tools")
            connection_status["healthy"] = True
            connection_status["error"] = None
        else:
            logger.warning("⚠️ Failed to connect to MCP server during startup")
            connection_status["healthy"] = False
            connection_status["error"] = "Failed to connect during startup"
            
        logger.info(f"🌐 Chatbot server starting on {config.get_chatbot_url()}")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        connection_status["healthy"] = False
        connection_status["error"] = str(e)
        # Don't raise - allow server to start even if MCP connection fails


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global mcp_client
    if mcp_client:
        try:
            await mcp_client.disconnect()
            logger.info("✅ MCP client cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


@app.get("/")
async def root():
    """Serve the main UI with connection status"""
    try:
        with open("simple_ui.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        # Enhanced fallback HTML with better error handling
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>MCP Chatbot</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                :root { color-scheme: dark; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                    margin: 0; background: #111; color: #eee; 
                    display: flex; flex-direction: column; height: 100vh;
                }
                .header { padding: 1rem; background: #1a1a1a; border-bottom: 1px solid #333; }
                .status { font-size: 0.8rem; opacity: 0.7; margin-top: 0.5rem; }
                .status.healthy { color: #4ade80; }
                .status.error { color: #f87171; }
                .chat-container { flex: 1; display: flex; flex-direction: column; max-width: 800px; margin: 0 auto; width: 100%; }
                .messages { flex: 1; overflow-y: auto; padding: 1rem; }
                .message { margin-bottom: 1rem; }
                .message.user { text-align: right; }
                .message.assistant { text-align: left; }
                .message.system { text-align: center; font-style: italic; opacity: 0.7; }
                .bubble { 
                    display: inline-block; padding: 0.75rem 1rem; border-radius: 1rem; 
                    max-width: 70%; white-space: pre-wrap; word-break: break-word;
                }
                .user .bubble { background: #0066cc; color: white; }
                .assistant .bubble { background: #2a2a2a; border: 1px solid #444; }
                .system .bubble { background: #444; }
                .input-area { 
                    padding: 1rem; background: #1a1a1a; border-top: 1px solid #333;
                    display: flex; gap: 0.5rem;
                }
                input[type="text"] { 
                    flex: 1; padding: 0.75rem; border: 1px solid #444; border-radius: 0.5rem;
                    background: #222; color: #eee; font-size: 1rem;
                }
                input[type="text"]:focus { outline: 2px solid #0066cc; border-color: #0066cc; }
                button { 
                    padding: 0.75rem 1.5rem; border: none; border-radius: 0.5rem;
                    background: #0066cc; color: white; cursor: pointer; font-size: 1rem;
                }
                button:hover { background: #0052a3; }
                button:disabled { opacity: 0.5; cursor: not-allowed; }
                .error { color: #f87171; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>MCP Chatbot</h1>
                <div id="status" class="status">Checking connection...</div>
            </div>
            
            <div class="chat-container">
                <div id="messages" class="messages">
                    <div class="message system">
                        <div class="bubble">Welcome! Checking MCP server connection...</div>
                    </div>
                </div>
                
                <div class="input-area">
                    <input type="text" id="messageInput" placeholder="Type your message..." 
                           onkeypress="handleKeyPress(event)" disabled>
                    <button onclick="sendMessage()" id="sendButton" disabled>Send</button>
                </div>
            </div>

            <script>
                let isConnected = false;
                
                // Check health on load
                checkHealth();
                
                async function checkHealth() {
                    try {
                        const response = await fetch('/health');
                        const health = await response.json();
                        updateStatus(health);
                    } catch (error) {
                        updateStatus({ status: 'error', error: 'Failed to connect to server' });
                    }
                }
                
                function updateStatus(health) {
                    const statusEl = document.getElementById('status');
                    const messageInput = document.getElementById('messageInput');
                    const sendButton = document.getElementById('sendButton');
                    
                    if (health.status === 'healthy' && health.mcp_connected) {
                        statusEl.textContent = '✅ Connected to MCP server';
                        statusEl.className = 'status healthy';
                        messageInput.disabled = false;
                        sendButton.disabled = false;
                        isConnected = true;
                        
                        if (document.querySelectorAll('.message').length === 1) {
                            addMessage('system', 'MCP server connected! You can now send messages.');
                        }
                    } else {
                        const errorMsg = health.error || 'MCP server not connected';
                        statusEl.textContent = '❌ ' + errorMsg;
                        statusEl.className = 'status error';
                        messageInput.disabled = true;
                        sendButton.disabled = true;
                        isConnected = false;
                        
                        addMessage('system', 'MCP server not available. ' + errorMsg);
                    }
                }
                
                function addMessage(role, content) {
                    const messagesDiv = document.getElementById('messages');
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message ' + role;
                    
                    const bubbleDiv = document.createElement('div');
                    bubbleDiv.className = 'bubble';
                    bubbleDiv.textContent = content;
                    
                    messageDiv.appendChild(bubbleDiv);
                    messagesDiv.appendChild(messageDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
                
                async function sendMessage() {
                    const input = document.getElementById('messageInput');
                    const message = input.value.trim();
                    
                    if (!message || !isConnected) return;
                    
                    // Add user message
                    addMessage('user', message);
                    input.value = '';
                    
                    // Disable input while processing
                    input.disabled = true;
                    document.getElementById('sendButton').disabled = true;
                    
                    try {
                        const response = await fetch('/chat', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message })
                        });
                        
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }
                        
                        const result = await response.json();
                        
                        if (result.status === 'success') {
                            addMessage('assistant', result.message);
                        } else {
                            addMessage('assistant', 'Error: ' + (result.message || 'Unknown error'));
                        }
                        
                    } catch (error) {
                        addMessage('system', 'Network error: ' + error.message);
                        checkHealth(); // Recheck connection
                    } finally {
                        // Re-enable input
                        if (isConnected) {
                            input.disabled = false;
                            document.getElementById('sendButton').disabled = false;
                            input.focus();
                        }
                    }
                }
                
                function handleKeyPress(event) {
                    if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        sendMessage();
                    }
                }
                
                // Recheck health every 30 seconds
                setInterval(checkHealth, 30000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with detailed status"""
    global mcp_client, connection_status
    
    health_info = {
        "status": "healthy" if connection_status.get("healthy", False) else "error",
        "mcp_connected": False,
        "tools_count": 0,
        "error": connection_status.get("error"),
        "last_check": connection_status.get("last_check")
    }
    
    try:
        if mcp_client:
            # Quick health check
            is_healthy = await mcp_client.health_check()
            health_info["mcp_connected"] = is_healthy
            
            if is_healthy:
                # Get tools count
                tools = await mcp_client.list_tools()
                health_info["tools_count"] = len(tools)
                health_info["status"] = "healthy"
            else:
                health_info["error"] = "MCP server not responding"
                
    except Exception as e:
        health_info["error"] = str(e)
        health_info["status"] = "error"
    
    return health_info


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with better error handling"""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")
            
            # Send acknowledgment
            await websocket_manager.send_personal_message(
                json.dumps({"type": "user_message", "content": data}),
                websocket
            )
            
            try:
                # Ensure MCP client is available
                client = await ensure_mcp_client()
                
                # Process message
                response = await client.process_message(data)
                
                # Send response
                await websocket_manager.send_personal_message(
                    json.dumps({"type": "bot_response", "content": response}),
                    websocket
                )
                
            except MCPConnectionError as e:
                error_msg = f"MCP connection error: {e}"
                logger.error(error_msg)
                await websocket_manager.send_personal_message(
                    json.dumps({"type": "error", "content": error_msg}),
                    websocket
                )
                
            except Exception as e:
                error_msg = f"Processing error: {str(e)}"
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket_manager.send_personal_message(
                    json.dumps({"type": "error", "content": error_msg}),
                    websocket
                )
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


@app.post("/chat")
async def chat_endpoint(message: ChatMessage):
    """HTTP endpoint for chat functionality with better error handling"""
    try:
        # Ensure MCP client is available
        client = await ensure_mcp_client()
        
        # Process message
        response = await client.process_message(message.message)
        
        return ChatResponse(
            status="success",
            message=response,
            session_id=message.session_id
        )
        
    except MCPConnectionError as e:
        logger.error(f"MCP connection error in chat endpoint: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"MCP server unavailable: {str(e)}"
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal error: {str(e)}"
        )


@app.get("/api/tools")
async def list_tools():
    """List available MCP tools with error handling"""
    try:
        client = await ensure_mcp_client()
        tools = await client.list_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
                for tool in tools
            ]
        }
        
    except MCPConnectionError as e:
        logger.error(f"MCP connection error listing tools: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"MCP server unavailable: {str(e)}"
        )
        
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal error: {str(e)}"
        )


@app.post("/credentials")
async def set_credentials(credentials: CredentialsRequest):
    """Set API credentials with proper validation"""
    try:
        # Ensure MCP client is available
        client = await ensure_mcp_client()
        
        logger.info(f"Setting credentials for user: {credentials.username}")
        
        # Call server-side set_credentials tool
        result = await client.call_tool(
            "set_credentials",
            {
                "username": credentials.username,
                "password": credentials.password,
                "api_key_name": getattr(config, 'DEFAULT_API_KEY_NAME', None),
                "api_key_value": getattr(config, 'DEFAULT_API_KEY_VALUE', None),
                "login_url": getattr(config, 'DEFAULT_LOGIN_URL', None)
            }
        )
        
        if result.get('status') != 'success':
            error_msg = result.get('message', 'Unknown error setting credentials')
            logger.error(f"Failed to set credentials: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info("✅ Credentials set successfully")
        return {
            "status": "success", 
            "message": "Credentials stored successfully",
            "username": credentials.username
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except MCPConnectionError as e:
        logger.error(f"MCP connection error setting credentials: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"MCP server unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error setting credentials: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal error: {str(e)}"
        )


@app.post("/login")
async def login():
    """Perform login with stored credentials"""
    try:
        # Ensure MCP client is available
        client = await ensure_mcp_client()
        
        logger.info("Attempting login with stored credentials")
        result = await client.perform_login()
        
        if result.get("status") == "success":
            logger.info("✅ Login successful")
            return {
                "status": "success", 
                "message": "Login successful"
            }
        else:
            error_msg = result.get("message", "Login failed")
            logger.warning(f"Login failed: {error_msg}")
            return {
                "status": "error", 
                "message": error_msg
            }
            
    except MCPConnectionError as e:
        logger.error(f"MCP connection error during login: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"MCP server unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal error: {str(e)}"
        )


# Add debugging endpoints
@app.get("/debug/connection")
async def debug_connection():
    """Debug endpoint to check MCP connection details"""
    global mcp_client, connection_status
    
    debug_info = {
        "connection_status": connection_status,
        "client_exists": mcp_client is not None,
        "session_exists": mcp_client.session is not None if mcp_client else False
    }
    
    if mcp_client:
        try:
            debug_info["health_check"] = await mcp_client.health_check()
            tools = await mcp_client.list_tools()
            debug_info["tools"] = [tool.name for tool in tools]
        except Exception as e:
            debug_info["error"] = str(e)
    
    return debug_info


if __name__ == "__main__":
    # Validate configuration
    try:
        config.validate()
        logger.info("✅ Configuration validated")
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        exit(1)
    
    # Start server
    logger.info(f"🚀 Starting chatbot server on {config.CHATBOT_HOST}:{config.CHATBOT_PORT}")
    uvicorn.run(
        "chatbot_app:app",
        host=config.CHATBOT_HOST,
        port=config.CHATBOT_PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=False  # Disable reload to avoid issues with MCP connections
    )
