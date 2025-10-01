"""
MCP Tools Manager for Demo MCP System
Manages MCP tools and execution
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPToolsManager:
    """Manages MCP tools and execution"""
    
    def __init__(self):
        self.tools: List[Dict[str, Any]] = []
        self.tool_categories: Dict[str, List[str]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self._generate_demo_tools()
    
    def _generate_demo_tools(self) -> None:
        """Generate demo MCP tools"""
        demo_tools = [
            {
                "name": "login",
                "description": "Authenticate user with credentials",
                "parameters": {"username": "string", "password": "string"},
                "category": "Authentication",
                "required": True,
                "example": {"username": "user123", "password": "password123"}
            },
            {
                "name": "verify_token",
                "description": "Verify authentication token",
                "parameters": {"token": "string"},
                "category": "Authentication",
                "required": True,
                "example": {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
            },
            {
                "name": "get_user_profile",
                "description": "Retrieve user profile information",
                "parameters": {"user_id": "string"},
                "category": "Authentication",
                "required": True,
                "example": {"user_id": "12345"}
            },
            {
                "name": "get_account_balance",
                "description": "Retrieve account balance for user",
                "parameters": {"user_id": "string", "account_id": "string"},
                "category": "Account",
                "required": True,
                "example": {"user_id": "12345", "account_id": "ACC-001"}
            },
            {
                "name": "get_transactions",
                "description": "Retrieve transaction history",
                "parameters": {"account_id": "string", "limit": "number", "offset": "number"},
                "category": "Account",
                "required": False,
                "example": {"account_id": "ACC-001", "limit": 10, "offset": 0}
            },
            {
                "name": "format_balance_report",
                "description": "Format balance information into report",
                "parameters": {"balance_data": "object", "format": "string"},
                "category": "Account",
                "required": False,
                "example": {"balance_data": {"balance": 1000.00}, "format": "json"}
            },
            {
                "name": "validate_payment",
                "description": "Validate payment details",
                "parameters": {"payment_data": "object"},
                "category": "Payment",
                "required": True,
                "example": {"payment_data": {"amount": 100.00, "currency": "USD"}}
            },
            {
                "name": "fraud_check",
                "description": "Perform fraud detection check",
                "parameters": {"transaction_data": "object"},
                "category": "Payment",
                "required": True,
                "example": {"transaction_data": {"amount": 100.00, "recipient": "user456"}}
            },
            {
                "name": "process_payment",
                "description": "Process payment transaction",
                "parameters": {"amount": "number", "currency": "string", "recipient": "string"},
                "category": "Payment",
                "required": True,
                "example": {"amount": 100.00, "currency": "USD", "recipient": "user456"}
            },
            {
                "name": "send_confirmation",
                "description": "Send payment confirmation",
                "parameters": {"transaction_id": "string", "recipient_email": "string"},
                "category": "Payment",
                "required": False,
                "example": {"transaction_id": "TXN-123", "recipient_email": "user@example.com"}
            },
            {
                "name": "get_portfolio",
                "description": "Retrieve investment portfolio",
                "parameters": {"user_id": "string", "portfolio_id": "string"},
                "category": "Investment",
                "required": True,
                "example": {"user_id": "12345", "portfolio_id": "PORT-001"}
            },
            {
                "name": "calculate_performance",
                "description": "Calculate portfolio performance metrics",
                "parameters": {"portfolio_data": "object", "timeframe": "string"},
                "category": "Investment",
                "required": True,
                "example": {"portfolio_data": {"stocks": []}, "timeframe": "1Y"}
            },
            {
                "name": "generate_insights",
                "description": "Generate investment insights",
                "parameters": {"performance_data": "object"},
                "category": "Investment",
                "required": True,
                "example": {"performance_data": {"returns": 0.15}}
            },
            {
                "name": "create_report",
                "description": "Create investment report",
                "parameters": {"insights_data": "object", "format": "string"},
                "category": "Investment",
                "required": False,
                "example": {"insights_data": {"insights": []}, "format": "pdf"}
            },
            {
                "name": "get_market_data",
                "description": "Retrieve market data for analysis",
                "parameters": {"symbol": "string", "timeframe": "string"},
                "category": "Market Data",
                "required": True,
                "example": {"symbol": "AAPL", "timeframe": "1D"}
            },
            {
                "name": "calculate_risk_metrics",
                "description": "Calculate risk metrics for portfolio",
                "parameters": {"portfolio_data": "object"},
                "category": "Risk Analysis",
                "required": True,
                "example": {"portfolio_data": {"stocks": []}}
            },
            {
                "name": "generate_risk_report",
                "description": "Generate risk assessment report",
                "parameters": {"risk_data": "object", "format": "string"},
                "category": "Risk Analysis",
                "required": False,
                "example": {"risk_data": {"metrics": []}, "format": "json"}
            },
            {
                "name": "create_ticket",
                "description": "Create customer support ticket",
                "parameters": {"user_id": "string", "issue_description": "string", "priority": "string"},
                "category": "Support",
                "required": True,
                "example": {"user_id": "12345", "issue_description": "Login issue", "priority": "high"}
            },
            {
                "name": "assign_priority",
                "description": "Assign priority to support ticket",
                "parameters": {"ticket_id": "string", "priority": "string"},
                "category": "Support",
                "required": True,
                "example": {"ticket_id": "TICKET-123", "priority": "high"}
            },
            {
                "name": "route_ticket",
                "description": "Route ticket to appropriate department",
                "parameters": {"ticket_id": "string", "department": "string"},
                "category": "Support",
                "required": True,
                "example": {"ticket_id": "TICKET-123", "department": "technical"}
            },
            {
                "name": "send_notification",
                "description": "Send notification to user",
                "parameters": {"user_id": "string", "message": "string", "type": "string"},
                "category": "Support",
                "required": False,
                "example": {"user_id": "12345", "message": "Ticket created", "type": "email"}
            }
        ]
        
        self.tools = demo_tools
        
        # Organize tools by category
        for tool in self.tools:
            category = tool["category"]
            if category not in self.tool_categories:
                self.tool_categories[category] = []
            self.tool_categories[category].append(tool["name"])
        
        logger.info(f"Generated {len(demo_tools)} demo MCP tools")
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools"""
        return self.tools
    
    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get specific tool"""
        for tool in self.tools:
            if tool["name"] == tool_name:
                return tool
        return None
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tools by category"""
        return [tool for tool in self.tools if tool["category"] == category]
    
    def get_categories(self) -> List[str]:
        """Get all available categories"""
        return list(self.tool_categories.keys())
    
    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """Search tools by name or description"""
        query_lower = query.lower()
        results = []
        
        for tool in self.tools:
            if (query_lower in tool["name"].lower() or 
                query_lower in tool["description"].lower()):
                results.append(tool)
        
        return results
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool"""
        tool = self.get_tool(tool_name)
        if not tool:
            return {"error": "Tool not found"}
        
        # Validate parameters
        validation_result = self._validate_parameters(tool, parameters)
        if not validation_result["valid"]:
            return {"error": f"Parameter validation failed: {validation_result['errors']}"}
        
        # Record execution start
        start_time = datetime.now()
        
        try:
            # Simulate tool execution
            execution_result = await self._simulate_tool_execution(tool, parameters)
            
            # Record execution end
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Create result
            result = {
                "tool": tool_name,
                "parameters": parameters,
                "success": True,
                "result": execution_result,
                "execution_time": f"{execution_time:.2f} seconds",
                "timestamp": start_time.isoformat()
            }
            
            # Add to execution history
            self.execution_history.append(result)
            
            # Keep only last 100 executions
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
            
            logger.info(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {str(e)}")
            return {
                "tool": tool_name,
                "parameters": parameters,
                "success": False,
                "error": str(e),
                "execution_time": "0.00 seconds",
                "timestamp": start_time.isoformat()
            }
    
    def _validate_parameters(self, tool: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool parameters"""
        errors = []
        required_params = tool.get("required", True)
        
        if required_params:
            for param_name in tool["parameters"]:
                if param_name not in parameters:
                    errors.append(f"Missing required parameter: {param_name}")
        
        # Type validation (simplified)
        for param_name, param_value in parameters.items():
            if param_name in tool["parameters"]:
                expected_type = tool["parameters"][param_name]
                if expected_type == "string" and not isinstance(param_value, str):
                    errors.append(f"Parameter {param_name} should be string")
                elif expected_type == "number" and not isinstance(param_value, (int, float)):
                    errors.append(f"Parameter {param_name} should be number")
                elif expected_type == "object" and not isinstance(param_value, dict):
                    errors.append(f"Parameter {param_name} should be object")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _simulate_tool_execution(self, tool: Dict[str, Any], parameters: Dict[str, Any]) -> str:
        """Simulate tool execution"""
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Generate realistic response based on tool type
        tool_name = tool["name"]
        category = tool["category"]
        
        if category == "Authentication":
            if tool_name == "login":
                return f"User {parameters.get('username', 'unknown')} authenticated successfully"
            elif tool_name == "verify_token":
                return "Token verified successfully"
            elif tool_name == "get_user_profile":
                return f"User profile retrieved for user {parameters.get('user_id', 'unknown')}"
        
        elif category == "Account":
            if tool_name == "get_account_balance":
                return f"Account balance: $1,234.56 for account {parameters.get('account_id', 'unknown')}"
            elif tool_name == "get_transactions":
                return f"Retrieved {parameters.get('limit', 10)} transactions for account {parameters.get('account_id', 'unknown')}"
            elif tool_name == "format_balance_report":
                return "Balance report formatted successfully"
        
        elif category == "Payment":
            if tool_name == "validate_payment":
                return "Payment validation successful"
            elif tool_name == "fraud_check":
                return "Fraud check passed - transaction approved"
            elif tool_name == "process_payment":
                return f"Payment of ${parameters.get('amount', 0)} processed successfully"
            elif tool_name == "send_confirmation":
                return "Confirmation sent successfully"
        
        elif category == "Investment":
            if tool_name == "get_portfolio":
                return f"Portfolio retrieved for user {parameters.get('user_id', 'unknown')}"
            elif tool_name == "calculate_performance":
                return "Portfolio performance calculated: +15.2% return"
            elif tool_name == "generate_insights":
                return "Investment insights generated successfully"
            elif tool_name == "create_report":
                return "Investment report created successfully"
        
        elif category == "Risk Analysis":
            if tool_name == "get_market_data":
                return f"Market data retrieved for symbol {parameters.get('symbol', 'unknown')}"
            elif tool_name == "calculate_risk_metrics":
                return "Risk metrics calculated: Beta = 1.2, Sharpe Ratio = 0.85"
            elif tool_name == "generate_risk_report":
                return "Risk assessment report generated successfully"
        
        elif category == "Support":
            if tool_name == "create_ticket":
                return f"Support ticket created with ID: TICKET-{hash(str(parameters)) % 10000}"
            elif tool_name == "assign_priority":
                return f"Priority {parameters.get('priority', 'medium')} assigned to ticket"
            elif tool_name == "route_ticket":
                return f"Ticket routed to {parameters.get('department', 'general')} department"
            elif tool_name == "send_notification":
                return "Notification sent successfully"
        
        # Default response
        return f"Tool '{tool_name}' executed successfully with parameters: {parameters}"
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tool execution history"""
        return self.execution_history[-limit:]
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        if not self.execution_history:
            return {"total_executions": 0}
        
        # Count executions by tool
        tool_counts = {}
        success_count = 0
        total_execution_time = 0
        
        for execution in self.execution_history:
            tool_name = execution["tool"]
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            
            if execution["success"]:
                success_count += 1
            
            # Parse execution time
            try:
                exec_time = float(execution["execution_time"].split()[0])
                total_execution_time += exec_time
            except:
                pass
        
        return {
            "total_executions": len(self.execution_history),
            "successful_executions": success_count,
            "success_rate": success_count / len(self.execution_history) if self.execution_history else 0,
            "average_execution_time": total_execution_time / len(self.execution_history) if self.execution_history else 0,
            "tool_usage": tool_counts,
            "most_used_tool": max(tool_counts.items(), key=lambda x: x[1])[0] if tool_counts else None
        }
    
    def clear_execution_history(self) -> None:
        """Clear tool execution history"""
        self.execution_history.clear()
        logger.info("Tool execution history cleared")
