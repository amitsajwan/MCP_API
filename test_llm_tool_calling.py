#!/usr/bin/env python3
"""
Test LLM Tool Calling
Demonstrates how the LLM in chatbot_app.py calls tools based on user queries.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_llm_tool_calling")

class MockMCPClient:
    """Mock MCP client to demonstrate tool calling logic."""
    
    def __init__(self):
        self.available_tools = []
        self.connected = False
    
    async def connect(self):
        """Mock connection."""
        self.connected = True
        # Mock tools that would be available from MCP server
        self.available_tools = [
            {"name": "set_credentials", "description": "Set authentication credentials"},
            {"name": "perform_login", "description": "Perform login with stored credentials"},
            {"name": "cash_api_getPayments", "description": "Get payments from cash API"},
            {"name": "cash_api_getCashSummary", "description": "Get cash summary from cash API"},
            {"name": "securities_api_getPositions", "description": "Get securities positions"},
            {"name": "mailbox_api_getMessages", "description": "Get mailbox messages"},
        ]
        logger.info(f"Mock connected with {len(self.available_tools)} tools")
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process user query and determine which tools to call."""
        logger.info(f"Processing query: {user_query}")
        
        # This is the key logic from chatbot_app.py
        # It analyzes the user query and determines which tools to call
        
        # Check for authentication-related queries
        auth_keywords = ['login', 'authenticate', 'credential', 'password', 'username', 'connect', 'setup']
        is_auth_query = any(keyword in user_query.lower() for keyword in auth_keywords)
        
        # Check for payment-related queries
        payment_keywords = ['payment', 'pending', 'show', 'list', 'payments']
        is_payment_query = any(keyword in user_query.lower() for keyword in payment_keywords)
        
        # Check for summary/balance queries
        summary_keywords = ['summary', 'balance', 'overview', 'total', 'cash']
        is_summary_query = any(keyword in user_query.lower() for keyword in summary_keywords)
        
        # Check for securities queries
        securities_keywords = ['securities', 'positions', 'portfolio', 'stocks', 'bonds']
        is_securities_query = any(keyword in user_query.lower() for keyword in securities_keywords)
        
        # Check for mailbox queries
        mailbox_keywords = ['mailbox', 'messages', 'email', 'notifications']
        is_mailbox_query = any(keyword in user_query.lower() for keyword in mailbox_keywords)
        
        # Determine which tools to call based on query analysis
        tool_calls = []
        
        if is_auth_query:
            tool_calls.extend([
                {"tool_name": "set_credentials", "arguments": {}, "reason": "User asked about authentication"},
                {"tool_name": "perform_login", "arguments": {}, "reason": "User asked about login"}
            ])
        
        if is_payment_query:
            tool_calls.append({
                "tool_name": "cash_api_getPayments", 
                "arguments": {"status": "pending"}, 
                "reason": "User asked about payments"
            })
        
        if is_summary_query:
            tool_calls.append({
                "tool_name": "cash_api_getCashSummary", 
                "arguments": {"include_pending": True}, 
                "reason": "User asked for cash summary"
            })
        
        if is_securities_query:
            tool_calls.append({
                "tool_name": "securities_api_getPositions", 
                "arguments": {}, 
                "reason": "User asked about securities"
            })
        
        if is_mailbox_query:
            tool_calls.append({
                "tool_name": "mailbox_api_getMessages", 
                "arguments": {}, 
                "reason": "User asked about mailbox"
            })
        
        # If no specific tools identified, provide a general response
        if not tool_calls:
            return {
                "status": "ok",
                "plan": [],
                "results": [],
                "summary": "I understand your query, but I need more specific information to help you. Please specify what you'd like to do with payments, cash summary, securities, or authentication."
            }
        
        # Mock tool execution results
        results = []
        for tool_call in tool_calls:
            result = self._mock_execute_tool(tool_call)
            results.append(result)
        
        # Generate summary
        summary = self._generate_summary(user_query, results, tool_calls)
        
        return {
            "status": "ok",
            "plan": tool_calls,
            "results": results,
            "summary": summary
        }
    
    def _mock_execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Mock tool execution."""
        tool_name = tool_call["tool_name"]
        arguments = tool_call["arguments"]
        
        # Mock different responses based on tool type
        if tool_name == "set_credentials":
            return {
                "tool_name": tool_name,
                "success": True,
                "result": {"status": "success", "message": "Credentials stored successfully"},
                "execution_time": 0.1
            }
        elif tool_name == "perform_login":
            return {
                "tool_name": tool_name,
                "success": True,
                "result": {"status": "success", "message": "Login successful", "session_id": "mock_session_123"},
                "execution_time": 0.2
            }
        elif tool_name == "cash_api_getPayments":
            return {
                "tool_name": tool_name,
                "success": True,
                "result": {
                    "status": "success",
                    "payments": [
                        {"id": "P001", "amount": 1000, "status": "pending", "description": "Payment 1"},
                        {"id": "P002", "amount": 2500, "status": "pending", "description": "Payment 2"}
                    ]
                },
                "execution_time": 0.3
            }
        elif tool_name == "cash_api_getCashSummary":
            return {
                "tool_name": tool_name,
                "success": True,
                "result": {
                    "status": "success",
                    "total_balance": 50000,
                    "pending_approvals": 2,
                    "available_balance": 47500
                },
                "execution_time": 0.2
            }
        elif tool_name == "securities_api_getPositions":
            return {
                "tool_name": tool_name,
                "success": True,
                "result": {
                    "status": "success",
                    "positions": [
                        {"symbol": "AAPL", "quantity": 100, "value": 15000},
                        {"symbol": "GOOGL", "quantity": 50, "value": 7500}
                    ]
                },
                "execution_time": 0.4
            }
        elif tool_name == "mailbox_api_getMessages":
            return {
                "tool_name": tool_name,
                "success": True,
                "result": {
                    "status": "success",
                    "messages": [
                        {"id": "M001", "subject": "Payment Approval Required", "unread": True},
                        {"id": "M002", "subject": "Daily Summary", "unread": False}
                    ]
                },
                "execution_time": 0.2
            }
        else:
            return {
                "tool_name": tool_name,
                "success": False,
                "result": None,
                "error": f"Unknown tool: {tool_name}",
                "execution_time": 0.0
            }
    
    def _generate_summary(self, user_query: str, results: List[Dict[str, Any]], tool_calls: List[Dict[str, Any]]) -> str:
        """Generate a summary of the results."""
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]
        
        parts = [f"Query: {user_query}", ""]
        
        if successful:
            parts.append("✅ Successfully executed:")
            for r in successful:
                parts.append(f"- {r['tool_name']}")
                if r.get("result"):
                    result_data = r["result"]
                    if "payments" in result_data:
                        payments = result_data["payments"]
                        parts.append(f"  Found {len(payments)} payments")
                        for payment in payments[:2]:  # Show first 2
                            parts.append(f"  • {payment.get('description', 'Payment')}: ${payment.get('amount', 0)} ({payment.get('status', 'unknown')})")
                    elif "total_balance" in result_data:
                        parts.append(f"  Total balance: ${result_data.get('total_balance', 0)}")
                        parts.append(f"  Pending approvals: {result_data.get('pending_approvals', 0)}")
                    elif "positions" in result_data:
                        positions = result_data["positions"]
                        parts.append(f"  Found {len(positions)} positions")
                        for position in positions[:2]:  # Show first 2
                            parts.append(f"  • {position.get('symbol', 'Unknown')}: {position.get('quantity', 0)} shares (${position.get('value', 0)})")
                    elif "messages" in result_data:
                        messages = result_data["messages"]
                        parts.append(f"  Found {len(messages)} messages")
                        for message in messages[:2]:  # Show first 2
                            parts.append(f"  • {message.get('subject', 'No subject')} ({'unread' if message.get('unread') else 'read'})")
                    elif "status" in result_data and result_data["status"] == "success":
                        parts.append(f"  {result_data.get('message', 'Operation completed successfully')}")
            parts.append("")
        
        if failed:
            parts.append("❌ Failed:")
            for r in failed:
                parts.append(f"- {r['tool_name']}: {r.get('error', 'Unknown error')}")
            parts.append("")
        
        # Add performance summary
        parts.append(f"📊 Performance Summary:")
        parts.append(f"   Success rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")
        
        return "\n".join(parts)

async def test_llm_tool_calling():
    """Test the LLM tool calling logic."""
    print("🧪 Testing LLM Tool Calling Logic")
    print("=" * 50)
    
    client = MockMCPClient()
    await client.connect()
    
    # Test cases that demonstrate how the LLM calls tools based on user queries
    test_queries = [
        "I need to login to the system",
        "Show me my pending payments",
        "What's my cash summary?",
        "I want to see my securities positions",
        "Check my mailbox for new messages",
        "I need help with authentication",
        "Show me all my financial data",
        "What's the weather like today?"  # This should not trigger any tools
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        print("-" * 40)
        
        response = await client.process_query(query)
        
        print(f"Status: {response['status']}")
        print(f"Tools planned: {len(response['plan'])}")
        
        if response['plan']:
            print("Tool calls:")
            for tool_call in response['plan']:
                print(f"  • {tool_call['tool_name']}: {tool_call['reason']}")
                if tool_call['arguments']:
                    print(f"    Arguments: {tool_call['arguments']}")
        
        print(f"\nSummary:")
        print(response['summary'])
        print("=" * 50)

async def demonstrate_azure_4o_planning():
    """Demonstrate how Azure 4o would enhance the planning."""
    print("\n🤖 Azure 4o Enhanced Planning (Conceptual)")
    print("=" * 50)
    
    print("""
In the actual chatbot_app.py, the system can use Azure 4o for intelligent tool planning:

1. **Simple Planning (Current Fallback)**:
   - Keyword-based matching
   - Hard-coded tool selection logic
   - Limited context understanding

2. **Azure 4o Planning (When Enabled)**:
   - Natural language understanding
   - Context-aware tool selection
   - Dynamic argument generation
   - Multi-step reasoning

Example Azure 4o Planning:
""")
    
    example_queries = [
        "I need to approve the pending payment for $1000 from client ABC",
        "Show me my portfolio performance for the last quarter",
        "I want to transfer funds from my checking to savings account"
    ]
    
    for query in example_queries:
        print(f"\nQuery: '{query}'")
        print("Azure 4o would analyze:")
        print("  • Intent: Complex financial operation")
        print("  • Context: Multi-step process required")
        print("  • Tools needed: Authentication → Data retrieval → Action execution")
        print("  • Arguments: Dynamically generated based on query context")
        print("  • Sequence: Logical order of operations")

async def main():
    """Main test function."""
    print("🚀 LLM Tool Calling Demonstration")
    print("=" * 60)
    print("This demonstrates how the LLM in chatbot_app.py calls tools based on user queries.")
    print()
    
    await test_llm_tool_calling()
    await demonstrate_azure_4o_planning()
    
    print("\n🎉 Demonstration Complete!")
    print("\nKey Points:")
    print("1. The chatbot_app.py uses keyword-based analysis to determine which tools to call")
    print("2. It can be enhanced with Azure 4o for more intelligent planning")
    print("3. The system supports both simple and complex multi-tool workflows")
    print("4. Tool calls are executed in sequence and results are summarized")

if __name__ == "__main__":
    asyncio.run(main())