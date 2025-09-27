"""
Web MCP Bridge - Browser-based MCP client for web applications
Provides MCP protocol support in web browsers via WebSocket bridge
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from mcp_client import IntelligentOrchestrationMCPClient

logger = logging.getLogger(__name__)


class WebMCPBridge:
    """
    WebSocket bridge that enables MCP protocol communication in web browsers
    Acts as a proxy between web clients and MCP servers
    """
    
    def __init__(self):
        self.mcp_client: Optional[IntelligentOrchestrationMCPClient] = None
        self.active_connections: Dict[str, WebSocket] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup message handlers for different MCP operations"""
        self.message_handlers = {
            "mcp_connect": self._handle_connect,
            "mcp_disconnect": self._handle_disconnect,
            "mcp_execute_query": self._handle_execute_query,
            "mcp_load_api": self._handle_load_api,
            "mcp_query_state": self._handle_query_state,
            "mcp_list_tools": self._handle_list_tools,
            "mcp_get_stats": self._handle_get_stats,
            "mcp_health_check": self._handle_health_check,
            "mcp_read_resource": self._handle_read_resource
        }
    
    async def connect_websocket(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # Initialize MCP client if not already done
        if not self.mcp_client:
            self.mcp_client = IntelligentOrchestrationMCPClient()
            await self.mcp_client.connect()
        
        await self._send_message(websocket, {
            "type": "mcp_connected",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to MCP bridge"
        })
        
        logger.info(f"WebSocket client connected: {client_id}")
    
    async def disconnect_websocket(self, client_id: str):
        """Disconnect a WebSocket client"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def handle_message(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        try:
            message_type = message.get("type")
            
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](websocket, client_id, message)
            else:
                await self._send_error(websocket, f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await self._send_error(websocket, str(e))
    
    async def _send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to WebSocket client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def _send_error(self, websocket: WebSocket, error: str):
        """Send error message to WebSocket client"""
        await self._send_message(websocket, {
            "type": "mcp_error",
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_connect(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle MCP connection request"""
        if not self.mcp_client:
            self.mcp_client = IntelligentOrchestrationMCPClient()
        
        success = await self.mcp_client.connect()
        
        await self._send_message(websocket, {
            "type": "mcp_connection_result",
            "success": success,
            "connected": self.mcp_client.connected,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_disconnect(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle MCP disconnection request"""
        if self.mcp_client:
            await self.mcp_client.disconnect()
        
        await self._send_message(websocket, {
            "type": "mcp_disconnected",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_execute_query(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle query execution request"""
        if not self.mcp_client or not self.mcp_client.connected:
            await self._send_error(websocket, "MCP client not connected")
            return
        
        query = message.get("query", "")
        max_iterations = message.get("max_iterations", 20)
        
        if not query:
            await self._send_error(websocket, "Query is required")
            return
        
        # Send start notification
        await self._send_message(websocket, {
            "type": "mcp_execution_started",
            "query": query,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        try:
            # Execute query
            result = await self.mcp_client.execute_query(query, max_iterations)
            
            await self._send_message(websocket, {
                "type": "mcp_execution_completed",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            await self._send_message(websocket, {
                "type": "mcp_execution_failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_load_api(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle API loading request"""
        if not self.mcp_client or not self.mcp_client.connected:
            await self._send_error(websocket, "MCP client not connected")
            return
        
        api_spec = message.get("api_spec")
        api_name = message.get("api_name")
        
        if not api_spec:
            await self._send_error(websocket, "API specification is required")
            return
        
        try:
            result = await self.mcp_client.load_api_spec(api_spec, api_name)
            
            await self._send_message(websocket, {
                "type": "mcp_api_loaded",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            await self._send_message(websocket, {
                "type": "mcp_api_load_failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_query_state(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle semantic state query request"""
        if not self.mcp_client or not self.mcp_client.connected:
            await self._send_error(websocket, "MCP client not connected")
            return
        
        query = message.get("query", "")
        context_types = message.get("context_types")
        limit = message.get("limit", 5)
        
        if not query:
            await self._send_error(websocket, "Query is required")
            return
        
        try:
            result = await self.mcp_client.query_semantic_state(query, context_types, limit)
            
            await self._send_message(websocket, {
                "type": "mcp_state_query_result",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            await self._send_message(websocket, {
                "type": "mcp_state_query_failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_list_tools(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle list tools request"""
        if not self.mcp_client or not self.mcp_client.connected:
            await self._send_error(websocket, "MCP client not connected")
            return
        
        try:
            result = await self.mcp_client.list_available_tools()
            
            await self._send_message(websocket, {
                "type": "mcp_tools_list",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            await self._send_message(websocket, {
                "type": "mcp_tools_list_failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_get_stats(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle get stats request"""
        if not self.mcp_client or not self.mcp_client.connected:
            await self._send_error(websocket, "MCP client not connected")
            return
        
        try:
            result = await self.mcp_client.get_system_stats()
            
            await self._send_message(websocket, {
                "type": "mcp_stats_result",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            await self._send_message(websocket, {
                "type": "mcp_stats_failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_health_check(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle health check request"""
        try:
            result = await self.mcp_client.health_check()
            
            await self._send_message(websocket, {
                "type": "mcp_health_result",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            await self._send_message(websocket, {
                "type": "mcp_health_failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_read_resource(self, websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """Handle read resource request"""
        if not self.mcp_client or not self.mcp_client.connected:
            await self._send_error(websocket, "MCP client not connected")
            return
        
        uri = message.get("uri", "")
        
        if not uri:
            await self._send_error(websocket, "Resource URI is required")
            return
        
        try:
            result = await self.mcp_client.read_resource(uri)
            
            await self._send_message(websocket, {
                "type": "mcp_resource_result",
                "uri": uri,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            await self._send_message(websocket, {
                "type": "mcp_resource_failed",
                "uri": uri,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })


# WebSocket endpoint integration for FastAPI
class WebMCPEndpoint:
    """FastAPI WebSocket endpoint for MCP bridge"""
    
    def __init__(self):
        self.bridge = WebMCPBridge()
    
    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket endpoint handler"""
        client_id = str(uuid.uuid4())
        
        try:
            await self.bridge.connect_websocket(websocket, client_id)
            
            while True:
                try:
                    # Receive message from client
                    data = await websocket.receive_json()
                    
                    # Handle message
                    await self.bridge.handle_message(websocket, client_id, data)
                    
                except WebSocketDisconnect:
                    logger.info(f"WebSocket client disconnected: {client_id}")
                    break
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    await self.bridge._send_error(websocket, str(e))
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            # Clean up connection
            await self.bridge.disconnect_websocket(client_id)


# HTML interface for MCP testing
MCP_TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MCP Web Bridge Test Interface</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .input-group { margin: 10px 0; }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .input-group input, .input-group textarea { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 3px; }
        .input-group textarea { height: 100px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        button:hover { background: #0056b3; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .output { background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 3px; max-height: 400px; overflow-y: auto; }
        .status { padding: 5px 10px; border-radius: 3px; margin: 5px 0; }
        .status.connected { background: #d4edda; color: #155724; }
        .status.disconnected { background: #f8d7da; color: #721c24; }
        .message { margin: 5px 0; padding: 5px; border-left: 3px solid #007bff; }
        .message.error { border-left-color: #dc3545; background: #f8d7da; }
        .message.success { border-left-color: #28a745; background: #d4edda; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 MCP Web Bridge Test Interface</h1>
        <p>Test Model Context Protocol communication through web browser</p>
        
        <div class="section">
            <h3>Connection Status</h3>
            <div id="connection-status" class="status disconnected">Disconnected</div>
            <button id="connect-btn" onclick="connectMCP()">Connect to MCP</button>
            <button id="disconnect-btn" onclick="disconnectMCP()" disabled>Disconnect</button>
            <button id="health-btn" onclick="healthCheck()" disabled>Health Check</button>
        </div>
        
        <div class="section">
            <h3>Query Execution</h3>
            <div class="input-group">
                <label for="query-input">Natural Language Query:</label>
                <textarea id="query-input" placeholder="Enter your query here... (e.g., 'What is my account balance?')"></textarea>
            </div>
            <div class="input-group">
                <label for="max-iterations">Max Iterations:</label>
                <input type="number" id="max-iterations" value="20" min="1" max="50">
            </div>
            <button id="execute-btn" onclick="executeQuery()" disabled>Execute Query</button>
        </div>
        
        <div class="section">
            <h3>API Management</h3>
            <div class="input-group">
                <label for="api-name">API Name:</label>
                <input type="text" id="api-name" placeholder="Enter API name">
            </div>
            <div class="input-group">
                <label for="api-spec">OpenAPI Specification (JSON):</label>
                <textarea id="api-spec" placeholder='{"openapi": "3.0.0", "info": {...}}'></textarea>
            </div>
            <button id="load-api-btn" onclick="loadAPI()" disabled>Load API</button>
            <button id="list-tools-btn" onclick="listTools()" disabled>List Tools</button>
        </div>
        
        <div class="section">
            <h3>Semantic State</h3>
            <div class="input-group">
                <label for="state-query">Semantic Query:</label>
                <input type="text" id="state-query" placeholder="Query semantic memory...">
            </div>
            <button id="query-state-btn" onclick="queryState()" disabled>Query State</button>
            <button id="get-stats-btn" onclick="getStats()" disabled>Get Stats</button>
        </div>
        
        <div class="section">
            <h3>Output</h3>
            <div id="output" class="output"></div>
            <button onclick="clearOutput()">Clear Output</button>
        </div>
    </div>

    <script>
        let ws = null;
        let clientId = null;
        let mcpConnected = false;

        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8000/mcp-ws');
            
            ws.onopen = function(event) {
                clientId = Math.random().toString(36).substr(2, 9);
                updateConnectionStatus('Connected', true);
                addMessage('WebSocket connected', 'success');
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleMCPMessage(data);
            };
            
            ws.onclose = function(event) {
                updateConnectionStatus('Disconnected', false);
                addMessage('WebSocket disconnected', 'error');
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                addMessage('WebSocket error: ' + error, 'error');
            };
        }

        function handleMCPMessage(data) {
            switch(data.type) {
                case 'mcp_connected':
                    addMessage('MCP connected: ' + data.message, 'success');
                    break;
                case 'mcp_connection_result':
                    mcpConnected = data.connected;
                    updateMCPButtons();
                    addMessage('MCP connection: ' + (data.success ? 'Success' : 'Failed'), data.success ? 'success' : 'error');
                    break;
                case 'mcp_execution_started':
                    addMessage('Execution started: ' + data.query, 'success');
                    break;
                case 'mcp_execution_completed':
                    addMessage('Execution completed', 'success');
                    addMessage('Result: ' + JSON.stringify(data.result, null, 2), 'success');
                    break;
                case 'mcp_execution_failed':
                    addMessage('Execution failed: ' + data.error, 'error');
                    break;
                case 'mcp_api_loaded':
                    addMessage('API loaded: ' + JSON.stringify(data.result, null, 2), 'success');
                    break;
                case 'mcp_tools_list':
                    addMessage('Available tools: ' + JSON.stringify(data.result, null, 2), 'success');
                    break;
                case 'mcp_stats_result':
                    addMessage('System stats: ' + JSON.stringify(data.result, null, 2), 'success');
                    break;
                case 'mcp_error':
                    addMessage('MCP Error: ' + data.error, 'error');
                    break;
                default:
                    addMessage('Unknown message: ' + JSON.stringify(data, null, 2), 'success');
            }
        }

        function updateConnectionStatus(status, connected) {
            const statusEl = document.getElementById('connection-status');
            statusEl.textContent = status;
            statusEl.className = 'status ' + (connected ? 'connected' : 'disconnected');
            
            document.getElementById('connect-btn').disabled = connected;
            document.getElementById('disconnect-btn').disabled = !connected;
        }

        function updateMCPButtons() {
            const buttons = ['execute-btn', 'load-api-btn', 'list-tools-btn', 'query-state-btn', 'get-stats-btn', 'health-btn'];
            buttons.forEach(id => {
                document.getElementById(id).disabled = !mcpConnected;
            });
        }

        function connectMCP() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'mcp_connect'}));
            }
        }

        function disconnectMCP() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'mcp_disconnect'}));
            }
        }

        function executeQuery() {
            const query = document.getElementById('query-input').value.trim();
            const maxIterations = parseInt(document.getElementById('max-iterations').value);
            
            if (!query) {
                alert('Please enter a query');
                return;
            }
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'mcp_execute_query',
                    query: query,
                    max_iterations: maxIterations
                }));
            }
        }

        function loadAPI() {
            const apiName = document.getElementById('api-name').value.trim();
            const apiSpec = document.getElementById('api-spec').value.trim();
            
            if (!apiSpec) {
                alert('Please enter API specification');
                return;
            }
            
            try {
                const spec = JSON.parse(apiSpec);
                
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'mcp_load_api',
                        api_spec: spec,
                        api_name: apiName || undefined
                    }));
                }
            } catch (e) {
                alert('Invalid JSON: ' + e.message);
            }
        }

        function listTools() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'mcp_list_tools'}));
            }
        }

        function queryState() {
            const query = document.getElementById('state-query').value.trim();
            
            if (!query) {
                alert('Please enter a semantic query');
                return;
            }
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'mcp_query_state',
                    query: query
                }));
            }
        }

        function getStats() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'mcp_get_stats'}));
            }
        }

        function healthCheck() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'mcp_health_check'}));
            }
        }

        function addMessage(message, type) {
            const output = document.getElementById('output');
            const messageEl = document.createElement('div');
            messageEl.className = 'message ' + (type || '');
            messageEl.innerHTML = '<strong>' + new Date().toLocaleTimeString() + ':</strong> ' + message;
            output.appendChild(messageEl);
            output.scrollTop = output.scrollHeight;
        }

        function clearOutput() {
            document.getElementById('output').innerHTML = '';
        }

        // Connect on page load
        connectWebSocket();
    </script>
</body>
</html>
"""


# Example usage
if __name__ == "__main__":
    # This would be integrated into the main FastAPI app
    print("Web MCP Bridge - Ready for integration with FastAPI")
    print("Use WebMCPEndpoint.websocket_endpoint as a FastAPI WebSocket route")