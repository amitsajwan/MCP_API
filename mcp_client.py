#!/usr/bin/env python3
"""
Real MCP Client for connecting to the OpenAPI MCP Server

This client can make actual tool calls to the MCP server running on HTTP transport.
"""

import asyncio
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPClient:
    """Real MCP client for connecting to the MCP server"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        })
        # FastMCP uses /mcp/jsonrpc endpoint
        self.jsonrpc_url = f"{self.server_url}/mcp/jsonrpc"
    
    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Make a real tool call to the MCP server"""
        try:
            # Prepare the tool call request
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": kwargs
                }
            }
            
            logger.info(f"🔧 Calling tool: {tool_name}")
            logger.info(f"📝 Parameters: {kwargs}")
            
            # Make the HTTP request to the MCP server
            response = self.session.post(
                self.jsonrpc_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    logger.info(f"✅ Tool call successful: {tool_name}")
                    return result["result"]
                elif "error" in result:
                    logger.error(f"❌ Tool call failed: {result['error']}")
                    return {"status": "error", "message": result["error"]}
                else:
                    logger.error(f"❌ Unexpected response format: {result}")
                    return {"status": "error", "message": "Unexpected response format"}
            else:
                logger.error(f"❌ HTTP error {response.status_code}: {response.text}")
                return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return {"status": "error", "message": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}
    
    def list_tools(self) -> Dict[str, Any]:
        """Get list of available tools from the MCP server"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            response = self.session.post(
                self.jsonrpc_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return result["result"]
                elif "error" in result:
                    return {"status": "error", "message": result["error"]}
            
            return {"status": "error", "message": f"HTTP {response.status_code}"}
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to list tools: {str(e)}"}
    
    def health_check(self) -> bool:
        """Check if the MCP server is running and healthy"""
        try:
            # Try to connect to the MCP endpoint - if it responds, server is running
            response = self.session.get(f"{self.server_url}/mcp/", timeout=5)
            # 406 is expected for MCP protocol (Method Not Acceptable for GET)
            # Any response means the server is running
            return response.status_code >= 200
        except:
            return False

class ChatbotMCPClient(MCPClient):
    """Enhanced MCP client with chatbot-specific methods"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        super().__init__(server_url)
        self.conversation_history = []
        self.authenticated = False
        self.session_cookies = None
    
    def login(self) -> Dict[str, Any]:
        """Authenticate with the MCP server"""
        try:
            result = self.call_tool("login")
            if result.get("status") != "error":
                self.authenticated = True
                self.session_cookies = result.get("cookies", {})
                logger.info("✅ Successfully authenticated with MCP server")
            return result
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return {"status": "error", "message": f"Login failed: {str(e)}"}
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """Ask a natural language question and get intelligent response"""
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": question})
        
        # Ensure we're authenticated first
        if not self.authenticated:
            login_result = self.login()
            if login_result.get("status") == "error":
                return {"status": "error", "message": "Authentication required before asking questions"}
        
        # Use intelligent API router to handle the question
        result = self.call_tool("intelligent_api_router", query=question)
        
        # Add response to conversation history
        self.conversation_history.append({"role": "assistant", "content": result})
        
        return result
    
    def get_financial_summary(self, date_range: Optional[str] = None) -> Dict[str, Any]:
        """Get financial summary across all APIs"""
        return self.call_tool("get_financial_summary", date_range=date_range)
    
    def check_payment_approvals(self, payment_id: Optional[str] = None) -> Dict[str, Any]:
        """Check payment approval status"""
        return self.call_tool("check_payment_approvals", payment_id=payment_id)
    
    def load_api_spec(self, spec_name: str, yaml_path: str, base_url: str, 
                     auth_type: str = "none", **auth_params) -> Dict[str, Any]:
        """Load an OpenAPI specification"""
        params = {
            "spec_name": spec_name,
            "yaml_path": yaml_path,
            "base_url": base_url,
            "auth_type": auth_type,
            **auth_params
        }
        return self.call_tool("load_openapi_spec", **params)
    
    def execute_parallel_apis(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute multiple API calls in parallel"""
        return self.call_tool("execute_parallel_apis", tool_calls=tool_calls)
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history"""
        return self.conversation_history.copy()
    
    def clear_conversation_history(self):
        """Clear the conversation history"""
        self.conversation_history = []

# Example usage and testing
def test_mcp_client():
    """Test the MCP client with the server"""
    client = ChatbotMCPClient()
    
    # Check if server is running
    if not client.health_check():
        print("❌ MCP server is not running. Please start it first.")
        return
    
    print("✅ MCP server is running!")
    
    # Test listing tools
    print("\n📋 Available tools:")
    tools_result = client.list_tools()
    if "status" not in tools_result:
        for tool in tools_result.get("tools", []):
            print(f"  - {tool['name']}: {tool['description']}")
    else:
        print(f"❌ Failed to list tools: {tools_result}")
    
    # Test asking a question
    print("\n🤖 Testing chatbot functionality:")
    question = "Show me all pending payments that need approval"
    result = client.ask_question(question)
    print(f"Question: {question}")
    print(f"Response: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    test_mcp_client()
