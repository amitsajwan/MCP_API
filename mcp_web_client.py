#!/usr/bin/env python3
"""
MCP Web Client
A web-based interface for using MCP tools registered with app.tool().
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mcp_tool_client import MCPToolClient, ToolCall, ToolResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_web_client")

# Create FastAPI app
app = FastAPI(title="MCP Tool Client", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global client instance
mcp_client: Optional[MCPToolClient] = None

# Pydantic models
class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}

class ToolCallResponse(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    response_size: int = 0

class ServerConfigRequest(BaseModel):
    server_script: str
    server_args: List[str] = ["--transport", "stdio"]

class ServerInfo(BaseModel):
    connected: bool
    server_script: str
    server_args: List[str]
    tool_count: int
    tools: List[Dict[str, Any]]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize the MCP client on startup."""
    global mcp_client
    try:
        mcp_client = MCPToolClient("fastmcp_chatbot_server.py")
        await mcp_client.connect()
        logger.info("MCP client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    global mcp_client
    if mcp_client:
        await mcp_client.disconnect()

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main web interface."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MCP Tool Client</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: #2563eb;
                color: white;
                padding: 20px;
                text-align: center;
            }
            .content {
                padding: 20px;
            }
            .section {
                margin-bottom: 30px;
                padding: 20px;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
            }
            .section h3 {
                margin-top: 0;
                color: #374151;
            }
            .tool-list {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }
            .tool-card {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 15px;
                background: #f9fafb;
            }
            .tool-name {
                font-weight: bold;
                color: #1f2937;
                margin-bottom: 8px;
            }
            .tool-description {
                color: #6b7280;
                font-size: 14px;
                margin-bottom: 10px;
            }
            .tool-params {
                font-size: 12px;
                color: #9ca3af;
            }
            .call-section {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
            }
            .call-section input, .call-section select {
                flex: 1;
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
            }
            .btn {
                background: #2563eb;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            .btn:hover {
                background: #1d4ed8;
            }
            .btn:disabled {
                background: #9ca3af;
                cursor: not-allowed;
            }
            .result {
                background: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 15px;
                margin-top: 15px;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 12px;
                white-space: pre-wrap;
                max-height: 400px;
                overflow-y: auto;
            }
            .status {
                padding: 10px;
                border-radius: 4px;
                margin-bottom: 15px;
            }
            .status.connected {
                background: #d1fae5;
                color: #065f46;
                border: 1px solid #a7f3d0;
            }
            .status.disconnected {
                background: #fee2e2;
                color: #991b1b;
                border: 1px solid #fca5a5;
            }
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
                color: #6b7280;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔧 MCP Tool Client</h1>
                <p>Interactive interface for MCP tools registered with app.tool()</p>
            </div>
            
            <div class="content">
                <div id="status" class="status disconnected">
                    ❌ Not connected to MCP server
                </div>
                
                <div class="section">
                    <h3>📋 Available Tools</h3>
                    <div id="loading" class="loading">Loading tools...</div>
                    <div id="tool-list" class="tool-list"></div>
                </div>
                
                <div class="section">
                    <h3>🚀 Call Tool</h3>
                    <div class="call-section">
                        <select id="tool-select">
                            <option value="">Select a tool...</option>
                        </select>
                        <input type="text" id="tool-args" placeholder='Arguments (JSON): {"key": "value"}' />
                        <button id="call-btn" class="btn" onclick="callTool()">Call Tool</button>
                    </div>
                    <div id="result" class="result" style="display: none;"></div>
                </div>
            </div>
        </div>

        <script>
            let tools = [];
            let ws = null;
            
            // Initialize WebSocket connection
            function initWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
                
                ws.onopen = function() {
                    console.log('WebSocket connected');
                    loadTools();
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === 'tools_loaded') {
                        tools = data.tools;
                        updateToolList();
                        updateStatus(true);
                    } else if (data.type === 'tool_result') {
                        showResult(data.result);
                    }
                };
                
                ws.onclose = function() {
                    console.log('WebSocket disconnected');
                    updateStatus(false);
                };
            }
            
            // Load tools from server
            async function loadTools() {
                try {
                    const response = await fetch('/api/tools');
                    const data = await response.json();
                    tools = data.tools;
                    updateToolList();
                    updateStatus(data.connected);
                } catch (error) {
                    console.error('Error loading tools:', error);
                    updateStatus(false);
                }
            }
            
            // Update tool list display
            function updateToolList() {
                const toolList = document.getElementById('tool-list');
                const toolSelect = document.getElementById('tool-select');
                
                toolList.innerHTML = '';
                toolSelect.innerHTML = '<option value="">Select a tool...</option>';
                
                tools.forEach(tool => {
                    // Add to grid
                    const toolCard = document.createElement('div');
                    toolCard.className = 'tool-card';
                    toolCard.innerHTML = `
                        <div class="tool-name">${tool.name}</div>
                        <div class="tool-description">${tool.description}</div>
                        <div class="tool-params">
                            Required: ${tool.required_params.join(', ') || 'None'}<br>
                            Optional: ${tool.optional_params.join(', ') || 'None'}
                        </div>
                    `;
                    toolList.appendChild(toolCard);
                    
                    // Add to select
                    const option = document.createElement('option');
                    option.value = tool.name;
                    option.textContent = tool.name;
                    toolSelect.appendChild(option);
                });
                
                document.getElementById('loading').style.display = 'none';
            }
            
            // Update connection status
            function updateStatus(connected) {
                const status = document.getElementById('status');
                if (connected) {
                    status.className = 'status connected';
                    status.innerHTML = `✅ Connected to MCP server (${tools.length} tools available)`;
                } else {
                    status.className = 'status disconnected';
                    status.innerHTML = '❌ Not connected to MCP server';
                }
            }
            
            // Call selected tool
            async function callTool() {
                const toolName = document.getElementById('tool-select').value;
                const argsText = document.getElementById('tool-args').value;
                
                if (!toolName) {
                    alert('Please select a tool');
                    return;
                }
                
                let args = {};
                if (argsText.trim()) {
                    try {
                        args = JSON.parse(argsText);
                    } catch (e) {
                        alert('Invalid JSON in arguments field');
                        return;
                    }
                }
                
                const callBtn = document.getElementById('call-btn');
                callBtn.disabled = true;
                callBtn.textContent = 'Calling...';
                
                try {
                    const response = await fetch('/api/call-tool', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            tool_name: toolName,
                            arguments: args
                        })
                    });
                    
                    const result = await response.json();
                    showResult(result);
                } catch (error) {
                    showResult({
                        success: false,
                        error: error.message
                    });
                } finally {
                    callBtn.disabled = false;
                    callBtn.textContent = 'Call Tool';
                }
            }
            
            // Show tool result
            function showResult(result) {
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                
                if (result.success) {
                    resultDiv.innerHTML = `<strong>✅ Success (${result.execution_time.toFixed(2)}s)</strong>\n${JSON.stringify(result.result, null, 2)}`;
                } else {
                    resultDiv.innerHTML = `<strong>❌ Error</strong>\n${result.error}`;
                }
            }
            
            // Initialize on page load
            document.addEventListener('DOMContentLoaded', function() {
                initWebSocket();
            });
        </script>
    </body>
    </html>
    """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle WebSocket messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/status")
async def get_status():
    """Get server status."""
    global mcp_client
    return {
        "connected": mcp_client is not None and mcp_client.connected,
        "server_script": mcp_client.server_script if mcp_client else None,
        "server_args": mcp_client.server_args if mcp_client else None
    }

@app.get("/api/tools")
async def get_tools():
    """Get list of available tools."""
    global mcp_client
    if not mcp_client or not mcp_client.connected:
        raise HTTPException(status_code=503, detail="MCP client not connected")
    
    tools = await mcp_client.list_tools()
    return {
        "connected": True,
        "server_script": mcp_client.server_script,
        "server_args": mcp_client.server_args,
        "tool_count": len(tools),
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "required_params": tool.required_params,
                "optional_params": tool.optional_params,
                "parameters": tool.parameters
            }
            for tool in tools
        ]
    }

@app.post("/api/call-tool", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """Call a tool on the MCP server."""
    global mcp_client
    if not mcp_client or not mcp_client.connected:
        raise HTTPException(status_code=503, detail="MCP client not connected")
    
    try:
        result = await mcp_client.call_tool(request.tool_name, request.arguments)
        return ToolCallResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time=result.execution_time,
            response_size=result.response_size
        )
    except Exception as e:
        logger.error(f"Error calling tool {request.tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reconnect")
async def reconnect_server(request: ServerConfigRequest):
    """Reconnect to a different MCP server."""
    global mcp_client
    
    try:
        # Disconnect current client
        if mcp_client:
            await mcp_client.disconnect()
        
        # Create new client
        mcp_client = MCPToolClient(request.server_script, request.server_args)
        await mcp_client.connect()
        
        return {
            "success": True,
            "message": f"Connected to {request.server_script}",
            "tool_count": len(mcp_client.available_tools)
        }
    except Exception as e:
        logger.error(f"Error reconnecting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/server-info", response_model=ServerInfo)
async def get_server_info():
    """Get detailed server information."""
    global mcp_client
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    tools = await mcp_client.list_tools() if mcp_client.connected else []
    
    return ServerInfo(
        connected=mcp_client.connected,
        server_script=mcp_client.server_script,
        server_args=mcp_client.server_args,
        tool_count=len(tools),
        tools=[
            {
                "name": tool.name,
                "description": tool.description,
                "required_params": tool.required_params,
                "optional_params": tool.optional_params,
                "parameters": tool.parameters
            }
            for tool in tools
        ]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)