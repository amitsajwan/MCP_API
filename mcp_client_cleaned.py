#!/usr/bin/env python3
"""
MCP Client - Production HTTP-Only Implementation
Optimized MCP client for production use:
- HTTP-only communication with MCP server
- Synchronous OpenAI client for better reliability
- Preserved authentication and login logic
- Streamlined tool execution flow
"""

import logging
import asyncio
import json
import os
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from tool_categorizer import DynamicToolCategorizer

# Tool type definition
@dataclass
class Tool:
    name: str
    description: str
    inputSchema: Dict[str, Any]

# Import config or create default
try:
    from config import config
except ImportError:
    # Create default config if not available
    class DefaultConfig:
        LOG_LEVEL = "INFO"
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        MAX_TOOL_EXECUTIONS = 5
        
        def validate(self):
            return True
    
    config = DefaultConfig()


# Configure logging
logging.basicConfig(
    level=getattr(logging, getattr(config, 'LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_client")


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

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict representation of the result."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
        }


class MCPClient:
    """Production MCP Client with HTTP-only communication"""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8000", 
                 openai_api_key: str = None, 
                 openai_model: str = "gpt-4o"):
        self.server_url = mcp_server_url
        self.available_tools: List[Tool] = []
        self.session = requests.Session()
        
        # Initialize OpenAI client - assume GPT-4o is available
        self.openai_client = self._create_openai_client()
        self.model = openai_model
        
        logging.info(f"Initialized MCP Client connecting to {mcp_server_url}")
        
        # Cache for tools and results
        self.tool_results: Dict[str, Any] = {}
        
        # Initialize dynamic tool categorizer
        self.tool_categorizer = DynamicToolCategorizer()
        

    
    def _create_openai_client(self) -> AsyncAzureOpenAI:
        """Create Azure OpenAI client with azure_ad_token_provider."""
        azure_endpoint = getattr(config, 'AZURE_OPENAI_ENDPOINT', os.getenv("AZURE_OPENAI_ENDPOINT"))
        
        # Assume GPT-4o client is available - no fallback
        try:
            # Create Azure AD token provider
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            
            client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint or "https://your-resource.openai.azure.com/",
                azure_ad_token_provider=token_provider,
                api_version="2024-02-01"
            )
            logging.info("✅ Azure OpenAI client created with Azure AD authentication")
            return client
        except Exception as e:
            logging.error(f"Failed to create Azure OpenAI client: {e}")
            raise e
    

    
    def connect(self):
         """Connect to MCP server via HTTP."""
         try:
             response = self.session.get(f"{self.server_url}/health")
             if response.status_code == 200:
                 logging.info(f"✅ Connected to HTTP MCP server at {self.server_url}")
                 return True
             else:
                 raise Exception(f"Server health check failed: {response.status_code}")
         except Exception as e:
             logging.error(f"❌ Failed to connect to HTTP MCP server: {e}")
             return False
    
    def disconnect(self):
         """Disconnect from the HTTP MCP server."""
         logging.info("Disconnected from HTTP MCP server")
         if self.session:
             self.session.close()
    
    def close(self):
        """Close the MCP client connection. Alias for disconnect."""
        self.disconnect()
    
    def list_tools(self) -> List[Tool]:
         """Get list of available tools from HTTP MCP server."""
         try:
             response = self.session.get(f"{self.server_url}/tools")
             if response.status_code == 200:
                 data = response.json()
                 tools = []
                 for tool_data in data.get("tools", []):
                     tool = Tool(
                         name=tool_data["name"],
                         description=tool_data["description"],
                         inputSchema=tool_data.get("inputSchema", {"type": "object"})
                     )
                     tools.append(tool)
                 self.available_tools = tools
                 logging.info(f"✅ Retrieved {len(tools)} tools from HTTP MCP server")
                 return tools
             else:
                 raise Exception(f"HTTP {response.status_code}")
         except Exception as e:
             logging.error(f"Error listing tools: {e}")
             return []
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
         """Call a tool on the MCP server."""
         if arguments is None:
             arguments = {}
             
         try:
             logging.info(f"Calling tool: {tool_name} with arguments: {arguments}")
             
             payload = {"name": tool_name, "arguments": arguments}
             response = self.session.post(f"{self.server_url}/call_tool", json=payload)
             
             if response.status_code == 200:
                 result = response.json()
                 return {"status": "success", "data": result}
             else:
                 return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
                 
         except Exception as e:
             logging.error(f"Error calling tool {tool_name}: {e}")
             return {"status": "error", "message": str(e)}

    def perform_login(self) -> Dict[str, Any]:
        """Call the perform_login tool on the MCP server."""
        logger.info("Attempting to perform login via MCP server tool.")
        try:
            result = self.call_tool("perform_login")
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
    
    def set_credentials(self, username: str = None, password: str = None, api_key: str = None) -> Dict[str, Any]:
        """Set credentials using the set_credentials tool."""
        credentials = {}
        if username:
            credentials["username"] = username
        if password:
            credentials["password"] = password
        if api_key:
            credentials["api_key"] = api_key
            
        return self.call_tool("set_credentials", credentials)
    

    



    async def plan_tool_execution(self, user_query: str) -> List[ToolCall]:
        """Enhanced tool execution planning with intelligent analysis."""
        if not self.available_tools:
            self.list_tools()
        
        # If no tools available, return empty plan
        if not self.available_tools:
            logger.warning("No tools available for planning")
            return []
        
        # Check if this is an authentication-related query
        auth_keywords = ["login", "credential", "authenticate", "password", "username", "auth"]
        if any(keyword in user_query.lower() for keyword in auth_keywords):
            return self._plan_authentication_tools(user_query)
        
        # Assume OpenAI client is always available - no fallback planning needed
        
        # Build enhanced tools description for LLM
        tools_description = self._build_enhanced_tools_description()
        
        # Create enhanced system prompt for better reasoning
        system_prompt = f"""You are an expert financial API assistant that plans tool execution.

Available Financial Tools:
{tools_description}

User Query: "{user_query}"

Analyze the user's request and create an execution plan. Consider:
1. What specific financial data they're asking for
2. Which APIs contain that data
3. Any parameters that can be extracted from their query
4. The logical order of tool execution

Respond with a JSON array of tool calls:
[
  {{
    "tool_name": "exact_tool_name_from_list_above",
    "arguments": {{"param1": "value1", "param2": "value2"}},
    "reason": "detailed explanation of why this tool is needed"
  }}
]

Guidelines:
- Extract specific parameters from the user query when possible
- Use exact tool names from the available tools list
- Provide detailed reasoning for each tool selection
- If multiple tools could provide similar data, choose the most specific one
- If no tools match the request, return an empty array []
- For general requests, select the most comprehensive tool available
- Maximum {getattr(config, 'MAX_TOOL_EXECUTIONS', 5)} tool calls allowed"""

        # Use the LLM to plan tool calls and parse them
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You plan tool executions for financial APIs. Output only the requested JSON array."},
                    {"role": "user", "content": system_prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            content = response.choices[0].message.content
            logger.info(f"LLM planning response (truncated): {content[:200]}...")

            # Handle potential code fences
            if '```json' in content:
                content = content.split('```json', 1)[1].split('```', 1)[0].strip()
            elif '```' in content:
                content = content.split('```', 1)[1].strip()

            tool_calls_data = json.loads(content)
            planned_calls: List[ToolCall] = []

            for call in tool_calls_data:
                if isinstance(call, dict) and 'tool_name' in call:
                    # Validate the tool exists
                    name = call['tool_name']
                    if any(t.name == name for t in self.available_tools):
                        planned_calls.append(
                            ToolCall(
                                tool_name=name,
                                arguments=call.get('arguments', {}),
                                reason=call.get('reason', 'LLM-planned execution'),
                            )
                        )
                    else:
                        logger.warning(f"LLM suggested unknown tool: {name}")

            if planned_calls:
                return planned_calls[: getattr(config, 'MAX_TOOL_EXECUTIONS', 5)]
            return []
        except Exception as e:
            logger.error(f"Enhanced planning failed: {e}")
            return []
    
    async def _generate_ai_summary(self, user_query: str, tool_results: List[ToolResult], tool_calls: List[ToolCall]) -> str:
        """Generate summary using Azure OpenAI client."""
        try:
            # Prepare messages for OpenAI API
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful financial assistant. Provide clear, concise summaries of financial data and operations."
                },
                {
                    "role": "user",
                    "content": f"User query: {user_query}\n\nTool results: {json.dumps([result.to_dict() for result in tool_results], indent=2)}\n\nPlease provide a helpful summary."
                }
            ]
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error in AI summary generation: {e}")
            return self._generate_simple_summary(user_query, tool_results, tool_calls)
    

    def execute_tool_plan(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute a plan of tool calls and collect results."""
        results: List[ToolResult] = []
        for i, tc in enumerate(tool_calls, 1):
            logger.info(f"Executing tool {i}/{len(tool_calls)}: {tc.tool_name}")
            try:
                raw = self.call_tool(tc.tool_name, tc.arguments)
                results.append(
                    ToolResult(
                        tool_name=tc.tool_name,
                        success=raw.get("status") == "success",
                        result=raw.get("data") if raw.get("status") == "success" else None,
                        error=raw.get("message") if raw.get("status") == "error" else None,
                    )
                )
            except Exception as e:
                logger.error(f"Exception during tool execution: {e}")
                results.append(ToolResult(tool_name=tc.tool_name, success=False, result=None, error=str(e)))
        return results

    def _generate_simple_summary(self, user_query: str, tool_results: List[ToolResult], tool_calls: List[ToolCall]) -> str:
        successful = [r for r in tool_results if r.success]
        failed = [r for r in tool_results if not r.success]
        parts = [f"Query: {user_query}", ""]
        if successful:
            parts.append("✅ Successfully executed:")
            for r in successful:
                parts.append(f"- {r.tool_name}")
            parts.append("")
        if failed:
            parts.append("❌ Failed:")
            for r in failed:
                parts.append(f"- {r.tool_name}: {r.error}")
            parts.append("")
        parts.append(f"Total: {len(successful)} successful, {len(failed)} failed")
        return "\n".join(parts)

    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """End-to-end: plan tools, execute, summarize, return structured data."""
        logger.info(f"Processing query: {user_query}")
        # Ensure connection and tool listing
        if not self.connect():
            return {"status": "error", "message": "Failed to connect to MCP server"}
        if not self.available_tools:
            self.list_tools()

        # Plan
        tool_calls = await self.plan_tool_execution(user_query)
        if not tool_calls:
            summary = "No suitable tools found for this request."
            return {"status": "ok", "plan": [], "results": [], "summary": summary}

        # Execute
        tool_results = self.execute_tool_plan(tool_calls)

        # Summarize
        try:
            summary = await self._generate_ai_summary(user_query, tool_results, tool_calls)
        except Exception as e:
            logger.error(f"AI summary failed, using simple summary: {e}")
            summary = self._generate_simple_summary(user_query, tool_results, tool_calls)

        return {
            "status": "ok",
            "plan": [{"tool_name": c.tool_name, "arguments": c.arguments, "reason": c.reason} for c in tool_calls],
            "results": [r.to_dict() for r in tool_results],
            "summary": summary,
        }

    
def main():
    """Example usage of MCP Client - HTTP only."""
    print("MCP Client Test")
    print("===============")
    print()
    print("🔌 Using HTTP connection to MCP server")
    print("📋 Make sure to start the MCP server first:")
    print("   python mcp_server.py")
    print()
    
    # Create HTTP-only client
    client = MCPClient()
    
    try:
        print(f"\n🔗 Connecting to MCP server via HTTP...")
        if not client.connect():
            print("Failed to connect to MCP server")
            return
        
        print("📋 Listing available tools...")
        tools = client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools[:5]]}..." + (f" and {len(tools)-5} more" if len(tools) > 5 else ""))
        
        if tools:
            print("\n🧪 Testing tool execution...")
            # Ensure we run the async process_query properly
            result = asyncio.run(client.process_query("Show me pending payments"))
            print("Result:")
            print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
        print("\n💡 Make sure the MCP server is running:")
        print("   python mcp_server.py")
    finally:
        print("\n👋 Disconnected from MCP server")


if __name__ == "__main__":
    main()
