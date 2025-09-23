#!/usr/bin/env python3
"""
Simple Dependency-Aware MCP Server
==================================
A working implementation that demonstrates dependency detection and smart tool creation.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP app
app = FastMCP("dependency-aware-mcp-server")

class SimpleDependencyAnalyzer:
    """Simple dependency analyzer using basic pattern matching"""
    
    def __init__(self):
        self.dependencies = {}
    
    def analyze_openapi_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze OpenAPI spec and detect dependencies"""
        
        dependencies = {}
        paths = spec.get('paths', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete']:
                    operation_id = operation.get('operationId', f"{method}_{path}")
                    deps = self._detect_dependencies(path, operation, spec)
                    if deps:
                        dependencies[operation_id] = deps
        
        return dependencies
    
    def _detect_dependencies(self, path: str, operation: Dict, spec: Dict) -> List[Dict]:
        """Detect dependencies for a single operation"""
        dependencies = []
        
        # Check for path parameters that might need other endpoints
        path_params = self._extract_path_params(path)
        
        for param in path_params:
            # Simple heuristic: if param ends with '_id', it might need another endpoint
            if param.endswith('_id'):
                # Try to find a corresponding get endpoint
                base_param = param.replace('_id', '')
                get_endpoint = self._find_get_endpoint_for_param(base_param, spec)
                
                if get_endpoint:
                    dependencies.append({
                        'type': 'parameter_dependency',
                        'parameter': param,
                        'source_endpoint': get_endpoint,
                        'description': f"{param} must be obtained from {get_endpoint} first"
                    })
        
        return dependencies
    
    def _extract_path_params(self, path: str) -> List[str]:
        """Extract path parameters from OpenAPI path"""
        import re
        return re.findall(r'\{([^}]+)\}', path)
    
    def _find_get_endpoint_for_param(self, param_base: str, spec: Dict) -> Optional[str]:
        """Find a GET endpoint that might provide the required parameter"""
        paths = spec.get('paths', {})
        
        # Look for endpoints that might return the required data
        candidates = [
            f"/{param_base}s",  # /accounts
            f"/{param_base}",   # /account
            f"/user/{param_base}s",  # /user/accounts
        ]
        
        for candidate in candidates:
            if candidate in paths and 'get' in paths[candidate]:
                return paths[candidate]['get'].get('operationId', f"get{candidate.replace('/', '_')}")
        
        return None

class SimpleDependencyMCPServer:
    """Simple MCP server with dependency awareness"""
    
    def __init__(self):
        self.dependency_analyzer = SimpleDependencyAnalyzer()
        self.dependencies = {}
        self.mock_data = {
            'users': [
                {'id': 'user_1', 'name': 'John Doe', 'email': 'john@example.com'},
                {'id': 'user_2', 'name': 'Jane Smith', 'email': 'jane@example.com'}
            ],
            'accounts': [
                {'id': 'acc_1', 'user_id': 'user_1', 'name': 'Personal Account', 'type': 'checking'},
                {'id': 'acc_2', 'user_id': 'user_1', 'name': 'Business Account', 'type': 'business'},
                {'id': 'acc_3', 'user_id': 'user_2', 'name': 'Savings Account', 'type': 'savings'}
            ],
            'mails': [
                {'id': 'mail_1', 'account_id': 'acc_1', 'subject': 'Welcome Email', 'from': 'system@bank.com'},
                {'id': 'mail_2', 'account_id': 'acc_1', 'subject': 'Account Statement', 'from': 'statements@bank.com'},
                {'id': 'mail_3', 'account_id': 'acc_2', 'subject': 'Business Update', 'from': 'business@bank.com'},
                {'id': 'mail_4', 'account_id': 'acc_3', 'subject': 'Interest Rate Change', 'from': 'rates@bank.com'}
            ]
        }
    
    def load_openapi_spec(self, spec: Dict[str, Any]):
        """Load OpenAPI spec and analyze dependencies"""
        logger.info("🔍 Analyzing OpenAPI spec for dependencies...")
        self.dependencies = self.dependency_analyzer.analyze_openapi_spec(spec)
        logger.info(f"✅ Found {len(self.dependencies)} operations with dependencies")
        
        # Register tools
        self._register_tools(spec)
    
    def _register_tools(self, spec: Dict[str, Any]):
        """Register tools with dependency awareness"""
        
        # Register getUsers tool
        @app.tool()
        async def get_users() -> str:
            """Get all users"""
            logger.info("📞 get_users called")
            return json.dumps({
                "status": "success",
                "data": self.mock_data['users'],
                "message": "Users retrieved successfully"
            }, indent=2)
        
        # Register getAccounts tool
        @app.tool()
        async def get_accounts(user_id: str = None) -> str:
            """Get accounts, optionally filtered by user_id"""
            logger.info(f"📞 get_accounts called with user_id: {user_id}")
            
            accounts = self.mock_data['accounts']
            if user_id:
                accounts = [acc for acc in accounts if acc['user_id'] == user_id]
            
            return json.dumps({
                "status": "success",
                "data": accounts,
                "message": f"Found {len(accounts)} accounts"
            }, indent=2)
        
        # Register getMails tool with dependency awareness
        @app.tool()
        async def get_mails(account_id: str = None, user_id: str = None) -> str:
            """
            Get emails for a specific account.
            
            DEPENDENCIES:
            - account_id: Required parameter that must be obtained from getAccounts
            - user_id: Optional, if provided will get accounts for user first
            
            DEPENDENCY_CHAIN:
            1. getAccounts(user_id) - Get accounts for user (if user_id provided)
            2. getMails(account_id) - Get emails for specific account
            """
            logger.info(f"📞 get_mails called with account_id: {account_id}, user_id: {user_id}")
            
            # Check dependencies
            if not account_id and not user_id:
                return json.dumps({
                    "status": "prerequisite_required",
                    "message": "account_id is required to get emails",
                    "prerequisite": {
                        "operation": "getAccounts",
                        "purpose": "Get account_id for email retrieval",
                        "description": "Call getAccounts first to obtain the account_id needed for getMails"
                    },
                    "suggested_workflow": [
                        "1. Call getAccounts() to get available accounts",
                        "2. Select account_id from the results", 
                        "3. Call getMails(account_id='acc_123') with the selected account_id"
                    ],
                    "example_usage": "getAccounts() → getMails(account_id='acc_123')"
                }, indent=2)
            
            # If user_id provided but no account_id, get accounts first
            if user_id and not account_id:
                accounts = [acc for acc in self.mock_data['accounts'] if acc['user_id'] == user_id]
                return json.dumps({
                    "status": "accounts_found",
                    "message": f"Found {len(accounts)} accounts for user {user_id}",
                    "accounts": accounts,
                    "next_step": "Call getMails with account_id from the accounts above",
                    "example": f"getMails(account_id='{accounts[0]['id'] if accounts else 'acc_1'}')"
                }, indent=2)
            
            # Get emails for the account
            mails = [mail for mail in self.mock_data['mails'] if mail['account_id'] == account_id]
            
            return json.dumps({
                "status": "success",
                "data": mails,
                "message": f"Found {len(mails)} emails for account {account_id}",
                "account_id": account_id
            }, indent=2)
        
        # Register getMailsSmart tool with auto-dependency resolution
        @app.tool()
        async def get_mails_smart(account_identifier: str = None, user_identifier: str = None) -> str:
            """
            Smart email retrieval that can resolve dependencies automatically.
            
            INTELLIGENT_PARAMETER_HANDLING:
            - account_identifier: Can be account_id, account_name, or user_id
            - user_identifier: User ID or email address
            - Auto-resolves dependencies intelligently
            """
            logger.info(f"📞 get_mails_smart called with account_identifier: {account_identifier}, user_identifier: {user_identifier}")
            
            # No identifiers provided - show available options
            if not account_identifier and not user_identifier:
                return json.dumps({
                    "status": "identifiers_required",
                    "message": "Please provide account_identifier or user_identifier",
                    "available_options": {
                        "users": self.mock_data['users'],
                        "accounts": self.mock_data['accounts']
                    },
                    "examples": [
                        "get_mails_smart(account_identifier='acc_1')",
                        "get_mails_smart(user_identifier='user_1')",
                        "get_mails_smart(account_identifier='Personal Account')"
                    ]
                }, indent=2)
            
            # Try to resolve account_id
            account_id = None
            
            if account_identifier:
                # Check if it's a direct account_id
                if account_identifier.startswith('acc_'):
                    account_id = account_identifier
                else:
                    # Try to find by account name
                    for acc in self.mock_data['accounts']:
                        if acc['name'].lower() == account_identifier.lower():
                            account_id = acc['id']
                            break
                    
                    # If not found by name, might be user_id
                    if not account_id:
                        for acc in self.mock_data['accounts']:
                            if acc['user_id'] == account_identifier:
                                account_id = acc['id']
                                break
            
            # If user_identifier provided, get accounts for that user
            if user_identifier and not account_id:
                user_accounts = []
                for acc in self.mock_data['accounts']:
                    if acc['user_id'] == user_identifier:
                        user_accounts.append(acc)
                
                if user_accounts:
                    return json.dumps({
                        "status": "user_accounts_found",
                        "message": f"Found {len(user_accounts)} accounts for user {user_identifier}",
                        "accounts": user_accounts,
                        "next_step": "Call get_mails_smart with account_identifier from the accounts above",
                        "example": f"get_mails_smart(account_identifier='{user_accounts[0]['id']}')"
                    }, indent=2)
            
            # Get emails for the resolved account
            if account_id:
                mails = [mail for mail in self.mock_data['mails'] if mail['account_id'] == account_id]
                return json.dumps({
                    "status": "success",
                    "data": mails,
                    "message": f"Found {len(mails)} emails for account {account_id}",
                    "account_id": account_id,
                    "dependency_resolved": True
                }, indent=2)
            else:
                return json.dumps({
                    "status": "account_not_found",
                    "message": f"Could not resolve account for identifier: {account_identifier}",
                    "available_accounts": self.mock_data['accounts']
                }, indent=2)

def main():
    """Main entry point"""
    logger.info("🚀 Starting Simple Dependency-Aware MCP Server...")
    
    # Create server
    server = SimpleDependencyMCPServer()
    
    # Load a simple OpenAPI spec
    simple_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Simple API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "getUsers",
                    "summary": "Get all users"
                }
            },
            "/accounts": {
                "get": {
                    "operationId": "getAccounts",
                    "summary": "Get accounts",
                    "parameters": [
                        {"name": "user_id", "in": "query", "schema": {"type": "string"}}
                    ]
                }
            },
            "/accounts/{account_id}/mails": {
                "get": {
                    "operationId": "getMails",
                    "summary": "Get emails for account",
                    "parameters": [
                        {"name": "account_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            }
        }
    }
    
    # Load spec and analyze dependencies
    server.load_openapi_spec(simple_spec)
    
    # Start the server
    logger.info("🌐 Starting MCP server with stdio transport...")
    app.run(transport="stdio")

if __name__ == "__main__":
    main()