#!/usr/bin/env python3
"""
Proper MCP Client Implementation - Demonstration
This shows how a proper MCP client should be structured using the actual MCP protocol.
This is a demonstration version that shows the correct architecture.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

# In a real implementation, these would be the actual MCP imports:
# from mcp import ClientSession, StdioServerParameters
# from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# Mock MCP types for demonstration
@dataclass
class MockTool:
    name: str
    description: str
    inputSchema: Dict[str, Any]

@dataclass
class MockTextContent:
    text: str

@dataclass
class MockToolResult:
    content: List[MockTextContent]

# Mock MCP Client Session for demonstration
class MockClientSession:
    def __init__(self, server_params):
        self.server_params = server_params
        self.initialized = False
        
    async def initialize(self):
        """Initialize the MCP session."""
        self.initialized = True
        logging.info("Mock MCP session initialized")
        
    async def list_tools(self):
        """List available tools."""
        # Mock tools from the OpenAPI specs
        mock_tools = [
            MockTool(
                name="cash_api_getPayments",
                description="GET /payments - Get all payments with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pending", "approved", "rejected", "completed"]},
                        "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                        "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                        "amount_min": {"type": "number", "description": "Minimum amount filter"},
                        "amount_max": {"type": "number", "description": "Maximum amount filter"}
                    }
                }
            ),
            MockTool(
                name="cash_api_getCashSummary",
                description="GET /summary - Get cash summary including pending approvals",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date_range": {"type": "string", "enum": ["today", "yesterday", "last_7_days", "this_month", "last_month"]},
                        "include_pending": {"type": "boolean", "default": True}
                    }
                }
            ),
            MockTool(
                name="set_credentials",
                description="Set authentication credentials for API access",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "Username for authentication"},
                        "password": {"type": "string", "description": "Password for authentication"},
                        "api_key_name": {"type": "string", "description": "API key header name"},
                        "api_key_value": {"type": "string", "description": "API key value"},
                        "login_url": {"type": "string", "description": "Login URL"}
                    }
                }
            ),
            MockTool(
                name="perform_login",
                description="Perform login using stored credentials to obtain session token",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "force_login": {"type": "boolean", "default": False}
                    }
                }
            )
        ]
        
        class MockToolsResponse:
            def __init__(self, tools):
                self.tools = tools
                
        return MockToolsResponse(mock_tools)
        
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Call a tool and return mock results."""
        logging.info(f"Mock MCP tool call: {tool_name} with args: {arguments}")
        
        # Mock different responses based on tool name
        if tool_name == "cash_api_getPayments":
            mock_data = {
                "payments": [
                    {
                        "id": "PAY-001",
                        "amount": 1500.00,
                        "currency": "USD",
                        "status": "pending",
                        "description": "Rent payment",
                        "recipient": "Property Management Co",
                        "created_at": "2024-01-15T10:00:00Z"
                    },
                    {
                        "id": "PAY-002", 
                        "amount": 250.00,
                        "currency": "USD",
                        "status": "pending",
                        "description": "Utility bill",
                        "recipient": "Electric Company",
                        "created_at": "2024-01-16T14:30:00Z"
                    }
                ],
                "total_count": 2
            }
        elif tool_name == "cash_api_getCashSummary":
            mock_data = {
                "total_balance": 15420.50,
                "currency": "USD",
                "pending_approvals": 2,
                "pending_amount": 1750.00,
                "recent_transactions": [
                    {
                        "id": "TXN-001",
                        "type": "debit",
                        "amount": 500.00,
                        "description": "ATM withdrawal",
                        "timestamp": "2024-01-16T09:00:00Z"
                    }
                ]
            }
        elif tool_name == "set_credentials":
            mock_data = {
                "status": "success",
                "message": "Credentials stored successfully",
                "username": arguments.get("username", "demo_user")
            }
        elif tool_name == "perform_login":
            mock_data = {
                "status": "success",
                "message": "Login successful",
                "session_id": "mock_session_12345"
            }
        else:
            mock_data = {"error": f"Unknown tool: {tool_name}"}
            
        return MockToolResult(content=[MockTextContent(text=json.dumps(mock_data, indent=2))])
        
    async def close(self):
        """Close the MCP session."""
        self.initialized = False
        logging.info("Mock MCP session closed")

# Mock server parameters
class MockStdioServerParameters:
    def __init__(self, command, args=None):
        self.command = command
        self.args = args or []

@dataclass
class ToolCall:
    """Represents a tool call to be executed."""
    tool_name: str
    arguments: Dict[str, Any]
    reason: Optional[str] = None

@dataclass
class ToolResult:
    """Represents the result of a tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
        }

class ProperMCPClient:
    """Proper MCP Client using the official MCP protocol (demonstration version)"""
    
    def __init__(self, server_command: List[str] = None):
        self.server_command = server_command or ["python", "mcp_server.py", "--transport", "stdio"]
        self.available_tools: List[MockTool] = []
        self.session: Optional[MockClientSession] = None
        self.connected = False
        
        logging.info(f"Initialized Proper MCP Client with server command: {' '.join(self.server_command)}")
    
    async def connect(self) -> bool:
        """Connect to MCP server using proper MCP protocol."""
        try:
            if self.connected:
                logging.info("Already connected to MCP server")
                return True
                
            # Create server parameters for stdio transport
            server_params = MockStdioServerParameters(
                command=self.server_command[0],
                args=self.server_command[1:] if len(self.server_command) > 1 else []
            )
            
            # Create MCP client session
            self.session = MockClientSession(server_params)
            
            # Initialize the session
            await self.session.initialize()
            
            # Load available tools
            await self._load_tools()
            
            self.connected = True
            logging.info(f"✅ Connected to MCP server with {len(self.available_tools)} tools")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to connect to MCP server: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        try:
            if self.session:
                await self.session.close()
            self.connected = False
            logging.info("Disconnected from MCP server")
        except Exception as e:
            logging.error(f"Error disconnecting from MCP server: {e}")
    
    async def _load_tools(self) -> List[MockTool]:
        """Load available tools from MCP server."""
        try:
            if not self.session:
                raise Exception("Not connected to MCP server")
                
            # Get tools from MCP server
            tools_response = await self.session.list_tools()
            tools = tools_response.tools
            
            self.available_tools = tools
            logging.info(f"✅ Loaded {len(tools)} tools from MCP server")
            return tools
            
        except Exception as e:
            logging.error(f"Error loading tools: {e}")
            return []
    
    async def list_tools(self) -> List[MockTool]:
        """Get list of available tools from MCP server."""
        if not self.connected:
            await self.connect()
        return self.available_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server using proper MCP protocol."""
        if arguments is None:
            arguments = {}
            
        try:
            if not self.session:
                raise Exception("Not connected to MCP server")
                
            logging.info(f"Calling MCP tool: {tool_name} with arguments: {arguments}")
            
            # Call tool using MCP protocol
            result = await self.session.call_tool(tool_name, arguments)
            
            # Extract text content from MCP result
            if result.content:
                content_text = ""
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        content_text += content_item.text
                
                # Try to parse as JSON if it looks like JSON
                try:
                    parsed_result = json.loads(content_text)
                    return {"status": "success", "data": parsed_result}
                except json.JSONDecodeError:
                    return {"status": "success", "data": content_text}
            else:
                return {"status": "success", "data": None}
                
        except Exception as e:
            logging.error(f"Error calling MCP tool {tool_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def execute_tool_plan(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute a plan of tool calls and collect results."""
        results: List[ToolResult] = []
        for i, tc in enumerate(tool_calls, 1):
            logging.info(f"Executing tool {i}/{len(tool_calls)}: {tc.tool_name}")
            try:
                import time
                start_time = time.time()
                raw = await self.call_tool(tc.tool_name, tc.arguments)
                execution_time = time.time() - start_time
                
                results.append(
                    ToolResult(
                        tool_name=tc.tool_name,
                        success=raw.get("status") == "success",
                        result=raw.get("data") if raw.get("status") == "success" else None,
                        error=raw.get("message") if raw.get("status") == "error" else None,
                        execution_time=execution_time,
                    )
                )
            except Exception as e:
                logging.error(f"Exception during tool execution: {e}")
                results.append(ToolResult(tool_name=tc.tool_name, success=False, result=None, error=str(e), execution_time=0.0))
        return results
    
    def _build_tools_description(self) -> str:
        """Build description of available tools."""
        descriptions = []
        
        for tool in self.available_tools:
            desc_parts = [f"🔧 {tool.name}"]
            desc_parts.append(f"   Description: {tool.description}")
            
            # Add schema information
            schema = tool.inputSchema or {}
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            if properties:
                desc_parts.append("   Parameters:")
                for prop_name, prop_info in list(properties.items())[:3]:  # Limit for brevity
                    prop_type = prop_info.get('type', 'any')
                    prop_desc = prop_info.get('description', '')
                    is_required = prop_name in required
                    req_indicator = "*" if is_required else ""
                    desc_parts.append(f"     - {prop_name}{req_indicator}: {prop_type} - {prop_desc}")
                
                if len(properties) > 3:
                    desc_parts.append(f"     ... and {len(properties) - 3} more parameters")
            
            descriptions.append("\n".join(desc_parts))
        
        return "\n\n".join(descriptions)
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """End-to-end: plan tools, execute, summarize, return structured data."""
        logging.info(f"Processing query: {user_query}")
        
        # Ensure connection and tool listing
        if not await self.connect():
            return {"status": "error", "message": "Failed to connect to MCP server"}
        if not self.available_tools:
            await self.list_tools()

        # Simple planning based on keywords
        tool_calls = self._simple_plan(user_query)
        if not tool_calls:
            summary = "No suitable tools found for this request."
            return {"status": "ok", "plan": [], "results": [], "summary": summary}

        # Execute
        tool_results = await self.execute_tool_plan(tool_calls)

        # Generate summary
        summary = self._generate_summary(user_query, tool_results, tool_calls)

        return {
            "status": "ok",
            "plan": [{"tool_name": c.tool_name, "arguments": c.arguments, "reason": c.reason} for c in tool_calls],
            "results": [r.to_dict() for r in tool_results],
            "summary": summary,
        }
    
    def _simple_plan(self, user_query: str) -> List[ToolCall]:
        """Simple planning based on keywords."""
        query_lower = user_query.lower()
        tool_calls = []
        
        if any(keyword in query_lower for keyword in ["payment", "pending", "show"]):
            tool_calls.append(ToolCall(
                tool_name="cash_api_getPayments",
                arguments={"status": "pending"},
                reason="User asked about pending payments"
            ))
        
        if any(keyword in query_lower for keyword in ["summary", "balance", "overview"]):
            tool_calls.append(ToolCall(
                tool_name="cash_api_getCashSummary",
                arguments={"include_pending": True},
                reason="User asked for cash summary"
            ))
        
        return tool_calls
    
    def _generate_summary(self, user_query: str, tool_results: List[ToolResult], tool_calls: List[ToolCall]) -> str:
        """Generate a summary of the results."""
        successful = [r for r in tool_results if r.success]
        failed = [r for r in tool_results if not r.success]
        
        parts = [f"Query: {user_query}", ""]
        
        if successful:
            parts.append("✅ Successfully executed:")
            for r in successful:
                parts.append(f"- {r.tool_name}")
                if r.result:
                    # Add key insights from the data
                    if isinstance(r.result, dict):
                        if "payments" in r.result:
                            payments = r.result["payments"]
                            parts.append(f"  Found {len(payments)} payments")
                            for payment in payments[:2]:  # Show first 2
                                parts.append(f"  • {payment.get('description', 'Payment')}: ${payment.get('amount', 0)} ({payment.get('status', 'unknown')})")
                        elif "total_balance" in r.result:
                            parts.append(f"  Total balance: ${r.result.get('total_balance', 0)}")
                            parts.append(f"  Pending approvals: {r.result.get('pending_approvals', 0)}")
            parts.append("")
        
        if failed:
            parts.append("❌ Failed:")
            for r in failed:
                parts.append(f"- {r.tool_name}: {r.error}")
            parts.append("")
        
        parts.append(f"Total: {len(successful)} successful, {len(failed)} failed")
        return "\n".join(parts)

async def main():
    """Demonstration of proper MCP Client."""
    print("Proper MCP Client - Demonstration")
    print("=================================")
    print()
    print("🔌 This demonstrates how a proper MCP client should work")
    print("📋 Using mock MCP protocol implementation")
    print()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create proper MCP client
    client = ProperMCPClient()
    
    try:
        print(f"\n🔗 Connecting to MCP server via stdio...")
        if not await client.connect():
            print("Failed to connect to MCP server")
            return
        
        print("📋 Listing available tools...")
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        if tools:
            print("\n🧪 Testing tool execution...")
            result = await client.process_query("Show me my pending payments and cash summary")
            print("\nResult:")
            print("=" * 50)
            print(result["summary"])
            print("=" * 50)
        
    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
    finally:
        print("\n👋 Disconnecting from MCP server")
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())