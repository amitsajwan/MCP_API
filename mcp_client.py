"""
MCP Client for Azure GPT-4o
---------------------------
- Discovers tools from any MCP server (stdio or HTTP transport)
- Handles hundreds of dynamic tools from OpenAPI specs
- Supports tool chaining: LLM can use multiple tools in sequence
- Truncates / summarizes large payloads to avoid context overflow
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List

from fastmcp import Client as MCPClient
from fastmcp.client import PythonStdioTransport

# Conditional Azure imports
try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AsyncAzureOpenAI
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    # Define fallback classes
    class DefaultAzureCredential:
        pass
    class AsyncAzureOpenAI:
        pass
    def get_bearer_token_provider(*args, **kwargs):
        return None


# ---------- CONFIG ----------
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource.openai.azure.com/")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")  # your GPT-4o deployment name
API_VERSION = "2024-02-01"
MAX_TOKENS_TOOL_RESPONSE = 4000  # safeguard for huge payloads
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure comprehensive logging for MCP client
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_client.log', encoding='utf-8')
    ]
)


# ---------- HELPERS ----------
def count_tokens(text: str) -> int:
    """Rough token counter."""
    return len(text.split())

def safe_truncate(obj: Any, max_tokens: int = MAX_TOKENS_TOOL_RESPONSE) -> Any:
    """Truncate huge tool responses while preserving JSON structure for LLM consumption."""
    
    # Handle CallToolResult objects specifically
    if hasattr(obj, 'isError') and hasattr(obj, 'content'):
        # Convert CallToolResult to a serializable dict
        serializable_obj = {
            "isError": obj.isError,
            "content": []
        }
        
        # Process content items
        for content_item in obj.content:
            if hasattr(content_item, 'text'):
                serializable_obj["content"].append({
                    "text": content_item.text
                })
            else:
                # Handle other content types
                serializable_obj["content"].append(str(content_item))
        
        return safe_truncate(serializable_obj, max_tokens)
    
    # Handle objects with structured_content attribute
    if hasattr(obj, 'structured_content'):
        try:
            # Try to serialize the structured_content first
            text = json.dumps(obj.structured_content)
        except (TypeError, ValueError):
            # If structured_content is not serializable, convert to string
            text = json.dumps(str(obj.structured_content))
    else:
        try:
            text = json.dumps(obj)
        except (TypeError, ValueError):
            # If object is not JSON serializable, convert to string representation
            text = json.dumps(str(obj))
    
    tokens = count_tokens(text)
    if tokens <= max_tokens:
        # Ensure the object is JSON serializable before returning
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # If not serializable, convert to a serializable format
            return {"data": str(obj), "type": type(obj).__name__}
    
    # Truncate while preserving JSON structure and ensuring serializability
    if isinstance(obj, list):
        # For lists, take a subset and add truncation info
        subset = obj[:100] if len(obj) > 100 else obj
        if len(obj) > 100:
            return {
                "note": f"Response truncated from {len(obj)} items to 100 items for safety.",
                "truncated_items": subset
            }
        return subset
    elif isinstance(obj, dict):
        # For dicts, take a subset of key-value pairs
        items = list(obj.items())
        if len(items) > 50:
            subset = dict(items[:50])
            return {
                "note": f"Response truncated from {len(items)} key-value pairs to 50 pairs for safety.",
                "truncated_data": subset
            }
        return obj
    else:
        # For other types, truncate the string representation
        str_repr = str(obj)
        if len(str_repr) > 5000:
            return {
                "note": f"Response truncated from {len(str_repr)} characters to 5000 characters for safety.",
                "truncated_text": str_repr[:5000]
            }
        return {"data": str_repr, "type": type(obj).__name__}


async def create_azure_client() -> AsyncAzureOpenAI:
    """Create Azure OpenAI client with Azure AD token provider."""
    if not AZURE_AVAILABLE:
        raise ImportError("Azure dependencies not available. Install azure-identity and openai packages.")
    
    logging.info("🔄 [MCP_CLIENT] Creating Azure OpenAI client...")
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=API_VERSION
    )
    logging.info("✅ [MCP_CLIENT] Azure OpenAI client created")
    return client


async def list_and_prepare_tools(mcp: MCPClient) -> List[Dict[str, Any]]:
    """Fetch available tools and convert them for Azure OpenAI."""
    logging.info("🔄 [MCP_CLIENT] Fetching tools from MCP server...")
    tools = await mcp.list_tools()
    logging.info(f"🔄 [MCP_CLIENT] Received {len(tools)} tools from MCP server")
    
    formatted = []
    for i, tool in enumerate(tools, 1):
        logging.info(f"🔧 [MCP_CLIENT] Processing tool {i}/{len(tools)}: {tool.name}")
        formatted.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema or {"type": "object", "properties": {}}
            }
        })
    logging.info(f"✅ [MCP_CLIENT] Loaded {len(formatted)} tools from MCP server")
    return formatted


async def run_chat(mcp_cmd: str, user_query: str):
    """Main chat loop with tool calling support."""
    # --- Connect to MCP server ---
    cmd_parts = mcp_cmd.split()
    script_path = cmd_parts[1]  # mcp_server_fastmcp2.py
    args = cmd_parts[2:]  # ['--transport', 'stdio']
    transport = PythonStdioTransport(script_path, args=args)
    async with MCPClient(transport) as mcp:
        tools = await list_and_prepare_tools(mcp)
        azure_client = await create_azure_client()

        # Conversation state for multi-step tool chaining
        messages = [
            {"role": "system", "content": (
                "You are an intelligent assistant. "
                "Use the available tools when helpful. "
                "If a tool may return thousands of records, first refine the query. "
                "Truncate or summarize results if they are huge."
            )},
            {"role": "user", "content": user_query}
        ]

        while True:
            # Call LLM
            response = await azure_client.chat.completions.create(
                model=AZURE_DEPLOYMENT,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            choice = response.choices[0]
            if choice.finish_reason == "tool_calls":
                # Add the assistant message with tool_calls to conversation history
                assistant_message = {
                    "role": "assistant",
                    "content": choice.message.content or "",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments or "{}"
                            }
                        }
                        for tool_call in choice.message.tool_calls
                    ]
                }
                messages.append(assistant_message)
                
                # Execute tool calls and add tool responses
                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments or "{}")
                    logging.info(f"🔧 LLM requested tool: {tool_name} with {args}")

                    try:
                        raw_result = await mcp.call_tool(tool_name, args)
                        result = safe_truncate(raw_result)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result)
                        })
                    except Exception as e:
                        logging.error(f"❌ Tool call failed: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: {e}"
                        })
                continue  # Loop to let LLM decide next step

            # Final response
            content = choice.message.content or ""
            print(f"\n🤖 Assistant: {content}\n")
            break


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MCP Client with Azure GPT-4o")
    parser.add_argument("query", help="User query")
    parser.add_argument(
        "--server",
        default="python mcp_server_fastmcp2.py --transport stdio",
        help="Command to start MCP server (default: stdio)"
    )
    args = parser.parse_args()

    asyncio.run(run_chat(args.server, args.query))
