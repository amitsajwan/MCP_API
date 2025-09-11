#!/usr/bin/env python3
"""
Intelligent Web UI with LLM + MCP Integration (Windows Compatible)
================================================================
Web interface where LLM understands requirements and executes tools
"""

import os
import json
import logging
import threading
import asyncio
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from mcp_service import ModernLLMService

# Configure comprehensive logging (Windows compatible)
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
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global MCP service
mcp_service = None
service_initialized = False

# Store conversation history per session
conversations = {}

def initialize_mcp_service():
    """Initialize MCP service in a separate thread"""
    global mcp_service, service_initialized
    
    logger.info("[UI] Starting MCP service initialization...")
    
    try:
        mcp_service = ModernLLMService()
        logger.info("[UI] MCP service instance created")
        
        def run_async_init():
            logger.info("[UI] Starting async initialization thread...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                logger.info("[UI] Calling mcp_service.initialize()...")
                result = loop.run_until_complete(mcp_service.initialize())
                service_initialized = result
                if result:
                    logger.info("[UI] MCP Service initialized successfully")
                    print("MCP Service initialized successfully")
                    socketio.emit('system_message', {'message': 'MCP Service initialized - I can now understand and execute tools!'})
                else:
                    logger.error("[UI] MCP Service initialization failed")
                    print("MCP Service initialization failed")
                    socketio.emit('error', {'message': 'MCP Service initialization failed'})
            except Exception as e:
                logger.error(f"[UI] Error in async initialization: {e}")
                service_initialized = False
            finally:
                loop.close()
                logger.info("[UI] Async initialization thread completed")
        
        thread = threading.Thread(target=run_async_init)
        thread.daemon = True
        thread.start()
        thread.join(timeout=15)
        
        if service_initialized:
            logger.info("[UI] MCP service initialization completed successfully")
        else:
            logger.warning("[UI] MCP service initialization may have failed or timed out")
        
    except Exception as e:
        logger.error(f"[UI] Error initializing MCP service: {e}")
        print(f"Error initializing MCP service: {e}")
        service_initialized = False

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('chat_ws.html')

@socketio.on('connect')
def handle_connect(auth=None):
    """Handle client connection"""
    session_id = request.sid
    logger.info(f"[UI] Client connected: {session_id}")
    conversations[session_id] = []
    
    # Initialize MCP service if not done yet
    if not service_initialized and mcp_service is None:
        logger.info(f"[UI] Initializing MCP service for client {session_id}")
        socketio.emit('system_message', {'message': 'Initializing MCP service...'}, room=session_id)
        initialize_mcp_service()
    else:
        logger.info(f"[UI] MCP service already initialized for client {session_id}")
    
    # Check if credentials are already configured
    has_credentials = bool(os.getenv('API_USERNAME') and os.getenv('API_PASSWORD')) or \
                     bool(os.getenv('API_KEY_NAME') and os.getenv('API_KEY_VALUE'))
    
    logger.info(f"[UI] Credentials status for {session_id}: {'configured' if has_credentials else 'not configured'}")
    
    emit('credentials_status', {
        'configured': has_credentials,
        'message': 'Connected to Intelligent MCP System' + (' - Ready to execute tools!' if has_credentials else ' - Configure credentials to enable tool execution')
    })
    
    emit('connected', {'message': 'Connected to Intelligent MCP System'})
    print(f"Client {session_id} connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = request.sid
    logger.info(f"[UI] Client disconnected: {session_id}")
    if session_id in conversations:
        del conversations[session_id]
        logger.info(f"[UI] Cleaned up conversation history for {session_id}")
    print(f"Client {session_id} disconnected")

@socketio.on('message')
def handle_message(data):
    """Handle incoming chat message"""
    session_id = request.sid
    user_message = data.get('message', '').strip()
    
    logger.info(f"[UI] Received message from {session_id}: '{user_message}'")
    
    if not user_message:
        logger.warning(f"[UI] Empty message from {session_id}")
        emit('error', {'message': 'Empty message'})
        return
    
    # Add user message to conversation
    conversations[session_id].append({
        "role": "user", 
        "content": user_message
    })
    logger.info(f"[UI] Added user message to conversation history for {session_id}")
    
    # Emit user message to client
    emit('user_message', {'message': user_message})
    
    # Process with intelligent MCP service
    if service_initialized and mcp_service:
        logger.info(f"[UI] Processing message with MCP service for {session_id}")
        emit('system_message', {'message': 'Analyzing your request and executing tools...'}, room=session_id)
        
        def process_with_mcp():
            logger.info(f"[UI] Starting MCP processing thread for {session_id}")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    logger.info(f"[UI] Calling mcp_service.process_message() for {session_id}")
                    result = loop.run_until_complete(mcp_service.process_message(user_message))
                    logger.info(f"[UI] MCP processing completed for {session_id}")
                    
                    # Emit tool calls with details
                    if result.get('tool_calls'):
                        tool_count = len(result['tool_calls'])
                        logger.info(f"[UI] Executed {tool_count} tools for {session_id}")
                        emit('system_message', {'message': f'Executed {tool_count} tools:'}, room=session_id)
                        for i, tool_call in enumerate(result['tool_calls'], 1):
                            tool_name = tool_call['tool_name']
                            args = tool_call.get('args', {})
                            status = "Success" if not tool_call.get('error') else "Failed"
                            
                            logger.info(f"[UI] Tool {i}/{tool_count}: {tool_name} - {status}")
                            if tool_call.get('error'):
                                logger.error(f"[UI] Tool error: {tool_call.get('error')}")
                            
                            emit('tool_call', {
                                'tool_name': tool_name,
                                'args': args,
                                'result': tool_call.get('result'),
                                'error': tool_call.get('error'),
                                'status': status,
                                'step': i
                            }, room=session_id)
                    else:
                        logger.info(f"[UI] No tools executed for {session_id}")
                    
                    # Emit capabilities demonstrated
                    if result.get('capabilities'):
                        caps = result['capabilities']
                        descriptions = caps.get('descriptions', [])
                        if descriptions:
                            logger.info(f"[UI] Capabilities demonstrated for {session_id}: {descriptions}")
                            emit('capabilities_demonstrated', {
                                'capabilities': {
                                    'descriptions': descriptions,
                                    'success_rate': caps.get('success_rate', 0),
                                    'tool_count': caps.get('tool_count', 0)
                                }
                            }, room=session_id)
                    
                    # Emit intelligent response
                    response_message = result['response']
                    logger.info(f"[UI] Sending response to {session_id}: '{response_message[:100]}...'")
                    emit('bot_message', {
                        'message': response_message,
                        'intelligent': True
                    }, room=session_id)
                    
                    # Update conversation history
                    conversations[session_id] = result.get('conversation', [])
                    logger.info(f"[UI] Updated conversation history for {session_id}")
                    
                finally:
                    loop.close()
                    logger.info(f"[UI] MCP processing thread completed for {session_id}")
                    
            except Exception as e:
                logger.error(f"[UI] Error processing message with MCP for {session_id}: {e}")
                emit('error', {'message': f'Processing error: {str(e)}'}, room=session_id)
        
        # Run in a separate thread
        thread = threading.Thread(target=process_with_mcp)
        thread.daemon = True
        thread.start()
        logger.info(f"[UI] Started MCP processing thread for {session_id}")
        
    else:
        # Fallback response if MCP service not available
        logger.warning(f"[UI] MCP service not available for {session_id}, sending fallback response")
        response = "I'm still initializing my tool execution capabilities. Please wait a moment and try again."
        conversations[session_id].append({
            "role": "assistant",
            "content": response
        })
        emit('bot_message', {'message': response})

@socketio.on('get_tools')
def handle_get_tools():
    """Handle request for available tools"""
    if service_initialized and mcp_service and hasattr(mcp_service, '_tools'):
        try:
            tools = []
            for tool in mcp_service._tools:
                tools.append({
                    'function': {
                        'name': tool['function']['name'],
                        'description': tool['function']['description']
                    }
                })
            emit('tools_list', {'tools': tools})
        except Exception as e:
            logger.error(f"Error getting tools: {e}")
            emit('error', {'message': f'Error getting tools: {str(e)}'})
    else:
        # Show that tools are loading
        emit('tools_list', {'tools': [{'function': {'name': 'Loading...', 'description': 'Initializing MCP service'}}]})

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
            os.environ['FORCE_BASE_URL'] = data['base_url']
            logger.info(f"[UI] Set FORCE_BASE_URL for {session_id}")
        
        # Perform login to get session ID
        def perform_login_async():
            logger.info(f"[UI] Starting login process for {session_id}")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if service_initialized and mcp_service:
                        logger.info(f"[UI] Calling set_credentials tool for {session_id}")
                        # Call set_credentials tool in MCP server
                        loop.run_until_complete(mcp_service._mcp_client.call_tool("set_credentials", {
                            "username": data.get('username', ''),
                            "password": data.get('password', ''),
                            "api_key_name": data.get('api_key_name', ''),
                            "api_key_value": data.get('api_key_value', ''),
                            "login_url": data.get('login_url', ''),
                            "base_url": data.get('base_url', '')
                        }))
                        logger.info(f"[UI] set_credentials tool completed for {session_id}")
                        
                        logger.info(f"[UI] Calling perform_login tool for {session_id}")
                        # Perform login to get session ID
                        login_result = loop.run_until_complete(mcp_service._mcp_client.call_tool("perform_login", {"force_login": True}))
                        logger.info(f"[UI] perform_login tool completed for {session_id}")
                        
                        login_data = json.loads(login_result)
                        logger.info(f"[UI] Login result for {session_id}: {login_data}")
                        
                        if login_data.get('status') == 'success':
                            session_id_value = login_data.get('session_id', 'N/A')
                            logger.info(f"[UI] Login successful for {session_id}, session: {session_id_value[:20]}...")
                            socketio.emit('credentials_status', {
                                'configured': True,
                                'message': f'Login successful! Session ID: {session_id_value[:20]}...'
                            }, room=session_id)
                        else:
                            error_msg = login_data.get("message", "Unknown error")
                            logger.error(f"[UI] Login failed for {session_id}: {error_msg}")
                            socketio.emit('credentials_status', {
                                'configured': False,
                                'message': f'Login failed: {error_msg}'
                            }, room=session_id)
                    else:
                        logger.warning(f"[UI] MCP service not available for {session_id}, credentials saved but login deferred")
                        socketio.emit('credentials_status', {
                            'configured': True,
                            'message': 'Credentials saved! (MCP service will handle login when ready)'
                        }, room=session_id)
                        
                finally:
                    loop.close()
                    logger.info(f"[UI] Login process completed for {session_id}")
                    
            except Exception as e:
                logger.error(f"[UI] Login error for {session_id}: {e}")
                socketio.emit('credentials_status', {
                    'configured': False,
                    'message': f'Login failed: {str(e)}'
                }, room=session_id)
        
        # Run login in a separate thread
        thread = threading.Thread(target=perform_login_async)
        thread.daemon = True
        thread.start()
        logger.info(f"[UI] Started login thread for {session_id}")
        
    except Exception as e:
        logger.error(f"[UI] Error setting credentials for {session_id}: {e}")
        emit('credentials_status', {
            'configured': False,
            'message': f'Error setting credentials: {str(e)}'
        }, room=session_id)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    
    print("Starting Intelligent MCP Web UI...")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    try:
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting server: {e}")
