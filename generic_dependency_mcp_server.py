#!/usr/bin/env python3
"""
Generic Dependency-Aware MCP Server
===================================
Works with ANY API and ANY user query by understanding dependencies dynamically.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP app
app = FastMCP("generic-dependency-mcp-server")

class GenericDependencyAnalyzer:
    """Generic dependency analyzer that works with any API"""
    
    def __init__(self):
        self.dependencies = {}
        self.endpoint_map = {}
    
    def analyze_openapi_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ANY OpenAPI spec and detect dependencies"""
        
        dependencies = {}
        paths = spec.get('paths', {})
        
        # Build endpoint map
        self.endpoint_map = {}
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    operation_id = operation.get('operationId', f"{method}_{path}")
                    self.endpoint_map[operation_id] = {
                        'path': path,
                        'method': method,
                        'operation': operation
                    }
        
        # Analyze dependencies for each endpoint
        for operation_id, endpoint_info in self.endpoint_map.items():
            deps = self._detect_generic_dependencies(operation_id, endpoint_info, spec)
            if deps:
                dependencies[operation_id] = deps
        
        return dependencies
    
    def _detect_generic_dependencies(self, operation_id: str, endpoint_info: Dict, spec: Dict) -> List[Dict]:
        """Detect dependencies for any endpoint using generic patterns"""
        dependencies = []
        path = endpoint_info['path']
        operation = endpoint_info['operation']
        
        # Pattern 1: Path parameters that need other endpoints
        path_params = self._extract_path_params(path)
        for param in path_params:
            source_endpoint = self._find_source_endpoint_for_param(param, spec)
            if source_endpoint:
                dependencies.append({
                    'type': 'path_parameter_dependency',
                    'parameter': param,
                    'source_endpoint': source_endpoint,
                    'description': f"{param} must be obtained from {source_endpoint} first"
                })
        
        # Pattern 2: Query parameters that might need other endpoints
        parameters = operation.get('parameters', [])
        for param in parameters:
            if param.get('in') == 'query':
                param_name = param.get('name')
                if self._is_reference_parameter(param_name):
                    source_endpoint = self._find_source_endpoint_for_param(param_name, spec)
                    if source_endpoint:
                        dependencies.append({
                            'type': 'query_parameter_dependency',
                            'parameter': param_name,
                            'source_endpoint': source_endpoint,
                            'description': f"{param_name} might need to be obtained from {source_endpoint}"
                        })
        
        # Pattern 3: Request body dependencies
        request_body = operation.get('requestBody', {})
        if request_body:
            body_deps = self._analyze_request_body_dependencies(request_body, spec)
            dependencies.extend(body_deps)
        
        return dependencies
    
    def _extract_path_params(self, path: str) -> List[str]:
        """Extract path parameters from any OpenAPI path"""
        return re.findall(r'\{([^}]+)\}', path)
    
    def _is_reference_parameter(self, param_name: str) -> bool:
        """Check if parameter is likely a reference to another entity"""
        reference_patterns = [
            r'.*_id$',           # user_id, account_id, order_id
            r'.*_uuid$',         # user_uuid, session_uuid
            r'.*_key$',          # api_key, access_key
            r'^id$',             # just 'id'
            r'^uuid$',           # just 'uuid'
        ]
        
        for pattern in reference_patterns:
            if re.match(pattern, param_name, re.IGNORECASE):
                return True
        return False
    
    def _find_source_endpoint_for_param(self, param: str, spec: Dict) -> Optional[str]:
        """Find endpoint that might provide the required parameter"""
        
        # Strategy 1: Direct entity endpoints
        entity_name = self._extract_entity_name(param)
        candidates = [
            f"/{entity_name}s",           # /users, /accounts, /orders
            f"/{entity_name}",            # /user, /account, /order
            f"/{entity_name}es",          # /companies -> /companies
            f"/{entity_name}ies",         # /categories -> /categories
        ]
        
        for candidate in candidates:
            if candidate in spec.get('paths', {}):
                get_operation = spec['paths'][candidate].get('get')
                if get_operation:
                    return get_operation.get('operationId', f"get{candidate.replace('/', '_')}")
        
        # Strategy 2: Search by operationId patterns
        for operation_id in self.endpoint_map.keys():
            if self._matches_entity_pattern(operation_id, entity_name):
                return operation_id
        
        return None
    
    def _extract_entity_name(self, param: str) -> str:
        """Extract entity name from parameter"""
        # Remove common suffixes
        entity = re.sub(r'_(id|uuid|key)$', '', param, flags=re.IGNORECASE)
        return entity.lower()
    
    def _matches_entity_pattern(self, operation_id: str, entity_name: str) -> bool:
        """Check if operation_id matches entity pattern"""
        patterns = [
            f"get{entity_name}s",
            f"get{entity_name}",
            f"list{entity_name}s",
            f"list{entity_name}",
            f"find{entity_name}s",
            f"find{entity_name}",
        ]
        
        for pattern in patterns:
            if operation_id.lower() == pattern.lower():
                return True
        return False
    
    def _analyze_request_body_dependencies(self, request_body: Dict, spec: Dict) -> List[Dict]:
        """Analyze request body for dependencies"""
        dependencies = []
        
        content = request_body.get('content', {})
        if 'application/json' in content:
            schema = content['application/json'].get('schema', {})
            if '$ref' in schema:
                # Resolve schema and check for reference fields
                resolved_schema = self._resolve_schema_ref(schema['$ref'], spec)
                if resolved_schema:
                    deps = self._find_schema_dependencies(resolved_schema, spec)
                    dependencies.extend(deps)
        
        return dependencies
    
    def _resolve_schema_ref(self, ref: str, spec: Dict) -> Optional[Dict]:
        """Resolve schema reference"""
        if ref.startswith('#/components/schemas/'):
            schema_name = ref.split('/')[-1]
            schemas = spec.get('components', {}).get('schemas', {})
            return schemas.get(schema_name)
        return None
    
    def _find_schema_dependencies(self, schema: Dict, spec: Dict) -> List[Dict]:
        """Find dependencies in schema properties"""
        dependencies = []
        properties = schema.get('properties', {})
        
        for prop_name, prop_schema in properties.items():
            if self._is_reference_parameter(prop_name):
                source_endpoint = self._find_source_endpoint_for_param(prop_name, spec)
                if source_endpoint:
                    dependencies.append({
                        'type': 'schema_property_dependency',
                        'parameter': prop_name,
                        'source_endpoint': source_endpoint,
                        'description': f"{prop_name} in request body needs to be obtained from {source_endpoint}"
                    })
        
        return dependencies

class GenericDependencyMCPServer:
    """Generic MCP server that works with any API"""
    
    def __init__(self):
        self.dependency_analyzer = GenericDependencyAnalyzer()
        self.dependencies = {}
        self.endpoint_map = {}
        self.mock_data = self._create_comprehensive_mock_data()
    
    def _create_comprehensive_mock_data(self) -> Dict[str, Any]:
        """Create comprehensive mock data for various API scenarios"""
        return {
            # User Management
            'users': [
                {'id': 'user_1', 'name': 'John Doe', 'email': 'john@example.com', 'role': 'admin'},
                {'id': 'user_2', 'name': 'Jane Smith', 'email': 'jane@example.com', 'role': 'user'},
                {'id': 'user_3', 'name': 'Bob Wilson', 'email': 'bob@example.com', 'role': 'user'}
            ],
            
            # Account Management
            'accounts': [
                {'id': 'acc_1', 'user_id': 'user_1', 'name': 'Personal Account', 'type': 'checking', 'balance': 5000},
                {'id': 'acc_2', 'user_id': 'user_1', 'name': 'Business Account', 'type': 'business', 'balance': 15000},
                {'id': 'acc_3', 'user_id': 'user_2', 'name': 'Savings Account', 'type': 'savings', 'balance': 25000}
            ],
            
            # Email System
            'mails': [
                {'id': 'mail_1', 'account_id': 'acc_1', 'subject': 'Welcome Email', 'from': 'system@bank.com', 'read': False},
                {'id': 'mail_2', 'account_id': 'acc_1', 'subject': 'Account Statement', 'from': 'statements@bank.com', 'read': True},
                {'id': 'mail_3', 'account_id': 'acc_2', 'subject': 'Business Update', 'from': 'business@bank.com', 'read': False}
            ],
            
            # E-commerce
            'products': [
                {'id': 'prod_1', 'name': 'Laptop', 'category_id': 'cat_1', 'price': 999.99, 'stock': 10},
                {'id': 'prod_2', 'name': 'Mouse', 'category_id': 'cat_1', 'price': 29.99, 'stock': 50},
                {'id': 'prod_3', 'name': 'Keyboard', 'category_id': 'cat_1', 'price': 79.99, 'stock': 25}
            ],
            
            'categories': [
                {'id': 'cat_1', 'name': 'Electronics', 'parent_id': None},
                {'id': 'cat_2', 'name': 'Computers', 'parent_id': 'cat_1'},
                {'id': 'cat_3', 'name': 'Accessories', 'parent_id': 'cat_1'}
            ],
            
            'orders': [
                {'id': 'order_1', 'user_id': 'user_1', 'product_id': 'prod_1', 'quantity': 1, 'status': 'pending'},
                {'id': 'order_2', 'user_id': 'user_1', 'product_id': 'prod_2', 'quantity': 2, 'status': 'shipped'},
                {'id': 'order_3', 'user_id': 'user_2', 'product_id': 'prod_3', 'quantity': 1, 'status': 'delivered'}
            ],
            
            # Project Management
            'projects': [
                {'id': 'proj_1', 'name': 'Website Redesign', 'owner_id': 'user_1', 'status': 'active'},
                {'id': 'proj_2', 'name': 'Mobile App', 'owner_id': 'user_2', 'status': 'planning'}
            ],
            
            'tasks': [
                {'id': 'task_1', 'project_id': 'proj_1', 'title': 'Design Homepage', 'assignee_id': 'user_2', 'status': 'in_progress'},
                {'id': 'task_2', 'project_id': 'proj_1', 'title': 'Implement Backend', 'assignee_id': 'user_3', 'status': 'pending'},
                {'id': 'task_3', 'project_id': 'proj_2', 'title': 'Create Wireframes', 'assignee_id': 'user_1', 'status': 'completed'}
            ]
        }
    
    def load_openapi_spec(self, spec: Dict[str, Any]):
        """Load OpenAPI spec and analyze dependencies"""
        logger.info("🔍 Analyzing OpenAPI spec for generic dependencies...")
        self.dependencies = self.dependency_analyzer.analyze_openapi_spec(spec)
        self.endpoint_map = self.dependency_analyzer.endpoint_map
        logger.info(f"✅ Found {len(self.dependencies)} operations with dependencies")
        
        # Register all tools
        self._register_all_tools(spec)
    
    def _register_all_tools(self, spec: Dict[str, Any]):
        """Register all tools with dependency awareness"""
        
        # Register generic tools based on the spec
        for operation_id, endpoint_info in self.endpoint_map.items():
            self._register_generic_tool(operation_id, endpoint_info)
    
    def _register_generic_tool(self, operation_id: str, endpoint_info: Dict):
        """Register a generic tool with dependency awareness"""
        
        path = endpoint_info['path']
        method = endpoint_info['method']
        operation = endpoint_info['operation']
        
        # Get dependencies for this operation
        deps = self.dependencies.get(operation_id, [])
        
        # Create tool function
        async def generic_tool(**kwargs):
            return await self._execute_generic_operation(operation_id, deps, kwargs)
        
        # Build description with dependency information
        description = self._build_tool_description(operation, deps, path, method)
        
        # Register with FastMCP
        app.tool(name=operation_id, description=description)(generic_tool)
    
    def _build_tool_description(self, operation: Dict, deps: List[Dict], path: str, method: str) -> str:
        """Build comprehensive tool description with dependency info"""
        
        summary = operation.get('summary', f"{method.upper()} {path}")
        description = operation.get('description', '')
        
        desc_parts = [f"{summary}"]
        
        if description:
            desc_parts.append(f"\nDescription: {description}")
        
        if deps:
            desc_parts.append("\nDEPENDENCIES:")
            for dep in deps:
                desc_parts.append(f"- {dep['description']}")
                desc_parts.append(f"  Source: {dep['source_endpoint']}")
        
        # Add generic usage guidance
        desc_parts.append("\nUSAGE:")
        desc_parts.append("- If required parameters are missing, this tool will guide you to get them first")
        desc_parts.append("- Check the response for prerequisite information")
        desc_parts.append("- Use suggested workflows to resolve dependencies")
        
        return "\n".join(desc_parts)
    
    async def _execute_generic_operation(self, operation_id: str, deps: List[Dict], kwargs: Dict) -> str:
        """Execute any operation with dependency awareness"""
        
        logger.info(f"📞 Executing {operation_id} with args: {list(kwargs.keys())}")
        
        # Check dependencies
        missing_deps = self._check_dependencies(deps, kwargs)
        
        if missing_deps:
            return json.dumps({
                "status": "prerequisites_required",
                "message": f"Operation {operation_id} requires prerequisites",
                "missing_prerequisites": missing_deps,
                "suggested_workflow": self._build_suggested_workflow(missing_deps),
                "available_data": self._get_available_data_for_context()
            }, indent=2)
        
        # Execute the operation
        result = await self._execute_operation_logic(operation_id, kwargs)
        return json.dumps(result, indent=2)
    
    def _check_dependencies(self, deps: List[Dict], kwargs: Dict) -> List[Dict]:
        """Check if dependencies are satisfied"""
        missing = []
        
        for dep in deps:
            param = dep['parameter']
            if param not in kwargs or kwargs[param] is None:
                missing.append(dep)
        
        return missing
    
    def _build_suggested_workflow(self, missing_deps: List[Dict]) -> List[str]:
        """Build suggested workflow for missing dependencies"""
        workflow = []
        
        for dep in missing_deps:
            source_endpoint = dep['source_endpoint']
            param = dep['parameter']
            
            workflow.append(f"1. Call {source_endpoint}() to get {param}")
            workflow.append(f"2. Use the {param} from the result")
            workflow.append(f"3. Call this operation with {param} parameter")
        
        return workflow
    
    def _get_available_data_for_context(self) -> Dict[str, Any]:
        """Get available data for context"""
        return {
            "users": [{"id": u["id"], "name": u["name"]} for u in self.mock_data["users"]],
            "accounts": [{"id": a["id"], "name": a["name"], "user_id": a["user_id"]} for a in self.mock_data["accounts"]],
            "products": [{"id": p["id"], "name": p["name"], "category_id": p["category_id"]} for p in self.mock_data["products"]],
            "categories": [{"id": c["id"], "name": c["name"]} for c in self.mock_data["categories"]],
            "projects": [{"id": p["id"], "name": p["name"], "owner_id": p["owner_id"]} for p in self.mock_data["projects"]]
        }
    
    async def _execute_operation_logic(self, operation_id: str, kwargs: Dict) -> Dict[str, Any]:
        """Execute the actual operation logic"""
        
        # Generic operation routing based on operation_id patterns
        if operation_id.startswith('get') or operation_id.startswith('list'):
            return await self._handle_get_operation(operation_id, kwargs)
        elif operation_id.startswith('create') or operation_id.startswith('add'):
            return await self._handle_create_operation(operation_id, kwargs)
        elif operation_id.startswith('update') or operation_id.startswith('modify'):
            return await self._handle_update_operation(operation_id, kwargs)
        elif operation_id.startswith('delete') or operation_id.startswith('remove'):
            return await self._handle_delete_operation(operation_id, kwargs)
        else:
            return {
                "status": "success",
                "message": f"Operation {operation_id} executed",
                "parameters": kwargs,
                "note": "Generic operation handler - implement specific logic as needed"
            }
    
    async def _handle_get_operation(self, operation_id: str, kwargs: Dict) -> Dict[str, Any]:
        """Handle GET operations generically"""
        
        # Determine data type from operation_id
        data_type = self._extract_data_type_from_operation(operation_id)
        
        if data_type in self.mock_data:
            data = self.mock_data[data_type]
            
            # Apply filters
            filtered_data = self._apply_filters(data, kwargs)
            
            return {
                "status": "success",
                "data": filtered_data,
                "message": f"Found {len(filtered_data)} {data_type}",
                "operation": operation_id,
                "filters_applied": list(kwargs.keys())
            }
        
        return {
            "status": "error",
            "message": f"Unknown data type for operation {operation_id}"
        }
    
    def _extract_data_type_from_operation(self, operation_id: str) -> str:
        """Extract data type from operation ID"""
        # Remove common prefixes
        data_type = re.sub(r'^(get|list|find|search)', '', operation_id, flags=re.IGNORECASE)
        
        # Convert to plural if needed
        if not data_type.endswith('s'):
            data_type += 's'
        
        # Map to mock data keys
        type_mapping = {
            'users': 'users',
            'accountss': 'accounts',
            'mailss': 'mails',
            'productss': 'products',
            'categoriess': 'categories',
            'orderss': 'orders',
            'projectss': 'projects',
            'taskss': 'tasks'
        }
        
        return type_mapping.get(data_type, data_type)
    
    def _apply_filters(self, data: List[Dict], filters: Dict) -> List[Dict]:
        """Apply filters to data"""
        filtered = data
        
        for key, value in filters.items():
            if value is not None:
                filtered = [item for item in filtered if item.get(key) == value]
        
        return filtered
    
    async def _handle_create_operation(self, operation_id: str, kwargs: Dict) -> Dict[str, Any]:
        """Handle CREATE operations"""
        return {
            "status": "success",
            "message": f"Created new resource via {operation_id}",
            "data": kwargs,
            "note": "Mock create operation - implement actual creation logic"
        }
    
    async def _handle_update_operation(self, operation_id: str, kwargs: Dict) -> Dict[str, Any]:
        """Handle UPDATE operations"""
        return {
            "status": "success",
            "message": f"Updated resource via {operation_id}",
            "data": kwargs,
            "note": "Mock update operation - implement actual update logic"
        }
    
    async def _handle_delete_operation(self, operation_id: str, kwargs: Dict) -> Dict[str, Any]:
        """Handle DELETE operations"""
        return {
            "status": "success",
            "message": f"Deleted resource via {operation_id}",
            "data": kwargs,
            "note": "Mock delete operation - implement actual deletion logic"
        }

def main():
    """Main entry point"""
    logger.info("🚀 Starting Generic Dependency-Aware MCP Server...")
    
    # Create server
    server = GenericDependencyMCPServer()
    
    # Load a comprehensive OpenAPI spec
    comprehensive_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Comprehensive API", "version": "1.0.0"},
        "paths": {
            # User Management
            "/users": {
                "get": {
                    "operationId": "getUsers",
                    "summary": "Get all users"
                }
            },
            "/users/{user_id}": {
                "get": {
                    "operationId": "getUserById",
                    "summary": "Get user by ID",
                    "parameters": [
                        {"name": "user_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            },
            
            # Account Management
            "/accounts": {
                "get": {
                    "operationId": "getAccounts",
                    "summary": "Get accounts",
                    "parameters": [
                        {"name": "user_id", "in": "query", "schema": {"type": "string"}}
                    ]
                }
            },
            "/accounts/{account_id}": {
                "get": {
                    "operationId": "getAccountById",
                    "summary": "Get account by ID",
                    "parameters": [
                        {"name": "account_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            },
            
            # Email System
            "/accounts/{account_id}/mails": {
                "get": {
                    "operationId": "getMails",
                    "summary": "Get emails for account",
                    "parameters": [
                        {"name": "account_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            },
            
            # E-commerce
            "/products": {
                "get": {
                    "operationId": "getProducts",
                    "summary": "Get all products",
                    "parameters": [
                        {"name": "category_id", "in": "query", "schema": {"type": "string"}}
                    ]
                }
            },
            "/products/{product_id}": {
                "get": {
                    "operationId": "getProductById",
                    "summary": "Get product by ID",
                    "parameters": [
                        {"name": "product_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            },
            "/categories": {
                "get": {
                    "operationId": "getCategories",
                    "summary": "Get all categories"
                }
            },
            "/categories/{category_id}/products": {
                "get": {
                    "operationId": "getProductsByCategory",
                    "summary": "Get products by category",
                    "parameters": [
                        {"name": "category_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            },
            "/users/{user_id}/orders": {
                "get": {
                    "operationId": "getUserOrders",
                    "summary": "Get orders for user",
                    "parameters": [
                        {"name": "user_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            },
            "/orders/{order_id}": {
                "get": {
                    "operationId": "getOrderById",
                    "summary": "Get order by ID",
                    "parameters": [
                        {"name": "order_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            },
            
            # Project Management
            "/projects": {
                "get": {
                    "operationId": "getProjects",
                    "summary": "Get all projects",
                    "parameters": [
                        {"name": "owner_id", "in": "query", "schema": {"type": "string"}}
                    ]
                }
            },
            "/projects/{project_id}": {
                "get": {
                    "operationId": "getProjectById",
                    "summary": "Get project by ID",
                    "parameters": [
                        {"name": "project_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            },
            "/projects/{project_id}/tasks": {
                "get": {
                    "operationId": "getProjectTasks",
                    "summary": "Get tasks for project",
                    "parameters": [
                        {"name": "project_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            },
            "/tasks/{task_id}": {
                "get": {
                    "operationId": "getTaskById",
                    "summary": "Get task by ID",
                    "parameters": [
                        {"name": "task_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ]
                }
            }
        }
    }
    
    # Load spec and analyze dependencies
    server.load_openapi_spec(comprehensive_spec)
    
    # Start the server
    logger.info("🌐 Starting Generic MCP server with stdio transport...")
    app.run(transport="stdio")

if __name__ == "__main__":
    main()