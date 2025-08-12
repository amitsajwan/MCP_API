#!/usr/bin/env python3
"""
Example usage script for the OpenAPI MCP Server

This script demonstrates how to use the MCP server to:
1. Load OpenAPI specifications
2. Execute API calls
3. Use intelligent routing
4. Get financial summaries
5. Check payment approvals

Now uses REAL MCP calls instead of mock ones!
"""

import json
import time
import logging
from typing import Dict, Any

from mcp_client import ChatbotMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main demonstration function"""
    print("🚀 Starting OpenAPI MCP Server Demo with REAL MCP calls!")
    print("=" * 60)
    
    # Initialize the real MCP client
    client = ChatbotMCPClient()
    
    # Check if MCP server is running
    print("\n1️⃣ Checking MCP server connection...")
    if not client.health_check():
        print("❌ MCP server is not running!")
        print("💡 Please start the MCP server first:")
        print("   python openapi_mcp_server.py")
        print("\n🔄 Starting server in background...")
        import subprocess
        import sys
        try:
            # Start the MCP server in background
            subprocess.Popen([sys.executable, "openapi_mcp_server.py"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            print("⏳ Waiting for server to start...")
            time.sleep(3)
            
            # Check again
            if not client.health_check():
                print("❌ Still cannot connect to MCP server")
                print("💡 Please manually start: python openapi_mcp_server.py")
                return
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return
    
    print("✅ MCP server is running and connected!")
    
    # Load API specifications
    print("\n2️⃣ Loading API specifications...")
    
    # Load Cash API
    print("📋 Loading Cash API...")
    cash_result = client.load_api_spec(
        spec_name="cash_api",
        yaml_path="api_specs/cash_api.yaml",
        base_url="https://api.company.com/cash/v1",
        auth_type="none"
    )
    print(f"   Result: {cash_result.get('status', 'unknown')}")
    
    # Load Securities API
    print("📈 Loading Securities API...")
    securities_result = client.load_api_spec(
        spec_name="securities_api",
        yaml_path="api_specs/securities_api.yaml",
        base_url="https://api.company.com/securities/v1",
        auth_type="none"
    )
    print(f"   Result: {securities_result.get('status', 'unknown')}")
    
    # Load CLS API
    print("🔄 Loading CLS API...")
    cls_result = client.load_api_spec(
        spec_name="cls_api",
        yaml_path="api_specs/cls_api.yaml",
        base_url="https://api.company.com/cls/v1",
        auth_type="none"
    )
    print(f"   Result: {cls_result.get('status', 'unknown')}")
    
    # Load Mailbox API
    print("📧 Loading Mailbox API...")
    mailbox_result = client.load_api_spec(
        spec_name="mailbox_api",
        yaml_path="api_specs/mailbox_api.yaml",
        base_url="https://api.company.com/mailbox/v1",
        auth_type="none"
    )
    print(f"   Result: {mailbox_result.get('status', 'unknown')}")
    
    # List available tools
    print("\n3️⃣ Listing available tools...")
    tools_result = client.list_tools()
    if "status" not in tools_result:
        print(f"✅ Found {len(tools_result.get('tools', []))} tools:")
        for tool in tools_result.get('tools', [])[:5]:  # Show first 5
            print(f"   - {tool['name']}: {tool['description'][:50]}...")
        if len(tools_result.get('tools', [])) > 5:
            print(f"   ... and {len(tools_result.get('tools', [])) - 5} more tools")
    else:
        print(f"❌ Failed to list tools: {tools_result}")
    
    # Test intelligent API routing
    print("\n4️⃣ Testing intelligent API routing...")
    
    questions = [
        "Show me all pending payments that need approval",
        "What's my current portfolio value?",
        "Are there any CLS settlements pending?",
        "Do I have any unread messages?",
        "Give me a summary of all financial activities"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n   Q{i}: {question}")
        try:
            result = client.ask_question(question)
            if result.get("status") == "error":
                print(f"   ❌ Error: {result.get('message', 'Unknown error')}")
            else:
                print(f"   ✅ Success: Found {len(result.get('results', []))} relevant APIs")
                for j, api_result in enumerate(result.get('results', [])[:2]):  # Show first 2
                    print(f"      {j+1}. {api_result.get('tool', 'Unknown')}: {api_result.get('status', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test financial summary
    print("\n5️⃣ Testing financial summary...")
    try:
        summary_result = client.get_financial_summary(date_range="this_month")
        if summary_result.get("status") == "error":
            print(f"   ❌ Error: {summary_result.get('message', 'Unknown error')}")
        else:
            print(f"   ✅ Success: Generated financial summary")
            print(f"      APIs called: {len(summary_result.get('results', []))}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test payment approvals
    print("\n6️⃣ Testing payment approvals...")
    try:
        approval_result = client.check_payment_approvals(status_filter="pending")
        if approval_result.get("status") == "error":
            print(f"   ❌ Error: {approval_result.get('message', 'Unknown error')}")
        else:
            print(f"   ✅ Success: Checked payment approvals")
            print(f"      APIs called: {len(approval_result.get('results', []))}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test parallel API execution
    print("\n7️⃣ Testing parallel API execution...")
    try:
        parallel_calls = [
            {"tool": "cash_getPayments", "params": {"status": "pending"}},
            {"tool": "securities_getPortfolio", "params": {}},
            {"tool": "cls_getCLSSettlements", "params": {"status": "pending"}},
            {"tool": "mailbox_getMessages", "params": {"unread": True}}
        ]
        
        parallel_result = client.execute_parallel_apis(tool_calls=parallel_calls)
        if parallel_result.get("status") == "error":
            print(f"   ❌ Error: {parallel_result.get('message', 'Unknown error')}")
        else:
            print(f"   ✅ Success: Executed {len(parallel_calls)} APIs in parallel")
            successful_calls = sum(1 for r in parallel_result.get('results', []) 
                                 if r.get('status') == 'success')
            print(f"      Successful calls: {successful_calls}/{len(parallel_calls)}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Show conversation history
    print("\n8️⃣ Conversation history:")
    history = client.get_conversation_history()
    for entry in history[-6:]:  # Show last 6 entries
        role = entry.get('role', 'unknown')
        content = entry.get('content', '')
        if isinstance(content, dict):
            content = f"API Response: {len(content.get('results', []))} results"
        else:
            content = str(content)[:50] + "..." if len(str(content)) > 50 else str(content)
        print(f"   {role.upper()}: {content}")
    
    print("\n" + "=" * 60)
    print("🎉 Demo completed successfully!")
    print("\n💡 Next steps:")
    print("   1. Start the FastAPI chatbot: python chatbot_app.py")
    print("   2. Open http://localhost:8080 in your browser")
    print("   3. Try asking questions in the web interface!")
    print("\n🔧 Available commands:")
    print("   - python openapi_mcp_server.py    # Start MCP server")
    print("   - python chatbot_app.py           # Start web chatbot")
    print("   - python mcp_client.py            # Test MCP client")
    print("   - python example_usage.py         # Run this demo")

if __name__ == "__main__":
    main()
