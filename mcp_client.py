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
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI


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
    """Truncate huge tool responses."""
    text = json.dumps(obj)
    tokens = count_tokens(text)
    if tokens <= max_tokens:
        return obj
    if isinstance(obj, list):
        subset = obj[:100]
    elif isinstance(obj, dict):
        subset = dict(list(obj.items())[:50])
    else:
        subset = str(obj)[:5000]
    return {
        "note": f"Response truncated from {tokens} tokens for safety.",
        "sample": subset
    }


async def create_azure_client() -> AsyncAzureOpenAI:
    """Create Azure OpenAI client with Azure AD token provider."""
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
