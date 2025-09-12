#!/usr/bin/env python3
"""
Web UI for MCP API - Intelligent LLM Tool Orchestration
Demonstrates modern LLM capabilities with real-time tool execution
"""

import os
import json
import logging
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('web_ui_mock.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# MCP service with intelligent tool orchestration
class IntelligentMCPService:
    def __init__(self):
        self.initialized = True
        self.tools = self._create_mock_tools()
        self.session_id = None
        
    def _create_mock_tools(self):
        """Create tools for intelligent orchestration"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "cash_api_getPayments",
                    "description": "Get all payments from the cash management system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "description": "Payment status filter"},
                            "limit": {"type": "integer", "description": "Maximum number of payments to return"}
                        }
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "cash_api_createPayment",
                    "description": "Create a new payment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "number", "description": "Payment amount"},
                            "currency": {"type": "string", "description": "Payment currency"},
                            "recipient": {"type": "string", "description": "Payment recipient"}
                        },
                        "required": ["amount", "currency", "recipient"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "securities_api_getPortfolio",
                    "description": "Get current portfolio holdings",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string", "description": "Account identifier"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_credentials",
                    "description": "Set API credentials for authentication",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"},
                            "api_key_name": {"type": "string"},
                            "api_key_value": {"type": "string"},
                            "login_url": {"type": "string"},
                            "base_url": {"type": "string"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "perform_login",
                    "description": "Perform login to get session ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "force_login": {"type": "boolean"}
                        }
                    }
                }
            }
        ]
    
    def process_message(self, user_message):
        """Intelligent message processing with tool orchestration"""
        logger.info(f"[INTELLIGENT_MCP] Processing message: '{user_message[:100]}...'")
        
        # Simulate intelligent tool selection based on message content
        tool_calls = []
        response = ""
        
        if "payment" in user_message.lower():
            # Simulate payment-related tool calls
            tool_calls.append({
                "tool_call_id": "call_123",
                "tool_name": "cash_api_getPayments",
                "args": {"status": "pending", "limit": 10},
                "result": {
                    "payments": [
                        {"id": "PAY001", "amount": 1000, "currency": "USD", "status": "pending"},
                        {"id": "PAY002", "amount": 2500, "currency": "EUR", "status": "completed"}
                    ]
                }
            })
            response = "I found 2 payments in the system. One pending payment of $1,000 USD and one completed payment of €2,500 EUR."
            
        elif "portfolio" in user_message.lower() or "holdings" in user_message.lower():
            # Simulate portfolio tool calls
            tool_calls.append({
                "tool_call_id": "call_456",
                "tool_name": "securities_api_getPortfolio",
                "args": {"account_id": "ACC123"},
                "result": {
                    "holdings": [
                        {"symbol": "AAPL", "shares": 100, "value": 15000},
                        {"symbol": "GOOGL", "shares": 50, "value": 12000}
                    ],
                    "total_value": 27000
                }
            })
            response = "Your portfolio shows holdings worth $27,000 total: 100 shares of AAPL ($15,000) and 50 shares of GOOGL ($12,000)."
            
        elif "login" in user_message.lower() or "credentials" in user_message.lower():
            # Simulate login process
            tool_calls.append({
                "tool_call_id": "call_789",
                "tool_name": "set_credentials",
                "args": {"username": "user123", "password": "***"},
                "result": {"status": "success", "message": "Credentials set successfully"}
            })
            tool_calls.append({
                "tool_call_id": "call_790",
                "tool_name": "perform_login",
                "args": {"force_login": True},
                "result": {"status": "success", "session_id": "JSESSIONID_ABC123XYZ789"}
            })
            response = "Login successful! I've set your credentials and obtained session ID: JSESSIONID_ABC123XYZ789. You can now access all API functions."
            
        else:
            response = "I can help you with payments, portfolio management, and other financial operations. What would you like to do?"
        
        # Simulate capabilities analysis
        capabilities = {
            "intelligent_selection": len(tool_calls) > 0,
            "tool_chaining": len(tool_calls) > 1,
            "error_handling": False,
            "adaptive_usage": len(tool_calls) > 0,
            "reasoning": len(tool_calls) > 0,
            "descriptions": []
        }
        
        if capabilities["intelligent_selection"]:
            capabilities["descriptions"].append("Intelligent tool selection")
        if capabilities["tool_chaining"]:
            capabilities["descriptions"].append("Tool chaining")
        if capabilities["adaptive_usage"]:
            capabilities["descriptions"].append("Adaptive tool usage")
        if capabilities["reasoning"]:
            capabilities["descriptions"].append("Reasoning about results")
        
        return {
            "success": True,
            "response": response,
            "tool_calls": tool_calls,
            "capabilities": capabilities
        }

# Global intelligent MCP service
mcp_service = IntelligentMCPService()

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
    logger.info(f"[UI] Client connected: {session_id}")
    
    # Initialize conversation history
    conversations[session_id] = []
    
    # Check credentials status
    credentials_configured = bool(os.getenv('API_USERNAME') and os.getenv('API_PASSWORD'))
    logger.info(f"[UI] Credentials status for {session_id}: {'configured' if credentials_configured else 'not configured'}")
    
    emit('connected', {'message': 'Connected to Intelligent MCP Server'})
    emit('credentials_status', {
        'configured': credentials_configured,
        'message': 'Credentials configured' if credentials_configured else 'Please configure credentials (Demo mode - any values work)'
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
    
    # Process with mock MCP service
    try:
        logger.info(f"[UI] Processing message with Intelligent MCP service for {session_id}")
        
        # Process message
        result = mcp_service.process_message(user_message)
        
        if result.get('success'):
            response = result.get('response', 'No response generated')
            logger.info(f"[UI] Intelligent MCP service response for {session_id}: {response}")
            
            # Add bot response to conversation
            conversations[session_id].append({'role': 'assistant', 'content': response})
            
            # Emit bot response
            emit('bot_message', {'message': response})
            
            # Emit tool calls if any
            if 'tool_calls' in result:
                for tool_call in result['tool_calls']:
                    emit('tool_call', {
                        'tool_name': tool_call.get('name', 'Unknown'),
                        'status': 'completed',
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
            logger.error(f"[UI] Intelligent MCP service error for {session_id}: {error_msg}")
            emit('error', {'message': f'Error: {error_msg}'})
            
    except Exception as e:
        logger.error(f"[UI] Error processing message for {session_id}: {e}")
        emit('error', {'message': f'Error processing message: {str(e)}'})

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
        
        # Simulate login process
        logger.info(f"[UI] Simulating login for {session_id}")
        
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
    
    tools = mcp_service.tools
    logger.info(f"[UI] Found {len(tools)} tools for {session_id}")
    emit('tools_list', {'tools': tools})

if __name__ == '__main__':
    logger.info("[UI] Starting Intelligent Web UI...")
    logger.info("[UI] Demo mode - simulating intelligent tool orchestration")
    
    logger.info("[UI] Starting Flask-SocketIO server...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
