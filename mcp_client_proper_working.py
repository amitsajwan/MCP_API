#!/usr/bin/env python3
"""
Proper MCP Client Implementation - Working Version
This is a real MCP client that uses the official MCP protocol with stdio transport.
"""

import asyncio
import json
import logging
import os
import sys
import subprocess
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

# MCP Protocol imports
from mcp import ClientSession, StdioServerParameters
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# Import config
try:
    from config import config
except ImportError:
    class DefaultConfig:
        LOG_LEVEL = "INFO"
        MCP_SERVER_SCRIPT = "mcp_server.py"
        MCP_SERVER_ARGS = ["--transport", "stdio"]
        
        def validate(self):
            return True
    
    config = DefaultConfig()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_client_proper")

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
    response_size: int = 0
    paginated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "response_size": self.response_size,
            "paginated": self.paginated,
        }

class ProperMCPClient:
    """Proper MCP Client using the official MCP protocol with stdio transport"""
    
    def __init__(self, server_command: List[str] = None):
        self.server_command = server_command or [
            sys.executable, 
            config.MCP_SERVER_SCRIPT
        ] + config.MCP_SERVER_ARGS
        self.available_tools: List[Tool] = []
        self.session: Optional[ClientSession] = None
        self.connected = False
        self._stdio_context = None
        
        # Enhanced configuration
        self.max_response_size = getattr(config, 'MAX_RESPONSE_SIZE', 5000)
        self.max_retries = getattr(config, 'MAX_RETRIES', 3)
        self.retry_delay = getattr(config, 'RETRY_DELAY', 1.0)
        
        logger.info(f"Initialized Proper MCP Client with server command: {' '.join(self.server_command)}")
    
    async def connect(self) -> bool:
        """Connect to MCP server using proper MCP protocol with stdio transport."""
        try:
            if self.connected:
                logger.info("Already connected to MCP server")
                return True
                
            # Create server parameters for stdio transport
            server_params = StdioServerParameters(
                command=self.server_command[0],
                args=self.server_command[1:] if len(self.server_command) > 1 else []
            )
            
            # Create MCP client session with stdio transport
            from mcp.client.stdio import stdio_client
            self._stdio_context = stdio_client(server_params)
            read_stream, write_stream = await self._stdio_context.__aenter__()
            self.session = ClientSession(read_stream, write_stream)
            
            # Initialize the session
            await self.session.initialize()
            
            # Load available tools
            await self._load_tools()
            
            self.connected = True
            logger.info(f"✅ Connected to MCP server with {len(self.available_tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MCP server: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        try:
            if self.session:
                await self.session.close()
            if hasattr(self, '_stdio_context'):
                await self._stdio_context.__aexit__(None, None, None)
            self.connected = False
            logger.info("Disconnected from MCP server")
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server: {e}")
    
    async def _load_tools(self) -> List[Tool]:
        """Load available tools from MCP server."""
        try:
            if not self.session:
                raise Exception("Not connected to MCP server")
                
            # Get tools from MCP server
            tools_response = await self.session.list_tools()
            self.available_tools = tools_response.tools
            
            logger.info(f"✅ Loaded {len(self.available_tools)} tools from MCP server")
            return self.available_tools
            
        except Exception as e:
            logger.error(f"Error loading tools: {e}")
            return []
    
    async def list_tools(self) -> List[Tool]:
        """Get list of available tools from MCP server."""
        if not self.connected:
            await self.connect()
        return self.available_tools
    
    def _estimate_response_size(self, data: Any) -> int:
        """Estimate the size of a response in tokens (rough approximation)."""
        if isinstance(data, str):
            return len(data.split())
        elif isinstance(data, dict):
            return sum(self._estimate_response_size(v) for v in data.values())
        elif isinstance(data, list):
            return sum(self._estimate_response_size(item) for item in data)
        else:
            return len(str(data).split())
    
    def _truncate_response(self, data: Any, max_size: int) -> Dict[str, Any]:
        """Truncate response data to fit within size limits."""
        if isinstance(data, dict):
            truncated = {}
            current_size = 0
            
            for key, value in data.items():
                value_size = self._estimate_response_size(value)
                if current_size + value_size > max_size:
                    truncated[f"{key}_truncated"] = f"... (truncated, {value_size} tokens)"
                    break
                truncated[key] = value
                current_size += value_size
            
            return truncated
        elif isinstance(data, list):
            truncated = []
            current_size = 0
            
            for item in data:
                item_size = self._estimate_response_size(item)
                if current_size + item_size > max_size:
                    truncated.append(f"... (truncated, {len(data) - len(truncated)} more items)")
                    break
                truncated.append(item)
                current_size += item_size
            
            return truncated
        else:
            data_str = str(data)
            if len(data_str.split()) > max_size:
                words = data_str.split()
                truncated_words = words[:max_size]
                return " ".join(truncated_words) + f"... (truncated, {len(words) - max_size} more words)"
            return data

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server using proper MCP protocol with pagination handling."""
        if arguments is None:
            arguments = {}
            
        for attempt in range(self.max_retries):
            try:
                if not self.session:
                    raise Exception("Not connected to MCP server")
                    
                logger.info(f"Calling MCP tool: {tool_name} with arguments: {arguments} (attempt {attempt + 1})")
                
                # Call tool using MCP protocol
                result = await self.session.call_tool(tool_name, arguments)
                
                # Extract text content from MCP result
                if result.content:
                    content_text = ""
                    for content_item in result.content:
                        if isinstance(content_item, TextContent):
                            content_text += content_item.text
                        elif isinstance(content_item, ImageContent):
                            content_text += f"[Image: {content_item.data}]"
                        elif isinstance(content_item, EmbeddedResource):
                            content_text += f"[Resource: {content_item.uri}]"
                    
                    # Try to parse as JSON if it looks like JSON
                    try:
                        parsed_result = json.loads(content_text)
                        
                        # Check response size and truncate if necessary
                        response_size = self._estimate_response_size(parsed_result)
                        if response_size > self.max_response_size:
                            logger.warning(f"Response size ({response_size} tokens) exceeds limit ({self.max_response_size} tokens), truncating...")
                            parsed_result = self._truncate_response(parsed_result, self.max_response_size)
                            parsed_result["_truncated"] = True
                            parsed_result["_original_size"] = response_size
                        
                        return {
                            "status": "success", 
                            "data": parsed_result,
                            "response_size": response_size,
                            "truncated": response_size > self.max_response_size
                        }
                    except json.JSONDecodeError:
                        # Handle non-JSON responses
                        response_size = self._estimate_response_size(content_text)
                        if response_size > self.max_response_size:
                            logger.warning(f"Response size ({response_size} tokens) exceeds limit ({self.max_response_size} tokens), truncating...")
                            content_text = self._truncate_response(content_text, self.max_response_size)
                        
                        return {
                            "status": "success", 
                            "data": content_text,
                            "response_size": response_size,
                            "truncated": response_size > self.max_response_size
                        }
                else:
                    return {"status": "success", "data": None, "response_size": 0, "truncated": False}
                    
            except Exception as e:
                logger.warning(f"Tool call attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Error calling MCP tool {tool_name} after {self.max_retries} attempts: {e}")
                    return {"status": "error", "message": str(e), "response_size": 0, "truncated": False}
    
    async def execute_tool_plan(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute a plan of tool calls and collect results with enhanced monitoring."""
        results: List[ToolResult] = []
        for i, tc in enumerate(tool_calls, 1):
            logger.info(f"Executing tool {i}/{len(tool_calls)}: {tc.tool_name}")
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
                        response_size=raw.get("response_size", 0),
                        paginated=raw.get("truncated", False)
                    )
                )
            except Exception as e:
                logger.error(f"Exception during tool execution: {e}")
                results.append(ToolResult(
                    tool_name=tc.tool_name, 
                    success=False, 
                    result=None, 
                    error=str(e), 
                    execution_time=0.0,
                    response_size=0,
                    paginated=False
                ))
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
        logger.info(f"Processing query: {user_query}")
        
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
        
        # Check for authentication-related queries
        if any(keyword in query_lower for keyword in ["login", "authenticate", "credential", "password", "username", "connect", "setup"]):
            tool_calls.append(ToolCall(
                tool_name="set_credentials",
                arguments={},
                reason="User asked about authentication"
            ))
            tool_calls.append(ToolCall(
                tool_name="perform_login",
                arguments={},
                reason="User asked about login"
            ))
        
        # Check for payment-related queries
        if any(keyword in query_lower for keyword in ["payment", "pending", "show", "list"]):
            # Look for cash API tools
            for tool in self.available_tools:
                if "cash_api" in tool.name and "getPayments" in tool.name:
                    tool_calls.append(ToolCall(
                        tool_name=tool.name,
                        arguments={"status": "pending"},
                        reason="User asked about pending payments"
                    ))
                    break
        
        # Check for summary/balance queries
        if any(keyword in query_lower for keyword in ["summary", "balance", "overview", "total"]):
            # Look for cash summary tools
            for tool in self.available_tools:
                if "cash_api" in tool.name and "getCashSummary" in tool.name:
                    tool_calls.append(ToolCall(
                        tool_name=tool.name,
                        arguments={"include_pending": True},
                        reason="User asked for cash summary"
                    ))
                    break
        
        return tool_calls
    
    def _generate_summary(self, user_query: str, tool_results: List[ToolResult], tool_calls: List[ToolCall]) -> str:
        """Generate a summary of the results with pagination information."""
        successful = [r for r in tool_results if r.success]
        failed = [r for r in tool_results if not r.success]
        total_size = sum(getattr(r, 'response_size', 0) for r in tool_results)
        truncated_count = sum(1 for r in tool_results if getattr(r, 'truncated', False))
        
        parts = [f"Query: {user_query}", ""]
        
        if successful:
            parts.append("✅ Successfully executed:")
            for r in successful:
                response_size = getattr(r, 'response_size', 0)
                truncated = getattr(r, 'truncated', False)
                parts.append(f"- {r.tool_name}")
                if truncated:
                    parts.append(f"  ⚠️ Response was truncated due to size limits")
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
                        elif "status" in r.result and r.result["status"] == "success":
                            parts.append(f"  {r.result.get('message', 'Operation completed successfully')}")
            parts.append("")
        
        if failed:
            parts.append("❌ Failed:")
            for r in failed:
                parts.append(f"- {r.tool_name}: {r.error}")
            parts.append("")
        
        # Add performance summary
        parts.append(f"📊 Performance Summary:")
        parts.append(f"   Total response size: {total_size} tokens")
        parts.append(f"   Truncated responses: {truncated_count}")
        parts.append(f"   Success rate: {len(successful)}/{len(tool_results)} ({len(successful)/len(tool_results)*100:.1f}%)")
        
        return "\n".join(parts)

    async def set_credentials(self, username: str = None, password: str = None, api_key: str = None) -> Dict[str, Any]:
        """Set credentials using the set_credentials tool."""
        credentials = {}
        if username:
            credentials["username"] = username
        if password:
            credentials["password"] = password
        if api_key:
            credentials["api_key_value"] = api_key
            
        return await self.call_tool("set_credentials", credentials)
    
    async def perform_login(self) -> Dict[str, Any]:
        """Call the perform_login tool on the MCP server."""
        logger.info("Attempting to perform login via MCP server tool.")
        try:
            result = await self.call_tool("perform_login")
            if result.get("status") == "success":
                logger.info("✅ Login tool call successful.")
                return {"status": "success", "message": "Login successful"}
            else:
                error_message = result.get("message", "Unknown error during login tool call.")
                logger.error(f"❌ Login tool call failed: {error_message}")
                return {"status": "error", "message": error_message}
        except Exception as e:
            logger.error(f"Exception when calling perform_login tool: {e}")
            return {"status": "error", "message": str(e)}

async def main():
    """Demonstration of proper MCP Client."""
    print("Proper MCP Client - Working Version")
    print("===================================")
    print()
    print("🔌 Using real MCP protocol with stdio transport")
    print()
    
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
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
    finally:
        print("\n👋 Disconnecting from MCP server")
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())