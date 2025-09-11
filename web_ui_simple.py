#!/usr/bin/env python3
"""
Simple Web UI for MCP API - Single Threaded Version
No complex threading, no asyncio event loops - just simple Flask-SocketIO
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
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global MCP service instance
mcp_service = None
service_initialized = False

# Store conversation history per session
conversations = {}

def initialize_mcp_service():
    """Initialize MCP service - synchronous version"""
    global mcp_service, service_initialized
    
    logger.info("[UI] Starting MCP service initialization...")
    
    try:
        mcp_service = ModernLLMService()
        logger.info("[UI] MCP service instance created")
        
        # Initialize synchronously
        logger.info("[UI] Calling mcp_service.initialize()...")
        result = mcp_service.initialize()
        
        # Update global variable
        service_initialized = result
        
        if result:
            logger.info("[UI] MCP Service initialized successfully")
            print("MCP Service initialized successfully")
            logger.info(f"[UI] service_initialized set to: {service_initialized}")
            return True
        else:
            logger.error("[UI] MCP Service initialization failed")
            print("MCP Service initialization failed")
            logger.info(f"[UI] service_initialized set to: {service_initialized}")
            return False
        
    except Exception as e:
        logger.error(f"[UI] Error initializing MCP service: {e}")
        print(f"Error initializing MCP service: {e}")
        service_initialized = False
        logger.info(f"[UI] service_initialized set to: {service_initialized}")
        return False

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('chat_ws.html')

@socketio.on('connect')
def handle_connect(auth=None):
    """Handle client connection"""
    session_id = request.sid
    logger.info(f"[UI] Client connected: {session_id}")
    
    # Initialize conversation history
    conversations[session_id] = []
    
    # Initialize MCP service if not done yet
    if not service_initialized:
        logger.info(f"[UI] Initializing MCP service for client {session_id}")
        socketio.emit('system_message', {'message': 'Initializing MCP service...'}, room=session_id)
        
        result = initialize_mcp_service()
        if result:
            socketio.emit('system_message', {'message': 'MCP Service initialized - I can now understand and execute tools!'}, room=session_id)
        else:
            socketio.emit('error', {'message': 'MCP Service initialization failed'}, room=session_id)
    else:
        logger.info(f"[UI] MCP service already initialized for client {session_id}")
    
    # Check credentials status
    credentials_configured = bool(os.getenv('API_USERNAME') and os.getenv('API_PASSWORD'))
    logger.info(f"[UI] Credentials status for {session_id}: {'configured' if credentials_configured else 'not configured'}")
    
    emit('connected', {'message': 'Connected to server'})
    emit('credentials_status', {
        'configured': credentials_configured,
        'message': 'Credentials configured' if credentials_configured else 'Please configure credentials'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = request.sid
    logger.info(f"[UI] Client disconnected: {session_id}")
    
    # Clean up conversation history
    if session_id in conversations:
        del conversations[session_id]
        logger.info(f"[UI] Cleaned up conversation history for {session_id}")

@socketio.on('message')
def handle_message(data):
    """Handle incoming messages"""
    session_id = request.sid
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return
    
    logger.info(f"[UI] Processing message from {session_id}: {user_message}")
    
    # Add user message to conversation
    if session_id not in conversations:
        conversations[session_id] = []
    conversations[session_id].append({'role': 'user', 'content': user_message})
    
    # Emit user message
    emit('user_message', {'message': user_message})
    
    # Process with MCP service if available
    if service_initialized and mcp_service:
        try:
            logger.info(f"[UI] Processing message with MCP service for {session_id}")
            
            # Process message synchronously
            result = mcp_service.process_message(user_message)
            
            if result.get('success'):
                response = result.get('response', 'No response generated')
                logger.info(f"[UI] MCP service response for {session_id}: {response}")
                
                # Add bot response to conversation
                conversations[session_id].append({'role': 'assistant', 'content': response})
                
                # Emit bot response
                emit('bot_message', {'message': response})
                
                # Emit tool calls if any
                if 'tool_calls' in result:
                    for tool_call in result['tool_calls']:
                        emit('tool_call', {
                            'tool_name': tool_call.get('name', 'Unknown'),
                            'status': tool_call.get('status', 'Unknown'),
                            'args': tool_call.get('args', {}),
                            'result': tool_call.get('result', 'No result')
                        })
                
                # Emit capabilities if any
                if 'capabilities' in result:
                    emit('capabilities_demonstrated', {
                        'capabilities': result['capabilities']
                    })
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"[UI] MCP service error for {session_id}: {error_msg}")
                emit('error', {'message': f'Error: {error_msg}'})
                
        except Exception as e:
            logger.error(f"[UI] Error processing message for {session_id}: {e}")
            emit('error', {'message': f'Error processing message: {str(e)}'})
    else:
        logger.warning(f"[UI] MCP service not available for {session_id}")
        emit('error', {'message': 'MCP service not available. Please try again later.'})

@socketio.on('set_credentials')
def handle_set_credentials(data):
    """Handle credential configuration"""
    session_id = request.sid
    logger.info(f"[UI] Setting credentials for {session_id}")
    
    try:
        # Update environment variables
        logger.info(f"[UI] Updating environment variables for {session_id}")
        
        if data.get('username'):
            os.environ['API_USERNAME'] = data['username']
            logger.info(f"[UI] Set API_USERNAME for {session_id}")
        
        if data.get('password'):
            os.environ['API_PASSWORD'] = data['password']
            logger.info(f"[UI] Set API_PASSWORD for {session_id}")
        
        if data.get('api_key_name'):
            os.environ['API_KEY_NAME'] = data['api_key_name']
            logger.info(f"[UI] Set API_KEY_NAME for {session_id}")
        
        if data.get('api_key_value'):
            os.environ['API_KEY_VALUE'] = data['api_key_value']
            logger.info(f"[UI] Set API_KEY_VALUE for {session_id}")
        
        if data.get('login_url'):
            os.environ['LOGIN_URL'] = data['login_url']
            logger.info(f"[UI] Set LOGIN_URL for {session_id}")
        
        if data.get('base_url'):
            os.environ['BASE_URL'] = data['base_url']
            logger.info(f"[UI] Set BASE_URL for {session_id}")
        
        # Try to perform login if MCP service is available
        if service_initialized and mcp_service:
            logger.info(f"[UI] Attempting login for {session_id}")
            
            try:
                # Use the MCP service's process_message method to handle login
                logger.info(f"[UI] Using MCP service to handle login for {session_id}")
                
                # Create a login request message
                login_message = f"Please set credentials: username={data.get('username', '')}, password={data.get('password', '')}, api_key_name={data.get('api_key_name', '')}, api_key_value={data.get('api_key_value', '')}, login_url={data.get('login_url', '')}, base_url={data.get('base_url', '')}. Then perform login to get session ID."
                
                # Process the login request
                result = mcp_service.process_message(login_message)
                
                if result.get('success'):
                    response = result.get('response', '')
                    logger.info(f"[UI] Login response for {session_id}: {response}")
                    
                    # Check if login was successful by looking for session ID in response
                    if 'session' in response.lower() or 'success' in response.lower():
                        emit('credentials_status', {
                            'configured': True,
                            'message': f'Login successful! {response[:100]}...'
                        })
                    else:
                        emit('credentials_status', {
                            'configured': False,
                            'message': f'Login may have failed: {response[:100]}...'
                        })
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"[UI] Login failed for {session_id}: {error_msg}")
                    emit('credentials_status', {
                        'configured': False,
                        'message': f'Login failed: {error_msg}'
                    })
                    
            except Exception as e:
                logger.error(f"[UI] Error in login process for {session_id}: {e}")
                emit('credentials_status', {
                    'configured': False,
                    'message': f'Login failed: {str(e)}'
                })
        else:
            logger.warning(f"[UI] MCP service not available for {session_id}, credentials saved but login deferred")
            emit('credentials_status', {
                'configured': True,
                'message': 'Credentials saved! (MCP service will handle login when ready)'
            })
            
    except Exception as e:
        logger.error(f"[UI] Error setting credentials for {session_id}: {e}")
        emit('credentials_status', {
            'configured': False,
            'message': f'Error setting credentials: {str(e)}'
        })

@socketio.on('get_tools')
def handle_get_tools():
    """Handle tool list request"""
    session_id = request.sid
    logger.info(f"[UI] Getting tools for {session_id}")
    
    if service_initialized and mcp_service and hasattr(mcp_service, '_tools'):
        tools = mcp_service._tools
        logger.info(f"[UI] Found {len(tools)} tools for {session_id}")
        emit('tools_list', {'tools': tools})
    else:
        logger.warning(f"[UI] No tools available for {session_id}")
        emit('tools_list', {'tools': []})

if __name__ == '__main__':
    logger.info("[UI] Starting Simple Web UI...")
    logger.info("[UI] No complex threading - just simple Flask-SocketIO")
    
    # Initialize MCP service on startup
    logger.info("[UI] Initializing MCP service on startup...")
    initialize_mcp_service()
    
    logger.info("[UI] Starting Flask-SocketIO server...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)