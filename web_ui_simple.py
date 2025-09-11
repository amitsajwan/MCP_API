"""
Simple Web UI for MCP API System
===============================
WebSocket interface without complex async operations
"""

import os
import json
import logging
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

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
    
    # Send credentials status
    emit('credentials_status', {
        'configured': has_credentials,
        'message': 'Connected to MCP API System' + (' - Credentials configured' if has_credentials else ' - Click to configure credentials')
    })
    
    emit('connected', {'message': 'Connected to MCP API System'})
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
    
    # Simple response for now (without MCP service)
    response = f"Echo: {user_message}"
    
    # Add bot response to conversation
    conversations[session_id].append({
        "role": "assistant",
        "content": response
    })
    
    # Emit bot response
    emit('bot_message', {'message': response})

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

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 Starting Simple MCP API Web UI...")
    print("📱 Open your browser to: http://localhost:5000")
    print("🔧 This is a simplified version without MCP service integration")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
