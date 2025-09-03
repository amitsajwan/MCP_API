#!/usr/bin/env python3
"""
Enhanced MCP Server with Direct LLM Integration
This server assumes LLM access is always available and uses it for
intelligent argument validation, response enhancement, and dynamic planning.
"""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash
from openai import AzureOpenAI
import yaml
import argparse
import sys

logger = logging.getLogger(__name__)

@dataclass
class EnhancedAPITool:
    """Enhanced API tool with LLM capabilities."""
    name: str
    description: str
    method: str
    path: str
    parameters: Dict[str, Any]
    spec_name: str = ""
    tags: List[str] = field(default_factory=list)
    summary: str = ""
    operation_id: str = ""
    
    # LLM-enhanced fields
    intelligent_validation: bool = True
    auto_fix_args: bool = True
    response_enhancement: bool = True
    usage_patterns: List[str] = field(default_factory=list)
    common_errors: List[str] = field(default_factory=list)
    optimization_hints: List[str] = field(default_factory=list)

@dataclass
class ValidationResult:
    """Result of LLM-powered argument validation."""
    is_valid: bool
    cleaned_args: Dict[str, Any]
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 1.0
    reasoning: str = ""
    auto_fixes: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

@dataclass
class ResponseEnhancement:
    """LLM-enhanced response data."""
    original_response: Dict[str, Any]
    enhanced_response: Dict[str, Any]
    explanations: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class EnhancedMCPServer:
    """Enhanced MCP Server with direct LLM integration for intelligent operations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Flask app
        self.app = Flask(__name__)
        self.app.config['JWT_SECRET_KEY'] = config.get('jwt_secret', 'your-secret-key-change-this')
        
        # Enable CORS
        CORS(self.app)
        
        # Initialize JWT
        self.jwt = JWTManager(self.app)
        
        # Initialize LLM client (assuming always available)
        self._init_llm_client()
        
        # Tool registry
        self.tools: Dict[str, EnhancedAPITool] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        
        # User management (simple in-memory for demo)
        self.users = {
            "admin": {
                "password_hash": generate_password_hash("password123"),
                "role": "admin"
            },
            "user": {
                "password_hash": generate_password_hash("userpass"),
                "role": "user"
            }
        }
        
        # Analytics and learning
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        self.validation_history: List[Dict[str, Any]] = []
        self.learned_patterns: Dict[str, List[str]] = {}
        
        # Setup routes
        self._setup_routes()
        
        logger.info("🚀 Enhanced MCP Server initialized with LLM capabilities")
    
    def _init_llm_client(self):
        """Initialize LLM client - assumes always available."""
        azure_config = self.config.get('azure_openai', {})
        self.llm_client = AzureOpenAI(
            azure_endpoint=azure_config.get('endpoint') or os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=azure_config.get('api_key') or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview"
        )
        self.deployment_name = azure_config.get('deployment', 'gpt-4')
        logger.info("✅ LLM client initialized successfully")
    
    def _setup_routes(self):
        """Setup Flask routes for the MCP server."""
        
        @self.app.route('/auth/login', methods=['POST'])
        def login():
            """Authenticate user and return JWT token."""
            try:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
                
                if not username or not password:
                    return jsonify({'error': 'Username and password required'}), 400
                
                user = self.users.get(username)
                if user and check_password_hash(user['password_hash'], password):
                    access_token = create_access_token(
                        identity=username,
                        additional_claims={'role': user['role']}
                    )
                    
                    logger.info(f"✅ User {username} authenticated successfully")
                    return jsonify({
                        'access_token': access_token,
                        'user': username,
                        'role': user['role']
                    })
                else:
                    logger.warning(f"❌ Failed authentication attempt for {username}")
                    return jsonify({'error': 'Invalid credentials'}), 401
                    
            except Exception as e:
                logger.error(f"❌ Login error: {e}")
                return jsonify({'error': 'Authentication failed'}), 500
        
        @self.app.route('/tools', methods=['GET'])
        @jwt_required()
        def list_tools():
            """List available tools with LLM enhancements."""
            try:
                user = get_jwt_identity()
                logger.info(f"📋 User {user} requesting tool list")
                
                tools_data = []
                for tool_name, tool in self.tools.items():
                    tool_info = {
                        'name': tool.name,
                        'description': tool.description,
                        'method': tool.method,
                        'path': tool.path,
                        'inputSchema': tool.parameters,
                        'tags': tool.tags,
                        'summary': tool.summary,
                        'usage_patterns': tool.usage_patterns,
                        'optimization_hints': tool.optimization_hints
                    }
                    tools_data.append(tool_info)
                
                return jsonify({
                    'tools': tools_data,
                    'total': len(tools_data),
                    'server_capabilities': {
                        'intelligent_validation': True,
                        'auto_fix_arguments': True,
                        'response_enhancement': True,
                        'dynamic_planning': True
                    }
                })
                
            except Exception as e:
                logger.error(f"❌ Error listing tools: {e}")
                return jsonify({'error': 'Failed to list tools'}), 500
        
        @self.app.route('/tools/<tool_name>/call', methods=['POST'])
        @jwt_required()
        def call_tool(tool_name):
            """Execute a tool with intelligent validation and enhancement."""
            start_time = time.time()
            user = get_jwt_identity()
            
            try:
                if tool_name not in self.tools:
                    return jsonify({'error': f'Tool {tool_name} not found'}), 404
                
                if tool_name not in self.tool_handlers:
                    return jsonify({'error': f'No handler for tool {tool_name}'}), 500
                
                # Get request data
                data = request.get_json()
                arguments = data.get('arguments', {})
                
                logger.info(f"🔧 User {user} calling tool {tool_name}")
                
                tool = self.tools[tool_name]
                
                # Intelligent argument validation
                if tool.intelligent_validation:
                    validation = self._validate_arguments_with_llm(tool, arguments)
                    
                    if not validation.is_valid:
                        logger.warning(f"⚠️ Validation failed for {tool_name}: {validation.reasoning}")
                        return jsonify({
                            'error': 'Argument validation failed',
                            'validation_result': {
                                'suggestions': validation.suggestions,
                                'reasoning': validation.reasoning,
                                'confidence': validation.confidence
                            }
                        }), 400
                    
                    # Use cleaned arguments
                    if tool.auto_fix_args:
                        arguments = validation.cleaned_args
                        
                        if validation.auto_fixes:
                            logger.info(f"🔧 Applied auto-fixes for {tool_name}: {validation.auto_fixes}")
                
                # Execute the tool
                handler = self.tool_handlers[tool_name]
                result = handler(arguments)
                
                execution_time = time.time() - start_time
                
                # Enhance response with LLM if enabled
                if tool.response_enhancement:
                    enhancement = self._enhance_response_with_llm(tool, arguments, result)
                    result = enhancement.enhanced_response
                
                # Record execution statistics
                self._record_execution_stats(tool_name, arguments, result, execution_time, True, user)
                
                logger.info(f"✅ Tool {tool_name} executed successfully in {execution_time:.2f}s")
                
                return jsonify({
                    'result': result,
                    'execution_time': execution_time,
                    'tool_name': tool_name,
                    'enhanced': tool.response_enhancement
                })
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = str(e)
                
                # Record failed execution
                self._record_execution_stats(tool_name, arguments, {'error': error_msg}, execution_time, False, user)
                
                # Get intelligent error analysis
                error_analysis = self._analyze_error_with_llm(tool_name, arguments, error_msg)
                
                logger.error(f"❌ Tool {tool_name} execution failed: {error_msg}")
                
                return jsonify({
                    'error': error_msg,
                    'error_analysis': error_analysis,
                    'execution_time': execution_time,
                    'tool_name': tool_name
                }), 500
        
        @self.app.route('/tools/<tool_name>/validate', methods=['POST'])
        @jwt_required()
        def validate_arguments(tool_name):
            """Validate arguments for a tool using LLM."""
            try:
                if tool_name not in self.tools:
                    return jsonify({'error': f'Tool {tool_name} not found'}), 404
                
                data = request.get_json()
                arguments = data.get('arguments', {})
                
                tool = self.tools[tool_name]
                validation = self._validate_arguments_with_llm(tool, arguments)
                
                return jsonify({
                    'is_valid': validation.is_valid,
                    'cleaned_args': validation.cleaned_args,
                    'suggestions': validation.suggestions,
                    'confidence': validation.confidence,
                    'reasoning': validation.reasoning,
                    'auto_fixes': validation.auto_fixes,
                    'warnings': validation.warnings
                })
                
            except Exception as e:
                logger.error(f"❌ Validation error: {e}")
                return jsonify({'error': 'Validation failed'}), 500
        
        @self.app.route('/analytics/stats', methods=['GET'])
        @jwt_required()
        def get_analytics():
            """Get server analytics and insights."""
            try:
                return jsonify({
                    'execution_stats': self.execution_stats,
                    'learned_patterns': self.learned_patterns,
                    'total_tools': len(self.tools),
                    'validation_history_count': len(self.validation_history)
                })
            except Exception as e:
                logger.error(f"❌ Analytics error: {e}")
                return jsonify({'error': 'Failed to get analytics'}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'tools_count': len(self.tools),
                'llm_available': True
            })
    
    def _validate_arguments_with_llm(self, tool: EnhancedAPITool, arguments: Dict[str, Any]) -> ValidationResult:
        """Use LLM to intelligently validate and enhance arguments."""
        try:
            prompt = f"""
Validate and enhance these API arguments:

**Tool:** {tool.name}
**Description:** {tool.description}
**Method:** {tool.method}
**Path:** {tool.path}
**Schema:** {json.dumps(tool.parameters, indent=2)}
**Arguments:** {json.dumps(arguments, indent=2)}
**Usage Patterns:** {tool.usage_patterns}
**Common Errors:** {tool.common_errors}

Analyze the arguments and provide:
1. Are they valid? (true/false)
2. Cleaned/enhanced arguments (fix types, add defaults, format correctly)
3. Suggestions for improvement
4. Confidence score (0.0-1.0)
5. Reasoning for validation decision
6. Auto-fixes applied
7. Warnings about potential issues

Format as JSON:
{{
  "is_valid": true/false,
  "cleaned_args": {{...}},
  "suggestions": ["suggestion1", ...],
  "confidence": 0.95,
  "reasoning": "detailed explanation",
  "auto_fixes": {{"field": "fix_description"}},
  "warnings": ["warning1", ...]
}}
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert API argument validator. Provide thorough validation with helpful suggestions and auto-fixes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            result_data = json.loads(response.choices[0].message.content)
            
            validation_result = ValidationResult(
                is_valid=result_data.get('is_valid', False),
                cleaned_args=result_data.get('cleaned_args', arguments),
                suggestions=result_data.get('suggestions', []),
                confidence=result_data.get('confidence', 0.5),
                reasoning=result_data.get('reasoning', ''),
                auto_fixes=result_data.get('auto_fixes', {}),
                warnings=result_data.get('warnings', [])
            )
            
            # Record validation for learning
            self.validation_history.append({
                "timestamp": datetime.now().isoformat(),
                "tool_name": tool.name,
                "arguments": arguments,
                "validation_result": result_data
            })
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ LLM validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                cleaned_args=arguments,
                suggestions=[f"Validation error: {str(e)}"],
                confidence=0.0,
                reasoning=f"LLM validation failed: {str(e)}"
            )
    
    def _enhance_response_with_llm(self, tool: EnhancedAPITool, arguments: Dict[str, Any], 
                                  response: Dict[str, Any]) -> ResponseEnhancement:
        """Enhance API response with LLM insights."""
        try:
            prompt = f"""
Enhance this API response with helpful insights:

**Tool:** {tool.name}
**Description:** {tool.description}
**Arguments Used:** {json.dumps(arguments, indent=2)}
**Original Response:** {json.dumps(response, indent=2)}
**Usage Patterns:** {tool.usage_patterns}

Provide:
1. Enhanced response with additional helpful information
2. Explanations of the response data
3. Suggestions for next steps or related actions
4. Metadata about the response quality/completeness

Format as JSON:
{{
  "enhanced_response": {{...}},
  "explanations": ["explanation1", ...],
  "suggestions": ["suggestion1", ...],
  "metadata": {{
    "quality_score": 0.95,
    "completeness": "high",
    "confidence": 0.9
  }}
}}
"""
            
            llm_response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API response enhancement expert. Add valuable insights while preserving original data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            enhancement_data = json.loads(llm_response.choices[0].message.content)
            
            return ResponseEnhancement(
                original_response=response,
                enhanced_response=enhancement_data.get('enhanced_response', response),
                explanations=enhancement_data.get('explanations', []),
                suggestions=enhancement_data.get('suggestions', []),
                metadata=enhancement_data.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"❌ Response enhancement failed: {e}")
            return ResponseEnhancement(
                original_response=response,
                enhanced_response=response,
                explanations=[f"Enhancement failed: {str(e)}"],
                suggestions=[],
                metadata={"enhancement_error": str(e)}
            )
    
    def _analyze_error_with_llm(self, tool_name: str, arguments: Dict[str, Any], 
                               error_message: str) -> Dict[str, Any]:
        """Analyze errors using LLM to provide intelligent suggestions."""
        try:
            tool = self.tools.get(tool_name)
            
            prompt = f"""
Analyze this API execution error and provide helpful insights:

**Tool:** {tool_name}
**Arguments:** {json.dumps(arguments, indent=2)}
**Error Message:** {error_message}
**Tool Schema:** {json.dumps(tool.parameters if tool else {}, indent=2)}
**Common Errors:** {tool.common_errors if tool else []}
**Recent Stats:** {self.execution_stats.get(tool_name, {})}

Provide:
1. Likely cause of the error
2. Specific suggestions to fix it
3. Alternative approaches
4. Whether this is a common issue
5. Prevention strategies

Format as JSON:
{{
  "likely_cause": "detailed explanation",
  "suggestions": ["fix1", "fix2", ...],
  "alternatives": ["approach1", "approach2", ...],
  "is_common": true/false,
  "severity": "low/medium/high",
  "prevention": ["strategy1", "strategy2", ...]
}}
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API error analysis expert. Provide actionable insights for fixing errors."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=700
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Failed to analyze error with LLM: {e}")
            return {
                "likely_cause": "Unknown error",
                "suggestions": ["Check the error message and tool documentation"],
                "alternatives": [],
                "is_common": False,
                "severity": "medium",
                "prevention": ["Validate arguments before execution"]
            }
    
    def _record_execution_stats(self, tool_name: str, arguments: Dict[str, Any], 
                               result: Dict[str, Any], execution_time: float, 
                               success: bool, user: str):
        """Record execution statistics for analytics and learning."""
        if tool_name not in self.execution_stats:
            self.execution_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "last_called": None,
                "users": set(),
                "common_args": {},
                "error_patterns": []
            }
        
        stats = self.execution_stats[tool_name]
        stats["total_calls"] += 1
        stats["total_time"] += execution_time
        stats["avg_time"] = stats["total_time"] / stats["total_calls"]
        stats["last_called"] = datetime.now().isoformat()
        stats["users"].add(user)
        
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
            if "error" in result:
                stats["error_patterns"].append(result["error"])
        
        # Track common argument patterns
        for key, value in arguments.items():
            if key not in stats["common_args"]:
                stats["common_args"][key] = {}
            
            value_str = str(value)
            if value_str not in stats["common_args"][key]:
                stats["common_args"][key][value_str] = 0
            stats["common_args"][key][value_str] += 1
        
        # Convert sets to lists for JSON serialization
        stats["users"] = list(stats["users"])
    
    def register_tool(self, tool: EnhancedAPITool, handler: Callable):
        """Register a tool with its handler function."""
        # Enhance tool with LLM insights
        self._enhance_tool_with_llm(tool)
        
        self.tools[tool.name] = tool
        self.tool_handlers[tool.name] = handler
        
        logger.info(f"🔧 Registered enhanced tool: {tool.name}")
    
    def _enhance_tool_with_llm(self, tool: EnhancedAPITool):
        """Enhance tool definition with LLM insights."""
        try:
            prompt = f"""
Analyze this API tool and provide enhancement insights:

**Tool Name:** {tool.name}
**Description:** {tool.description}
**Method:** {tool.method}
**Path:** {tool.path}
**Parameters:** {json.dumps(tool.parameters, indent=2)}

Provide:
1. 5 common usage patterns
2. 5 common errors users might encounter
3. 5 optimization hints for better performance

Format as JSON:
{{
  "usage_patterns": ["pattern1", "pattern2", ...],
  "common_errors": ["error1", "error2", ...],
  "optimization_hints": ["hint1", "hint2", ...]
}}
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API tool enhancement expert. Provide practical insights for tool optimization."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )
            
            insights = json.loads(response.choices[0].message.content)
            
            tool.usage_patterns = insights.get('usage_patterns', [])
            tool.common_errors = insights.get('common_errors', [])
            tool.optimization_hints = insights.get('optimization_hints', [])
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to enhance tool {tool.name} with LLM: {e}")
    
    def run(self, host: str = '0.0.0.0', port: int = 8000, debug: bool = False):
        """Run the enhanced MCP server."""
        logger.info(f"🚀 Starting Enhanced MCP Server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

# Example tool implementations
def create_sample_tools(server: EnhancedMCPServer):
    """Create sample tools for demonstration."""
    
    # Payment creation tool
    def create_payment_handler(args):
        """Handle payment creation."""
        amount = float(args.get('amount', 0))
        currency = args.get('currency', 'USD')
        description = args.get('description', '')
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Simulate payment creation
        payment_id = f"pay_{int(time.time())}"
        
        return {
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "description": description,
            "status": "created",
            "created_at": datetime.now().isoformat()
        }
    
    payment_tool = EnhancedAPITool(
        name="createPayment",
        description="Create a new payment transaction",
        method="POST",
        path="/payments",
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "number", "minimum": 0.01},
                "currency": {"type": "string", "enum": ["USD", "EUR", "GBP"]},
                "description": {"type": "string", "maxLength": 255}
            },
            "required": ["amount", "currency"]
        },
        tags=["payments"],
        summary="Create payment"
    )
    
    server.register_tool(payment_tool, create_payment_handler)
    
    # Balance check tool
    def get_balance_handler(args):
        """Handle balance retrieval."""
        account_id = args.get('account_id')
        
        if not account_id:
            raise ValueError("Account ID is required")
        
        # Simulate balance retrieval
        return {
            "account_id": account_id,
            "balance": 1250.75,
            "currency": "USD",
            "last_updated": datetime.now().isoformat()
        }
    
    balance_tool = EnhancedAPITool(
        name="getBalance",
        description="Get account balance",
        method="GET",
        path="/accounts/{account_id}/balance",
        parameters={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "pattern": "^acc_[a-zA-Z0-9]+$"}
            },
            "required": ["account_id"]
        },
        tags=["accounts"],
        summary="Get balance"
    )
    
    server.register_tool(balance_tool, get_balance_handler)

if __name__ == "__main__":
    # Configuration
    config = {
        "jwt_secret": "your-secret-key-change-this-in-production",
        "azure_openai": {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "deployment": "gpt-4"
        }
    }
    
    # Create enhanced server
    server = EnhancedMCPServer(config)
    
    # Register sample tools
    create_sample_tools(server)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enhanced MCP Server with LLM Integration')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Run the server
        server.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("🛑 Enhanced MCP Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)