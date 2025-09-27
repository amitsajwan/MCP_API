"""
Intelligent API Orchestration System - Main Application
Real-time WebSocket interface with streaming execution updates
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from semantic_state_manager import SemanticStateManager
from tool_manager import ToolManager
from adaptive_orchestrator import AdaptiveOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Intelligent API Orchestration System",
    description="Semantic-first API orchestration with real-time streaming",
    version="1.0.0"
)

# Global components
semantic_state_manager: Optional[SemanticStateManager] = None
tool_manager: Optional[ToolManager] = None
orchestrator: Optional[AdaptiveOrchestrator] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, execution_id: str):
        await websocket.accept()
        self.active_connections[execution_id] = websocket
        logger.info(f"WebSocket connected: {execution_id}")
    
    def disconnect(self, execution_id: str):
        if execution_id in self.active_connections:
            del self.active_connections[execution_id]
            logger.info(f"WebSocket disconnected: {execution_id}")
    
    async def send_message(self, execution_id: str, message: Dict[str, Any]):
        if execution_id in self.active_connections:
            try:
                await self.active_connections[execution_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {execution_id}: {e}")
                self.disconnect(execution_id)

manager = ConnectionManager()


# Pydantic models
class QueryRequest(BaseModel):
    query: str
    execution_id: Optional[str] = None


class QueryResponse(BaseModel):
    execution_id: str
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    semantic_state: Dict[str, Any]
    tools: Dict[str, Any]
    orchestrator: str


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize system components on startup"""
    global semantic_state_manager, tool_manager, orchestrator
    
    try:
        logger.info("Initializing Intelligent API Orchestration System...")
        
        # Initialize semantic state manager
        semantic_state_manager = SemanticStateManager()
        logger.info("✓ Semantic state manager initialized")
        
        # Initialize tool manager
        tool_manager = ToolManager(semantic_state_manager)
        logger.info("✓ Tool manager initialized")
        
        # Initialize orchestrator
        orchestrator = AdaptiveOrchestrator(
            llm_provider="openai",  # Can be configured via environment
            semantic_state_manager=semantic_state_manager,
            tool_manager=tool_manager
        )
        logger.info("✓ Adaptive orchestrator initialized")
        
        logger.info("🚀 System ready for intelligent API orchestration!")
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global tool_manager
    
    try:
        if tool_manager:
            await tool_manager.close()
        logger.info("System shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# API Routes
@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "Intelligent API Orchestration System",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "Semantic state management",
            "Adaptive orchestration",
            "Real-time WebSocket streaming",
            "FastMCP tool integration"
        ]
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check"""
    try:
        semantic_stats = await semantic_state_manager.get_stats()
        tool_health = await tool_manager.health_check()
        
        return HealthResponse(
            status="healthy",
            semantic_state=semantic_stats,
            tools=tool_health,
            orchestrator="active"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """Execute a query synchronously (for testing)"""
    try:
        execution_id = request.execution_id or str(uuid.uuid4())
        
        # Execute query
        result = await orchestrator.execute_query(
            user_query=request.query,
            execution_id=execution_id
        )
        
        return QueryResponse(
            execution_id=execution_id,
            status="completed" if result.success else "failed",
            message=result.final_answer
        )
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/load")
async def load_api_spec(file_path: str, api_name: Optional[str] = None):
    """Load new API specification"""
    try:
        tools_loaded = await tool_manager.load_api_spec(file_path, api_name)
        
        return {
            "message": f"Loaded {tools_loaded} tools",
            "api_name": api_name or "unknown",
            "tools_loaded": tools_loaded
        }
        
    except Exception as e:
        logger.error(f"Failed to load API spec: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    """List available tools"""
    try:
        tool_names = tool_manager.get_tool_names()
        tool_context = tool_manager.get_tool_context()
        
        return {
            "total_tools": len(tool_names),
            "tool_names": tool_names,
            "context": tool_context
        }
        
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        semantic_stats = await semantic_state_manager.get_stats()
        tool_health = await tool_manager.health_check()
        
        return {
            "semantic_state": semantic_stats,
            "tools": tool_health,
            "active_connections": len(manager.active_connections),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket interface for streaming orchestration"""
    execution_id = str(uuid.uuid4())
    
    try:
        # Connect WebSocket
        await manager.connect(websocket, execution_id)
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "execution_id": execution_id,
            "message": "Connected to Intelligent API Orchestration System",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                
                if data.get("type") == "query":
                    query = data.get("query", "")
                    
                    if not query:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Empty query provided",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        continue
                    
                    # Send acknowledgment
                    await websocket.send_json({
                        "type": "query_received",
                        "execution_id": execution_id,
                        "query": query,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # Stream orchestration execution
                    async for update in orchestrator.execute_with_streaming(
                        user_query=query,
                        execution_id=execution_id
                    ):
                        # Forward update to WebSocket client
                        await websocket.send_json(update)
                        
                        # Check if client is still connected
                        try:
                            await websocket.send_json({"type": "ping"})
                        except:
                            logger.info(f"Client disconnected during execution: {execution_id}")
                            break
                
                elif data.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {data.get('type')}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {execution_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {execution_id}")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Clean up connection
        manager.disconnect(execution_id)


# Simple HTML interface for testing
@app.get("/ui", response_class=HTMLResponse)
async def get_ui():
    """Simple HTML interface for testing the system"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Intelligent API Orchestration System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .query-box { width: 100%; height: 100px; margin: 10px 0; }
            .output { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
            .status { color: #666; font-size: 0.9em; }
            .error { color: red; }
            .success { color: green; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #0056b3; }
            button:disabled { background: #ccc; cursor: not-allowed; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Intelligent API Orchestration System</h1>
            <p>Enter your query and watch the system intelligently orchestrate API calls in real-time!</p>
            
            <div>
                <textarea id="query" class="query-box" placeholder="Enter your query here... (e.g., 'What is my account balance?')"></textarea>
                <br>
                <button id="send" onclick="sendQuery()">Send Query</button>
                <button id="clear" onclick="clearOutput()">Clear Output</button>
            </div>
            
            <div id="status" class="status"></div>
            <div id="output" class="output"></div>
        </div>

        <script>
            let ws = null;
            let currentExecutionId = null;

            function connectWebSocket() {
                ws = new WebSocket('ws://localhost:8000/ws');
                
                ws.onopen = function(event) {
                    updateStatus('Connected to orchestration system', 'success');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                };
                
                ws.onclose = function(event) {
                    updateStatus('Disconnected from orchestration system', 'error');
                    setTimeout(connectWebSocket, 3000); // Reconnect after 3 seconds
                };
                
                ws.onerror = function(error) {
                    updateStatus('WebSocket error: ' + error, 'error');
                };
            }

            function handleMessage(data) {
                const output = document.getElementById('output');
                
                switch(data.type) {
                    case 'connected':
                        updateStatus('Connected: ' + data.message, 'success');
                        currentExecutionId = data.execution_id;
                        break;
                        
                    case 'query_received':
                        output.innerHTML += '<div><strong>📝 Query Received:</strong> ' + data.query + '</div>';
                        break;
                        
                    case 'status':
                        updateStatus(data.message, 'success');
                        break;
                        
                    case 'context_loaded':
                        output.innerHTML += '<div><strong>🧠 Context Loaded:</strong> ' + data.context_items + ' relevant items found</div>';
                        break;
                        
                    case 'step_planned':
                        output.innerHTML += '<div><strong>🎯 Step ' + data.iteration + ':</strong> ' + data.action;
                        if (data.tool_name) {
                            output.innerHTML += ' using ' + data.tool_name;
                        }
                        output.innerHTML += '<br><em>Reasoning:</em> ' + data.reasoning + '</div>';
                        break;
                        
                    case 'tool_executing':
                        output.innerHTML += '<div><strong>⚡ Executing:</strong> ' + data.tool_name + ' with params: ' + JSON.stringify(data.params) + '</div>';
                        break;
                        
                    case 'tool_completed':
                        if (data.success) {
                            output.innerHTML += '<div><strong>✅ Tool Completed:</strong> ' + data.tool_name + ' (took ' + data.execution_time.toFixed(3) + 's)</div>';
                        } else {
                            output.innerHTML += '<div><strong>❌ Tool Failed:</strong> ' + data.tool_name + ' - ' + data.result.error + '</div>';
                        }
                        break;
                        
                    case 'completed':
                        output.innerHTML += '<div><strong>🎉 Orchestration Complete!</strong><br><strong>Final Answer:</strong> ' + data.final_answer + '</div>';
                        updateStatus('Query completed successfully', 'success');
                        document.getElementById('send').disabled = false;
                        break;
                        
                    case 'error':
                        output.innerHTML += '<div><strong>❌ Error:</strong> ' + data.message + '</div>';
                        updateStatus('Error: ' + data.message, 'error');
                        document.getElementById('send').disabled = false;
                        break;
                        
                    case 'ping':
                        // Respond to ping
                        ws.send(JSON.stringify({type: 'pong'}));
                        break;
                        
                    default:
                        output.innerHTML += '<div><strong>📨 Update:</strong> ' + JSON.stringify(data) + '</div>';
                }
                
                output.scrollTop = output.scrollHeight;
            }

            function sendQuery() {
                const query = document.getElementById('query').value.trim();
                if (!query) {
                    alert('Please enter a query');
                    return;
                }
                
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    alert('Not connected to server');
                    return;
                }
                
                document.getElementById('send').disabled = true;
                document.getElementById('output').innerHTML = '';
                
                ws.send(JSON.stringify({
                    type: 'query',
                    query: query
                }));
            }

            function clearOutput() {
                document.getElementById('output').innerHTML = '';
                document.getElementById('status').innerHTML = '';
            }

            function updateStatus(message, type) {
                const status = document.getElementById('status');
                status.innerHTML = '<span class="' + type + '">' + message + '</span>';
            }

            // Connect on page load
            connectWebSocket();
        </script>
    </body>
    </html>
    """


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )