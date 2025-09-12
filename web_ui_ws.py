#!/usr/bin/env python3
"""
Simple Demo Web UI for MCP API
==============================
Simplified version without threading/global variable issues
Perfect for demo purposes - single user, reliable initialization
"""

import os
import json
import asyncio
import logging
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
app.config['SECRET_KEY'] = 'demo-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Simple class to hold MCP service state (no global variables)
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
            return "❌ MCP service not initialized. Please refresh the page."
        
        try:
            # Add user message to conversation
            self.conversation.append({"role": "user", "content": message})
            
            # Process with MCP service
            response = await self.service.process_message(message, self.conversation)
            
            # Add assistant response to conversation
            self.conversation.append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            logger.error(f"❌ [DEMO] Error processing message: {e}")
            return f"❌ Error processing message: {str(e)}"

# Create single instance (no global variables)
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
        
        # Run async initialization in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(demo_service.initialize())
            if result:
                emit('system_message', {'message': '✅ MCP Service initialized - I can now understand and execute tools!'})
            else:
                emit('error', {'message': '❌ MCP Service initialization failed'})
        except Exception as e:
            logger.error(f"❌ [DEMO] Initialization error: {e}")
            emit('error', {'message': f'❌ Initialization error: {str(e)}'})
        finally:
            loop.close()

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
        # Run async processing in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(demo_service.process_message(message))
            emit('assistant_message', {'message': response})
        except Exception as e:
            logger.error(f"❌ [DEMO] Processing error: {e}")
            emit('error', {'message': f'❌ Processing error: {str(e)}'})
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"❌ [DEMO] Error handling message: {e}")
        emit('error', {'message': f'❌ Error: {str(e)}'})

@socketio.on('set_credentials')
def handle_set_credentials(data):
    """Handle credential setting"""
    session_id = request.sid
    logger.info(f"🔐 [DEMO] Setting credentials for {session_id}")
    
    try:
        # Set environment variables
        for key, value in data.items():
            if value:
                os.environ[key] = value
                logger.info(f"🔐 [DEMO] Set {key}")
        
        emit('credentials_set', {'message': '✅ Credentials set successfully'})
        
    except Exception as e:
        logger.error(f"❌ [DEMO] Error setting credentials: {e}")
        emit('error', {'message': f'❌ Error setting credentials: {str(e)}'})

@socketio.on('clear_conversation')
def handle_clear_conversation():
    """Clear conversation history"""
    session_id = request.sid
    logger.info(f"🗑️ [DEMO] Clearing conversation for {session_id}")
    
    demo_service.conversation = []
    emit('conversation_cleared', {'message': '✅ Conversation cleared'})

if __name__ == '__main__':
    print("🚀 Starting Simple Demo Web UI...")
    print("📱 Open http://localhost:5000 in your browser")
    print("💡 This is a simplified demo version - single user, reliable initialization")
    print()
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Shutting down demo web UI...")
    except Exception as e:
        print(f"❌ Error starting web UI: {e}")