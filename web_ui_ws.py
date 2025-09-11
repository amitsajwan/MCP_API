"""
Modern LLM Tool Capabilities WebSocket UI
========================================
Real-time interface showcasing modern LLM tool usage
"""

import os
import json
import asyncio
import logging
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from mcp_service import mcp_service

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store conversation history per session
conversations = {}

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('chat_ws.html')

@socketio.on('connect')
def handle_connect(auth=None):
    """Handle client connection"""
    session_id = request.sid
    conversations[session_id] = []
    
    # Check if credentials are already configured
    has_credentials = bool(os.getenv('API_USERNAME') and os.getenv('API_PASSWORD')) or \
                     bool(os.getenv('API_KEY_NAME') and os.getenv('API_KEY_VALUE'))
    
    # Initialize MCP service if not already done
    # Note: MCP service initialization is handled separately
    pass
    
    # Send credentials status
    emit('credentials_status', {
        'configured': has_credentials,
        'message': 'Connected to Modern LLM Bot' + (' - Credentials configured' if has_credentials else ' - Click to configure credentials')
    })
    
    emit('connected', {'message': 'Connected to Modern LLM Bot'})
    print(f"Client {session_id} connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = request.sid
    if session_id in conversations:
        del conversations[session_id]
    print(f"Client {session_id} disconnected")

@socketio.on('message')
def handle_message(data):
    """Handle incoming chat message"""
    session_id = request.sid
    user_message = data.get('message', '').strip()
    
    if not user_message:
        emit('error', {'message': 'Empty message'})
        return
    
    # Add user message to conversation
    conversations[session_id].append({
        "role": "user", 
        "content": user_message
    })
    
    # Emit user message to client
    emit('user_message', {'message': user_message})
    
    # Simple echo response for now (MCP service integration pending)
    response = f"Echo: {user_message}"
    
    # Add bot response to conversation
    conversations[session_id].append({
        "role": "assistant",
        "content": response
    })
    
    # Emit bot response
    emit('bot_message', {'message': response})

async def initialize_mcp_service():
    """Initialize MCP service"""
    try:
        success = await mcp_service.initialize()
        if success:
            socketio.emit('system_message', {'message': 'Modern LLM Service initialized successfully'})
        else:
            socketio.emit('error', {'message': 'Failed to initialize Modern LLM Service'})
    except Exception as e:
        socketio.emit('error', {'message': f'Initialization error: {str(e)}'})

async def process_message_async(session_id: str, user_message: str):
    """Process message asynchronously"""
    try:
        # Get conversation history for this session
        conversation_history = conversations.get(session_id, [])
        
        # Process message through modern LLM service
        result = await mcp_service.process_message(user_message, conversation_history)
        
        if 'error' in result:
            socketio.emit('error', {'message': result['error']}, room=session_id)
            return
        
        # Update conversation history
        conversations[session_id] = result.get('conversation', [])
        
        # Emit tool calls if any
        if result.get('tool_calls'):
            for tool_call in result['tool_calls']:
                socketio.emit('tool_call', {
                    'tool_name': tool_call['tool_name'],
                    'args': tool_call['args'],
                    'result': tool_call.get('result'),
                    'error': tool_call.get('error')
                }, room=session_id)
        
        # Emit capabilities demonstrated
        if result.get('capabilities'):
            socketio.emit('capabilities_demonstrated', {
                'capabilities': result['capabilities']
            }, room=session_id)
        
        # Emit bot response
        socketio.emit('bot_message', {
            'message': result['response']
        }, room=session_id)
        
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        socketio.emit('error', {'message': f'Processing error: {str(e)}'}, room=session_id)

@socketio.on('get_tools')
def handle_get_tools():
    """Handle request for available tools"""
    # Return a simple list of available tools
    tools = [
        {
            "function": {
                "name": "cash_api_getPayments",
                "description": "Get all cash payments with optional filtering"
            }
        },
        {
            "function": {
                "name": "cash_api_createPayment", 
                "description": "Create a new cash payment request"
            }
        },
        {
            "function": {
                "name": "cls_api_getSettlements",
                "description": "Get CLS settlement information"
            }
        },
        {
            "function": {
                "name": "mailbox_api_getMessages",
                "description": "Get mailbox messages with filtering"
            }
        },
        {
            "function": {
                "name": "securities_api_getPositions",
                "description": "Get securities positions"
            }
        }
    ]
    
    emit('tools_list', {'tools': tools})

@socketio.on('set_credentials')
def handle_set_credentials(data):
    """Handle credential configuration"""
    try:
        # Update environment variables
        if data.get('username'):
            os.environ['API_USERNAME'] = data['username']
        if data.get('password'):
            os.environ['API_PASSWORD'] = data['password']
        if data.get('api_key_name'):
            os.environ['API_KEY_NAME'] = data['api_key_name']
        if data.get('api_key_value'):
            os.environ['API_KEY_VALUE'] = data['api_key_value']
        if data.get('login_url'):
            os.environ['LOGIN_URL'] = data['login_url']
        if data.get('base_url'):
            os.environ['FORCE_BASE_URL'] = data['base_url']
        
        emit('credentials_status', {
            'configured': True,
            'message': 'Credentials saved successfully! (Note: MCP service integration pending)'
        }, room=request.sid)
        
    except Exception as e:
        logging.error(f"Error setting credentials: {e}")
        emit('credentials_status', {
            'configured': False,
            'message': f'Error setting credentials: {str(e)}'
        }, room=request.sid)

async def set_credentials_async(credentials, session_id):
    """Set credentials asynchronously and perform login to get session ID"""
    try:
        # Update environment variables for this session
        if credentials.get('username'):
            os.environ['API_USERNAME'] = credentials['username']
        if credentials.get('password'):
            os.environ['API_PASSWORD'] = credentials['password']
        if credentials.get('api_key_name'):
            os.environ['API_KEY_NAME'] = credentials['api_key_name']
        if credentials.get('api_key_value'):
            os.environ['API_KEY_VALUE'] = credentials['api_key_value']
        if credentials.get('login_url'):
            os.environ['LOGIN_URL'] = credentials['login_url']
        if credentials.get('base_url'):
            os.environ['FORCE_BASE_URL'] = credentials['base_url']
        
        # Update MCP service with new credentials
        await mcp_service.cleanup()
        
        # Create new MCP server command with updated environment
        mcp_server_cmd = f"python mcp_server_fastmcp2.py --transport stdio"
        
        # Reinitialize MCP service with new server process
        success = await mcp_service.initialize_with_cmd(mcp_server_cmd)
        
        if success:
            # Now perform login to get session ID
            try:
                # Call the set_credentials tool to set credentials in MCP server
                await mcp_service._mcp_client.call_tool("set_credentials", {
                    "username": credentials.get('username', ''),
                    "password": credentials.get('password', ''),
                    "api_key_name": credentials.get('api_key_name', ''),
                    "api_key_value": credentials.get('api_key_value', ''),
                    "login_url": credentials.get('login_url', ''),
                    "base_url": credentials.get('base_url', '')
                })
                
                # Perform login to get session ID
                login_result = await mcp_service._mcp_client.call_tool("perform_login", {"force_login": True})
                login_data = json.loads(login_result)
                
                if login_data.get('status') == 'success':
                    socketio.emit('credentials_status', {
                        'configured': True,
                        'message': f'Credentials saved and login successful! Session ID: {login_data.get("session_id", "N/A")}'
                    }, room=session_id)
                else:
                    socketio.emit('credentials_status', {
                        'configured': False,
                        'message': f'Login failed: {login_data.get("message", "Unknown error")}'
                    }, room=session_id)
                    
            except Exception as login_error:
                logging.error(f"Login error: {login_error}")
                socketio.emit('credentials_status', {
                    'configured': False,
                    'message': f'Credentials saved but login failed: {str(login_error)}'
                }, room=session_id)
        else:
            socketio.emit('credentials_status', {
                'configured': False,
                'message': 'Failed to initialize service with new credentials'
            }, room=session_id)
            
    except Exception as e:
        logging.error(f"Error setting credentials: {e}")
        socketio.emit('credentials_status', {
            'configured': False,
            'message': f'Error setting credentials: {str(e)}'
        }, room=session_id)

async def get_tools_async():
    """Get available tools asynchronously"""
    try:
        tools = await mcp_service.get_available_tools()
        socketio.emit('tools_list', {'tools': tools})
    except Exception as e:
        socketio.emit('error', {'message': f'Error getting tools: {str(e)}'})

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 Starting Modern LLM Tool Capabilities Demo...")
    print("📱 Open your browser to: http://localhost:5000")
    print("🔧 Make sure your Azure OpenAI credentials are configured")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)