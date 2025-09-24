#!/usr/bin/env python3
"""
Simplified Web UI for FastMCP Server
====================================
A clean, simple web interface that connects to the simplified FastMCP server
using the from_openapi approach.
"""

import os
import json
import asyncio
import logging
import threading
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from simplified_fastmcp_server import get_server, SimplifiedFastMCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('simplified_web_ui.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simplified-fastmcp-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Async event loop management
class AsyncEventLoop:
    def __init__(self):
        self.loop = None
        self.thread = None
        self._start_loop()
    
    def _start_loop(self):
        """Start the async event loop in a separate thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        
        # Wait for loop to be ready
        import time
        while self.loop is None:
            time.sleep(0.01)
    
    def run_async(self, coro):
        """Run an async coroutine in the event loop"""
        if self.loop is None:
            raise RuntimeError("Event loop not initialized")
        
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=30)

# Global async event loop
async_loop = AsyncEventLoop()

# Simple service class
class SimplifiedService:
    def __init__(self):
        self.server = None
        self.initialized = False
        self.conversation = []
    
    async def initialize(self):
        """Initialize the simplified FastMCP server"""
        if self.initialized:
            return True
            
        try:
            logger.info("🔄 Initializing simplified FastMCP server...")
            self.server = await get_server()
            self.initialized = True
            
            logger.info("✅ Simplified FastMCP server initialized successfully")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error initializing server: {e}")
            return False
    
    async def get_tools(self):
        """Get available tools"""
        if not self.initialized or not self.server:
            return []
        
        try:
            return await self.server.get_tools()
        except Exception as e:
            logger.error(f"❌ Error getting tools: {e}")
            return []
    
    async def execute_tool(self, tool_name: str, arguments: dict):
        """Execute a tool"""
        if not self.initialized or not self.server:
            return {"status": "error", "message": "Server not initialized"}
        
        try:
            return await self.server.execute_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"❌ Error executing tool {tool_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def set_credentials(self, **kwargs):
        """Set credentials"""
        if not self.initialized or not self.server:
            return {"status": "error", "message": "Server not initialized"}
        
        try:
            return await self.server.set_credentials(**kwargs)
        except Exception as e:
            logger.error(f"❌ Error setting credentials: {e}")
            return {"status": "error", "message": str(e)}

# Create service instance
service = SimplifiedService()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('simplified_chat.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    session_id = request.sid
    logger.info(f"🔌 Client connected: {session_id}")
    
    # Initialize server on first connection
    if not service.initialized:
        logger.info("🔄 Starting server initialization...")
        emit('system_message', {'message': '🔄 Initializing FastMCP server...'})
        
        try:
            result = async_loop.run_async(service.initialize())
            
            if result:
                emit('system_message', {'message': '✅ FastMCP server initialized - Ready to use API tools!'})
                
                # Load and send tools list
                tools = async_loop.run_async(service.get_tools())
                emit('tools_list', {'tools': tools})
            else:
                emit('error', {'message': '❌ Server initialization failed'})
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            emit('error', {'message': f'❌ Initialization error: {str(e)}'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = request.sid
    logger.info(f"🔌 Client disconnected: {session_id}")

@socketio.on('message')
def handle_message(data):
    """Handle incoming messages"""
    session_id = request.sid
    message = data.get('message', '').strip()
    
    if not message:
        return
    
    logger.info(f"💬 Received message from {session_id}: '{message}'")
    
    # Emit user message
    emit('user_message', {'message': message})
    
    # Simple response for now - in a real implementation, you'd integrate with an LLM
    # For demo purposes, we'll just echo back with available tools
    try:
        tools = async_loop.run_async(service.get_tools())
        
        response = f"I received your message: '{message}'\n\n"
        response += f"I have access to {len(tools)} API tools. "
        response += "You can ask me to execute specific tools or set up authentication credentials."
        
        emit('assistant_message', {'message': response})
        
    except Exception as e:
        logger.error(f"❌ Processing error: {e}")
        emit('error', {'message': f'❌ Processing error: {str(e)}'})

@socketio.on('set_credentials')
def handle_set_credentials(data):
    """Handle credential setting"""
    session_id = request.sid
    logger.info(f"🔐 Setting credentials for {session_id}")
    
    try:
        result = async_loop.run_async(service.set_credentials(**data))
        
        if result.get("status") == "success":
            emit('system_message', {'message': '✅ Credentials set successfully'})
        else:
            emit('error', {'message': f'❌ Failed to set credentials: {result.get("message", "Unknown error")}'})
        
    except Exception as e:
        logger.error(f"❌ Error setting credentials: {e}")
        emit('error', {'message': f'❌ Error setting credentials: {str(e)}'})

@socketio.on('execute_tool')
def handle_execute_tool(data):
    """Handle tool execution"""
    session_id = request.sid
    tool_name = data.get('tool_name', '')
    arguments = data.get('arguments', {})
    
    logger.info(f"🔧 Executing tool {tool_name} for {session_id}")
    
    try:
        result = async_loop.run_async(service.execute_tool(tool_name, arguments))
        
        if result.get("status") == "success":
            emit('tool_result', {
                'tool_name': tool_name,
                'status': 'success',
                'result': result.get("result", ""),
                'spec_name': result.get("spec_name", "")
            })
        else:
            emit('tool_result', {
                'tool_name': tool_name,
                'status': 'error',
                'error': result.get("message", "Unknown error")
            })
        
    except Exception as e:
        logger.error(f"❌ Error executing tool {tool_name}: {e}")
        emit('tool_result', {
            'tool_name': tool_name,
            'status': 'error',
            'error': str(e)
        })

@socketio.on('get_tools')
def handle_get_tools():
    """Get available tools"""
    session_id = request.sid
    logger.info(f"🔧 Getting tools for {session_id}")
    
    try:
        tools = async_loop.run_async(service.get_tools())
        emit('tools_list', {'tools': tools})
        logger.info(f"✅ Sent {len(tools)} tools to {session_id}")
    except Exception as e:
        logger.error(f"❌ Error getting tools: {e}")
        emit('error', {'message': f'❌ Error getting tools: {str(e)}'})

@socketio.on('clear_conversation')
def handle_clear_conversation():
    """Clear conversation history"""
    session_id = request.sid
    logger.info(f"🗑️ Clearing conversation for {session_id}")
    
    service.conversation = []
    emit('system_message', {'message': '✅ Conversation cleared'})

if __name__ == '__main__':
    print("🤖 Starting Simplified FastMCP Web UI...")
    print("🌐 Open http://localhost:5001 in your browser")
    print("💬 Chat with your simplified API assistant")
    print()
    
    try:
        socketio.run(app, host='0.0.0.0', port=5001, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Error starting web UI: {e}")
    finally:
        # Cleanup async loop
        if async_loop.loop:
            async_loop.loop.call_soon_threadsafe(async_loop.loop.stop)