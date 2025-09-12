#!/usr/bin/env python3
"""
MCP Bot Web Interface - FIXED
==============================
Personal API assistant with 51 tools
Clean, simple, and reliable
"""

import os
import json
import asyncio
import logging
import threading
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from mcp_service import ModernLLMService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('web_ui.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mcp-bot-secret-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# FIXED: Proper async event loop management
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
        return future.result(timeout=30)  # 30 second timeout

# Global async event loop
async_loop = AsyncEventLoop()

# Simple class to hold MCP service state
class MCPDemoService:
    def __init__(self):
        self.service = None
        self.initialized = False
        self.conversation = []
    
    async def initialize(self):
        """Initialize MCP service once"""
        if self.initialized:
            return True
            
        try:
            logger.info("🔄 [DEMO] Initializing MCP service...")
            self.service = ModernLLMService()
            result = await self.service.initialize()
            self.initialized = result
            
            if result:
                logger.info("✅ [DEMO] MCP Service initialized successfully")
                return True
            else:
                logger.error("❌ [DEMO] MCP Service initialization failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ [DEMO] Error initializing MCP service: {e}")
            return False
    
    async def process_message(self, message):
        """Process user message with MCP service"""
        if not self.initialized or not self.service:
            return {
                "response": "❌ MCP service not initialized. Please refresh the page.",
                "tool_calls": [],
                "capabilities": {"descriptions": []}
            }
        
        try:
            # Add user message to conversation
            self.conversation.append({"role": "user", "content": message})
            
            # Process with MCP service
            result = await self.service.process_message(message, self.conversation[-10:])  # Keep last 10 messages
            
            # Add assistant response to conversation
            if result.get("response"):
                self.conversation.append({"role": "assistant", "content": result.get("response", "")})
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [DEMO] Error processing message: {e}")
            return {
                "response": f"❌ Error processing message: {str(e)}",
                "tool_calls": [],
                "capabilities": {"descriptions": []}
            }
    
    async def get_tools(self):
        """Get available tools"""
        if not self.initialized or not self.service:
            return []
        
        try:
            return await self.service.get_available_tools()
        except Exception as e:
            logger.error(f"❌ [DEMO] Error getting tools: {e}")
            return []

# Create single instance
demo_service = MCPDemoService()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('chat_ws.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    session_id = request.sid
    logger.info(f"🔌 [DEMO] Client connected: {session_id}")
    
    # Initialize MCP service on first connection
    if not demo_service.initialized:
        logger.info("🔄 [DEMO] Starting MCP service initialization...")
        emit('system_message', {'message': '🔄 Initializing MCP service...'})
        
        try:
            # FIXED: Proper async handling
            result = async_loop.run_async(demo_service.initialize())
            
            if result:
                emit('system_message', {'message': '✅ MCP Service initialized - I can now understand and execute tools!'})
                
                # Load and send tools list
                tools = async_loop.run_async(demo_service.get_tools())
                emit('tools_list', {'tools': tools})
            else:
                emit('error', {'message': '❌ MCP Service initialization failed'})
        except Exception as e:
            logger.error(f"❌ [DEMO] Initialization error: {e}")
            emit('error', {'message': f'❌ Initialization error: {str(e)}'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = request.sid
    logger.info(f"🔌 [DEMO] Client disconnected: {session_id}")

@socketio.on('message')
def handle_message(data):
    """Handle incoming messages"""
    session_id = request.sid
    message = data.get('message', '').strip()
    
    if not message:
        return
    
    logger.info(f"💬 [DEMO] Received message from {session_id}: '{message}'")
    
    # Emit user message
    emit('user_message', {'message': message})
    
    # Process with MCP service
    try:
        # FIXED: Proper async handling
        result = async_loop.run_async(demo_service.process_message(message))
        
        # Extract components from result
        response = result.get("response", "")
        tool_calls = result.get("tool_calls", [])
        capabilities = result.get("capabilities", {})
        
        # Emit tool execution details
        if tool_calls:
            logger.info(f"🔧 [DEMO] Executed {len(tool_calls)} tools for {session_id}")
            for i, tool_call in enumerate(tool_calls, 1):
                tool_name = tool_call.get("tool_name", "unknown")
                success = tool_call.get("success", False)
                status = "✅ Success" if success else "❌ Failed"
                args = tool_call.get("args", {})
                error = tool_call.get("error", "")
                
                logger.info(f"🔧 [DEMO] Tool {i}/{len(tool_calls)}: {tool_name} - {status}")
                emit('tool_execution', {
                    'tool_name': tool_name,
                    'status': status,
                    'args': args,
                    'result': tool_call.get("result", ""),
                    'error': error
                })
        
        # Emit capabilities demonstrated
        if capabilities.get("descriptions"):
            logger.info(f"✨ [DEMO] Capabilities: {capabilities['descriptions']}")
            emit('capabilities', {'capabilities': capabilities['descriptions']})
        
        # Emit final response
        emit('assistant_message', {'message': response})
        
    except Exception as e:
        logger.error(f"❌ [DEMO] Processing error: {e}")
        emit('error', {'message': f'❌ Processing error: {str(e)}'})

@socketio.on('set_credentials')
def handle_set_credentials(data):
    """Handle credential setting"""
    session_id = request.sid
    logger.info(f"🔐 [DEMO] Setting credentials for {session_id}")
    
    try:
        # Set environment variables
        env_mapping = {
            'username': 'API_USERNAME',
            'password': 'API_PASSWORD',
            'api_key_name': 'API_KEY_NAME',
            'api_key_value': 'API_KEY_VALUE',
            'login_url': 'LOGIN_URL',
            'base_url': 'FORCE_BASE_URL'
        }
        
        for key, value in data.items():
            if value and key in env_mapping:
                os.environ[env_mapping[key]] = value
                logger.info(f"🔐 [DEMO] Set {env_mapping[key]}")
        
        emit('system_message', {'message': '✅ Credentials set successfully'})
        
    except Exception as e:
        logger.error(f"❌ [DEMO] Error setting credentials: {e}")
        emit('error', {'message': f'❌ Error setting credentials: {str(e)}'})

@socketio.on('clear_conversation')
def handle_clear_conversation():
    """Clear conversation history"""
    session_id = request.sid
    logger.info(f"🗑️ [DEMO] Clearing conversation for {session_id}")
    
    demo_service.conversation = []
    emit('system_message', {'message': '✅ Conversation cleared'})

@socketio.on('get_tools')
def handle_get_tools():
    """Get available tools"""
    session_id = request.sid
    logger.info(f"🔧 [DEMO] Getting tools for {session_id}")
    
    try:
        tools = async_loop.run_async(demo_service.get_tools())
        emit('tools_list', {'tools': tools})
        logger.info(f"✅ [DEMO] Sent {len(tools)} tools to {session_id}")
    except Exception as e:
        logger.error(f"❌ [DEMO] Error getting tools: {e}")
        emit('error', {'message': f'❌ Error getting tools: {str(e)}'})

if __name__ == '__main__':
    print("🤖 Starting MCP Bot...")
    print("🌐 Open http://localhost:5000 in your browser")
    print("💬 Chat with your personal API assistant")
    print()
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Shutting down MCP Bot...")
    except Exception as e:
        print(f"❌ Error starting MCP Bot: {e}")
    finally:
        # Cleanup async loop
        if async_loop.loop:
            async_loop.loop.call_soon_threadsafe(async_loop.loop.stop)
