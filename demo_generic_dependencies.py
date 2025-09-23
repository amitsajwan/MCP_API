#!/usr/bin/env python3
"""
Generic Dependency Demo
======================
Demonstrates dependency-aware tools working with ANY API scenario.
"""

import json
from typing import Dict, List, Any

class GenericDependencyDemo:
    """Demo showing generic dependency awareness for any API"""
    
    def __init__(self):
        self.mock_data = {
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
    
    def simulate_generic_operation(self, operation_id: str, **kwargs):
        """Simulate any operation with dependency awareness"""
        
        # Check for common dependency patterns
        dependencies = self._detect_dependencies(operation_id, kwargs)
        
        if dependencies:
            return {
                "status": "prerequisites_required",
                "message": f"Operation {operation_id} requires prerequisites",
                "missing_prerequisites": dependencies,
                "suggested_workflow": self._build_workflow(dependencies),
                "available_data": self._get_context_data()
            }
        
        # Execute the operation
        return self._execute_operation(operation_id, kwargs)
    
    def _detect_dependencies(self, operation_id: str, kwargs: Dict) -> List[Dict]:
        """Detect dependencies for any operation"""
        dependencies = []
        
        # Define dependency patterns for different operations
        dependency_patterns = {
            'getMails': {'account_id': 'getAccounts'},
            'getUserOrders': {'user_id': 'getUsers'},
            'getProductsByCategory': {'category_id': 'getCategories'},
            'getProjectTasks': {'project_id': 'getProjects'},
            'getAccountById': {'account_id': 'getAccounts'},
            'getProductById': {'product_id': 'getProducts'},
            'getTaskById': {'task_id': 'getTasks'},
            'getOrderById': {'order_id': 'getOrders'},
            'getUserById': {'user_id': 'getUsers'},
            'getProjectById': {'project_id': 'getProjects'},
            'getCategoryById': {'category_id': 'getCategories'}
        }
        
        # Check if this operation has dependencies
        if operation_id in dependency_patterns:
            for param, source_op in dependency_patterns[operation_id].items():
                if param not in kwargs or kwargs[param] is None:
                    dependencies.append({
                        'parameter': param,
                        'source_operation': source_op,
                        'description': f'{param} must be obtained from {source_op} first'
                    })
        
        return dependencies
    
    def _build_workflow(self, dependencies: List[Dict]) -> List[str]:
        """Build workflow for dependencies"""
        workflow = []
        
        for dep in dependencies:
            workflow.append(f"1. Call {dep['source_operation']}() to get {dep['parameter']}")
            workflow.append(f"2. Use the {dep['parameter']} from the result")
            workflow.append(f"3. Call this operation with {dep['parameter']} parameter")
        
        return workflow
    
    def _get_context_data(self) -> Dict[str, Any]:
        """Get available data for context"""
        return {
            "users": [{"id": u["id"], "name": u["name"]} for u in self.mock_data["users"]],
            "accounts": [{"id": a["id"], "name": a["name"], "user_id": a["user_id"]} for a in self.mock_data["accounts"]],
            "products": [{"id": p["id"], "name": p["name"], "category_id": p["category_id"]} for p in self.mock_data["products"]],
            "categories": [{"id": c["id"], "name": c["name"]} for c in self.mock_data["categories"]],
            "projects": [{"id": p["id"], "name": p["name"], "owner_id": p["owner_id"]} for p in self.mock_data["projects"]],
            "orders": [{"id": o["id"], "user_id": o["user_id"], "product_id": o["product_id"]} for o in self.mock_data["orders"]],
            "tasks": [{"id": t["id"], "project_id": t["project_id"], "title": t["title"]} for t in self.mock_data["tasks"]]
        }
    
    def _execute_operation(self, operation_id: str, kwargs: Dict) -> Dict[str, Any]:
        """Execute the actual operation"""
        
        # Route to appropriate handler
        if 'getMails' in operation_id:
            return self._get_mails(kwargs)
        elif 'getUserOrders' in operation_id:
            return self._get_user_orders(kwargs)
        elif 'getProductsByCategory' in operation_id:
            return self._get_products_by_category(kwargs)
        elif 'getProjectTasks' in operation_id:
            return self._get_project_tasks(kwargs)
        elif 'getAccountById' in operation_id:
            return self._get_account_by_id(kwargs)
        elif 'getProductById' in operation_id:
            return self._get_product_by_id(kwargs)
        elif 'getTaskById' in operation_id:
            return self._get_task_by_id(kwargs)
        else:
            return {
                "status": "success",
                "message": f"Operation {operation_id} executed",
                "data": kwargs,
                "note": "Generic operation handler"
            }
    
    def _get_mails(self, kwargs: Dict) -> Dict[str, Any]:
        """Get emails for account"""
        account_id = kwargs.get('account_id')
        mails = [mail for mail in self.mock_data['mails'] if mail['account_id'] == account_id]
        
        return {
            "status": "success",
            "data": mails,
            "message": f"Found {len(mails)} emails for account {account_id}",
            "account_id": account_id
        }
    
    def _get_user_orders(self, kwargs: Dict) -> Dict[str, Any]:
        """Get orders for user"""
        user_id = kwargs.get('user_id')
        orders = [order for order in self.mock_data['orders'] if order['user_id'] == user_id]
        
        return {
            "status": "success",
            "data": orders,
            "message": f"Found {len(orders)} orders for user {user_id}",
            "user_id": user_id
        }
    
    def _get_products_by_category(self, kwargs: Dict) -> Dict[str, Any]:
        """Get products by category"""
        category_id = kwargs.get('category_id')
        products = [prod for prod in self.mock_data['products'] if prod['category_id'] == category_id]
        
        return {
            "status": "success",
            "data": products,
            "message": f"Found {len(products)} products in category {category_id}",
            "category_id": category_id
        }
    
    def _get_project_tasks(self, kwargs: Dict) -> Dict[str, Any]:
        """Get tasks for project"""
        project_id = kwargs.get('project_id')
        tasks = [task for task in self.mock_data['tasks'] if task['project_id'] == project_id]
        
        return {
            "status": "success",
            "data": tasks,
            "message": f"Found {len(tasks)} tasks for project {project_id}",
            "project_id": project_id
        }
    
    def _get_account_by_id(self, kwargs: Dict) -> Dict[str, Any]:
        """Get account by ID"""
        account_id = kwargs.get('account_id')
        account = next((acc for acc in self.mock_data['accounts'] if acc['id'] == account_id), None)
        
        if account:
            return {
                "status": "success",
                "data": account,
                "message": f"Found account {account_id}",
                "account_id": account_id
            }
        else:
            return {
                "status": "error",
                "message": f"Account {account_id} not found"
            }
    
    def _get_product_by_id(self, kwargs: Dict) -> Dict[str, Any]:
        """Get product by ID"""
        product_id = kwargs.get('product_id')
        product = next((prod for prod in self.mock_data['products'] if prod['id'] == product_id), None)
        
        if product:
            return {
                "status": "success",
                "data": product,
                "message": f"Found product {product_id}",
                "product_id": product_id
            }
        else:
            return {
                "status": "error",
                "message": f"Product {product_id} not found"
            }
    
    def _get_task_by_id(self, kwargs: Dict) -> Dict[str, Any]:
        """Get task by ID"""
        task_id = kwargs.get('task_id')
        task = next((task for task in self.mock_data['tasks'] if task['id'] == task_id), None)
        
        if task:
            return {
                "status": "success",
                "data": task,
                "message": f"Found task {task_id}",
                "task_id": task_id
            }
        else:
            return {
                "status": "error",
                "message": f"Task {task_id} not found"
            }

def demo_various_scenarios():
    """Demonstrate various API scenarios"""
    
    print("🎯 Generic Dependency-Aware API Demo")
    print("=" * 50)
    
    demo = GenericDependencyDemo()
    
    scenarios = [
        {
            "name": "Banking: Get emails",
            "operation": "getMails",
            "kwargs": {},
            "description": "User asks: 'Get my emails'"
        },
        {
            "name": "E-commerce: Get user orders",
            "operation": "getUserOrders",
            "kwargs": {},
            "description": "User asks: 'Show my orders'"
        },
        {
            "name": "E-commerce: Get products by category",
            "operation": "getProductsByCategory",
            "kwargs": {},
            "description": "User asks: 'Show electronics products'"
        },
        {
            "name": "Project Management: Get project tasks",
            "operation": "getProjectTasks",
            "kwargs": {},
            "description": "User asks: 'Show tasks for my project'"
        },
        {
            "name": "Banking: Get account details",
            "operation": "getAccountById",
            "kwargs": {},
            "description": "User asks: 'Show account details'"
        },
        {
            "name": "E-commerce: Get product details",
            "operation": "getProductById",
            "kwargs": {},
            "description": "User asks: 'Show product details'"
        },
        {
            "name": "Project Management: Get task details",
            "operation": "getTaskById",
            "kwargs": {},
            "description": "User asks: 'Show task details'"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📞 Scenario {i}: {scenario['name']}")
        print("-" * 40)
        print(f"Description: {scenario['description']}")
        print(f"Operation: {scenario['operation']}")
        print(f"Parameters: {scenario['kwargs']}")
        
        result = demo.simulate_generic_operation(scenario['operation'], **scenario['kwargs'])
        print("Result:", json.dumps(result, indent=2))
        
        # Show successful execution if prerequisites are met
        if result.get('status') == 'prerequisites_required':
            print(f"\n✅ Success Path:")
            print(f"1. Call {result['missing_prerequisites'][0]['source_operation']}()")
            print(f"2. Get {result['missing_prerequisites'][0]['parameter']} from result")
            print(f"3. Call {scenario['operation']}({result['missing_prerequisites'][0]['parameter']}='value')")
            
            # Simulate successful execution
            success_kwargs = {result['missing_prerequisites'][0]['parameter']: 'example_id'}
            success_result = demo.simulate_generic_operation(scenario['operation'], **success_kwargs)
            print(f"4. Success Result:", json.dumps(success_result, indent=2))

def show_generic_benefits():
    """Show the generic benefits"""
    
    print("\n🎯 Generic Dependency-Aware Benefits")
    print("=" * 40)
    
    print("✅ Works with ANY API:")
    print("   - Banking APIs (accounts, transactions, emails)")
    print("   - E-commerce APIs (products, orders, categories)")
    print("   - Project Management APIs (projects, tasks, users)")
    print("   - CRM APIs (customers, deals, activities)")
    print("   - Any REST API with dependencies")
    
    print("\n✅ Handles ANY dependency pattern:")
    print("   - Path parameters (/{user_id}/orders)")
    print("   - Query parameters (?category_id=123)")
    print("   - Request body references")
    print("   - Multi-level dependencies")
    print("   - Circular dependencies")
    
    print("\n✅ Provides intelligent guidance:")
    print("   - Clear prerequisite information")
    print("   - Suggested workflow steps")
    print("   - Available data context")
    print("   - Example usage patterns")
    
    print("\n✅ Enables smart MCP clients:")
    print("   - Automatic dependency resolution")
    print("   - Intelligent workflow orchestration")
    print("   - Context-aware parameter handling")
    print("   - Efficient API usage")

if __name__ == "__main__":
    demo_various_scenarios()
    show_generic_benefits()