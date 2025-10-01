"""
Use Case Manager for Demo MCP System
Manages use cases with documentation and flowcharts
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UseCaseManager:
    """Manages use cases with documentation and flowcharts"""
    
    def __init__(self):
        self.use_cases: Dict[str, Dict[str, Any]] = {}
        self.documentation: Dict[str, str] = {}
        self.flowcharts: Dict[str, str] = {}
        self._generate_demo_use_cases()
    
    def _generate_demo_use_cases(self) -> None:
        """Generate demo use cases"""
        demo_cases = [
            {
                "id": "1",
                "name": "User Authentication Flow",
                "description": "Complete user authentication with login, verification, and session management",
                "tools": ["login", "verify_token", "get_user_profile"],
                "business_value": "High - Core security functionality",
                "complexity": "Medium",
                "estimated_time": "2-3 minutes",
                "category": "Authentication",
                "keywords": ["login", "auth", "security", "session"]
            },
            {
                "id": "2", 
                "name": "Account Balance Inquiry",
                "description": "Retrieve account balance and recent transaction history",
                "tools": ["get_account_balance", "get_transactions", "format_balance_report"],
                "business_value": "High - Core banking functionality",
                "complexity": "Low",
                "estimated_time": "1-2 minutes",
                "category": "Banking",
                "keywords": ["balance", "account", "transactions", "banking"]
            },
            {
                "id": "3",
                "name": "Payment Processing",
                "description": "Process payment with validation, fraud check, and confirmation",
                "tools": ["validate_payment", "fraud_check", "process_payment", "send_confirmation"],
                "business_value": "Critical - Revenue generation",
                "complexity": "High",
                "estimated_time": "3-5 minutes",
                "category": "Payment",
                "keywords": ["payment", "transfer", "money", "transaction"]
            },
            {
                "id": "4",
                "name": "Portfolio Analysis",
                "description": "Analyze investment portfolio performance and generate insights",
                "tools": ["get_portfolio", "calculate_performance", "generate_insights", "create_report"],
                "business_value": "Medium - Customer insights",
                "complexity": "High",
                "estimated_time": "5-7 minutes",
                "category": "Investment",
                "keywords": ["portfolio", "investment", "analysis", "performance"]
            },
            {
                "id": "5",
                "name": "Risk Assessment",
                "description": "Comprehensive risk analysis for investment decisions",
                "tools": ["get_market_data", "calculate_risk_metrics", "generate_risk_report"],
                "business_value": "High - Risk management",
                "complexity": "Medium",
                "estimated_time": "3-4 minutes",
                "category": "Risk Management",
                "keywords": ["risk", "assessment", "analysis", "metrics"]
            },
            {
                "id": "6",
                "name": "Customer Support Ticket",
                "description": "Create and manage customer support tickets with automated routing",
                "tools": ["create_ticket", "assign_priority", "route_ticket", "send_notification"],
                "business_value": "Medium - Customer service",
                "complexity": "Low",
                "estimated_time": "1-2 minutes",
                "category": "Support",
                "keywords": ["support", "ticket", "customer", "help"]
            }
        ]
        
        for case in demo_cases:
            self.use_cases[case["id"]] = case
            self.documentation[case["id"]] = self._generate_documentation(case)
            self.flowcharts[case["id"]] = self._generate_flowchart(case)
        
        logger.info(f"Generated {len(demo_cases)} demo use cases")
    
    def _generate_documentation(self, use_case: Dict[str, Any]) -> str:
        """Generate documentation for use case"""
        return f"""
# {use_case['name']}

## Overview
{use_case['description']}

## Business Value
{use_case['business_value']}

## Complexity
{use_case['complexity']} - Estimated time: {use_case['estimated_time']}

## Category
{use_case['category']}

## Required Tools
{', '.join(use_case['tools'])}

## Keywords
{', '.join(use_case['keywords'])}

## Execution Steps
1. **Initialize**: Set up parameters and validate inputs
2. **Execute Tools**: Run tools in sequence: {', '.join(use_case['tools'])}
3. **Validate Results**: Check each tool's output
4. **Aggregate Data**: Combine results into final output
5. **Generate Report**: Create comprehensive report

## Error Handling
- **Tool Failures**: Retry with exponential backoff
- **Validation Errors**: Return clear error messages
- **Timeout**: Implement 30-second timeout per tool

## Performance Considerations
- **Caching**: Results cached for 1 hour
- **Parallel Execution**: Tools 2 and 3 can run in parallel
- **Rate Limiting**: Respect API rate limits

## Example Parameters
```json
{{
    "user_id": "12345",
    "account_id": "ACC-001",
    "amount": 100.00,
    "currency": "USD"
}}
```

## Expected Output
```json
{{
    "success": true,
    "result": "Use case executed successfully",
    "execution_time": "2.5 seconds",
    "tools_executed": {len(use_case['tools'])},
    "data": {{}}
}}
```

## Dependencies
- Authentication required for all operations
- Valid user session for user-specific operations
- Sufficient permissions for administrative operations

## Monitoring
- Execution time tracking
- Success/failure rates
- Resource usage monitoring
- Performance metrics collection
"""
    
    def _generate_flowchart(self, use_case: Dict[str, Any]) -> str:
        """Generate Mermaid flowchart for use case"""
        tools = use_case['tools']
        flowchart = f"""
graph TD
    A[Start: {use_case['name']}] --> B[Initialize Parameters]
    B --> C[Validate Inputs]
    C --> D[Execute Tools]
    
    D --> E[{tools[0] if len(tools) > 0 else 'Tool 1'}]
    E --> F[{tools[1] if len(tools) > 1 else 'Tool 2'}]
    F --> G[{tools[2] if len(tools) > 2 else 'Tool 3'}]
    
    {f"G --> H[{tools[3] if len(tools) > 3 else 'Tool 4'}]" if len(tools) > 3 else ""}
    
    G --> I[Validate Results]
    {f"H --> I" if len(tools) > 3 else ""}
    
    I --> J[Generate Report]
    J --> K[Cache Results]
    K --> L[Return Success]
    
    C --> M[Input Validation Failed]
    M --> N[Return Error]
    
    E --> O[Tool Execution Failed]
    F --> O
    G --> O
    {f"H --> O" if len(tools) > 3 else ""}
    
    O --> P[Retry with Backoff]
    P --> Q[Max Retries Reached]
    Q --> R[Return Error]
    
    style A fill:#e1f5fe
    style L fill:#c8e6c9
    style N fill:#ffcdd2
    style R fill:#ffcdd2
"""
        return flowchart
    
    def get_all_use_cases(self) -> List[Dict[str, Any]]:
        """Get all use cases"""
        return list(self.use_cases.values())
    
    def get_use_case(self, use_case_id: str) -> Optional[Dict[str, Any]]:
        """Get specific use case"""
        return self.use_cases.get(use_case_id)
    
    def get_use_cases_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get use cases by category"""
        return [case for case in self.use_cases.values() if case["category"] == category]
    
    def get_use_cases_by_complexity(self, complexity: str) -> List[Dict[str, Any]]:
        """Get use cases by complexity"""
        return [case for case in self.use_cases.values() if case["complexity"] == complexity]
    
    def search_use_cases(self, query: str) -> List[Dict[str, Any]]:
        """Search use cases by keywords"""
        query_lower = query.lower()
        results = []
        
        for case in self.use_cases.values():
            # Search in name, description, and keywords
            if (query_lower in case["name"].lower() or 
                query_lower in case["description"].lower() or
                any(query_lower in keyword.lower() for keyword in case["keywords"])):
                results.append(case)
        
        return results
    
    def get_documentation(self, use_case_id: str) -> str:
        """Get documentation for use case"""
        return self.documentation.get(use_case_id, "Documentation not found")
    
    def get_flowchart(self, use_case_id: str) -> str:
        """Get flowchart for use case"""
        return self.flowcharts.get(use_case_id, "Flowchart not found")
    
    async def execute_use_case(self, use_case_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute use case with parameters"""
        use_case = self.get_use_case(use_case_id)
        if not use_case:
            return {"error": "Use case not found"}
        
        # Check cache first (if cache manager is available)
        try:
            from .cache_manager import CacheManager
            cache_manager = CacheManager()
            cached_result = cache_manager.get_use_case_cache(use_case_id, parameters)
            if cached_result:
                return {"result": cached_result, "source": "cache"}
        except ImportError:
            pass
        
        # Simulate execution
        start_time = datetime.now()
        
        # Simulate tool execution
        execution_results = []
        for i, tool in enumerate(use_case['tools']):
            # Simulate tool execution time
            import time
            time.sleep(0.1)  # Simulate processing time
            
            execution_results.append({
                "tool": tool,
                "success": True,
                "execution_time": "0.1s",
                "result": f"Tool '{tool}' executed successfully"
            })
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        execution_result = {
            "use_case": use_case['name'],
            "use_case_id": use_case_id,
            "tools_executed": use_case['tools'],
            "parameters": parameters,
            "success": True,
            "execution_time": f"{execution_time:.2f} seconds",
            "tool_results": execution_results,
            "result": f"Successfully executed {use_case['name']} with parameters: {parameters}",
            "timestamp": datetime.now().isoformat()
        }
        
        # Cache result (if cache manager is available)
        try:
            cache_manager.set_use_case_cache(use_case_id, parameters, execution_result)
        except:
            pass
        
        logger.info(f"Use case {use_case_id} executed successfully")
        return execution_result
    
    def get_categories(self) -> List[str]:
        """Get all available categories"""
        return list(set(case["category"] for case in self.use_cases.values()))
    
    def get_complexity_levels(self) -> List[str]:
        """Get all available complexity levels"""
        return list(set(case["complexity"] for case in self.use_cases.values()))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get use case statistics"""
        categories = {}
        complexity_levels = {}
        
        for case in self.use_cases.values():
            # Count by category
            category = case["category"]
            categories[category] = categories.get(category, 0) + 1
            
            # Count by complexity
            complexity = case["complexity"]
            complexity_levels[complexity] = complexity_levels.get(complexity, 0) + 1
        
        return {
            "total_use_cases": len(self.use_cases),
            "categories": categories,
            "complexity_levels": complexity_levels,
            "average_tools_per_case": sum(len(case["tools"]) for case in self.use_cases.values()) / len(self.use_cases)
        }
