#!/usr/bin/env python3
"""
HTTP-based MCP client used by the FastAPI chatbot frontend.
- Uses aiohttp to call the HTTP introspection endpoints exposed by openapi_mcp_server.py
- Provides higher-level async methods expected by chatbot_app.py
"""

import asyncio
import logging
import os
import aiohttp
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastmcp_client")


class DirectHTTPMCPClient:
    def __init__(self, server_url: str = None):
        if server_url is None:
            server_url = os.getenv('MCP_SERVER_ENDPOINT', 'http://localhost:9000')
        self.server_url = server_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None
        self.authenticated = False
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.base_url: Optional[str] = None
        self.login_path: Optional[str] = "/login"
        self.environment = "DEV"

    async def _ensure_session(self):
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def health_check(self) -> bool:
        try:
            await self._ensure_session()
            # Try endpoints list first; fallback to tools list
            async with self._session.get(f"{self.server_url}/endpoints") as resp:
                return resp.status == 200
        except Exception as e:
            logger.debug("Health check failed: %s", e)
            return False

    async def list_tools(self) -> Dict[str, Any]:
        """Return normalized list of tool objects: [{name, description}, ...].
        Tries rich tool listing endpoint first, then falls back to plain endpoints list.
        """
        try:
            await self._ensure_session()

            # 1. Prefer /tools (expects {"tools": [{"name":..., "description": ...}, ...]})
            for path in ("/tools", "/endpoints"):
                url = f"{self.server_url}{path}"
                try:
                    async with self._session.get(url) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                        if path == "/tools" and "tools" in data:
                            tools_raw = data.get("tools", [])
                            # ensure each item is an object with name/description
                            normalized = []
                            for item in tools_raw:
                                if isinstance(item, dict):
                                    name = item.get("name") or item.get("id") or "unknown"
                                    desc = item.get("description", "")
                                else:
                                    name = str(item)
                                    desc = ""
                                normalized.append({"name": name, "description": desc})
                            return {"status": "success", "tools": normalized}
                        if path == "/endpoints" and "endpoints" in data:
                            normalized = [{"name": name, "description": ""} for name in data.get("endpoints", [])]
                            return {"status": "success", "tools": normalized}
                except Exception:
                    # try next path
                    continue
            return {"status": "error", "message": "No tool listing endpoint succeeded"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a specific tool exposed by the MCP server.
        The OpenAPI MCP server exposes tools via the FastMCP mcp transport.
        For the HTTP wrapper we simulate execution by calling / (chat) or use the server's introspection.
        The OpenAPI MCP server itself uses FastMCP; this HTTP client uses the 'chat' endpoint of the Chatbot app
        or asks the server to execute via an application-specific endpoint (not implemented here).
        We'll POST to /tools/<tool_name> if available on the HTTP layer; otherwise, we call /chat with a structured prompt.
        """
        try:
            await self._ensure_session()
            # prefer a dedicated HTTP /tools/<tool_name> if present on the server
            tool_url = f"{self.server_url}/tools/{tool_name}"
            try:
                async with self._session.post(tool_url, json={"arguments": kwargs}) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except Exception:
                # fallthrough to chat-style execution
                pass

            # Fallback: call POST /chat with a structured message that the server's chat endpoint understands.
            chat_payload = {"message": f"CALL_TOOL {tool_name} ARGS {kwargs}"}
            async with self._session.post(f"{self.server_url}/chat", json=chat_payload) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    # chat endpoint returns {"response": {...}, ...}
                    return body.get("response", body)
                text = await resp.text()
                return {"status": "error", "message": f"HTTP {resp.status}: {text}"}
        except Exception as e:
            logger.exception("call_tool failed")
            return {"status": "error", "message": str(e)}

    async def __aenter__(self):
        """
        Enter the asynchronous context manager.
        """
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the asynchronous context manager.
        """
        await self.close()


class ChatbotFastMCPClient(DirectHTTPMCPClient):
    """
    The client used by chatbot_app.py. Adds high level chat helpers expected by the app.
    """

    def __init__(self, server_url: str = None):
        super().__init__(server_url)
        self.conversation_history: List[Dict[str, Any]] = []

    async def login(self) -> Dict[str, Any]:
        if not self.username or not self.password:
            return {"status": "error", "message": "username/password required"}
        try:
            # Server login tool accepts: username, password, optional spec_name/api_key_*
            # Also pass login_path if configured
            login_args = {"username": self.username, "password": self.password}
            if self.login_path:
                login_args["login_path"] = self.login_path
            return await self.call_tool("login", **login_args)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def ask_question(self, question: str) -> Dict[str, Any]:
        """
        Ask a natural question. The server is expected to have an 'intelligent_api_router' tool or an HTTP /chat route.
        This function posts to /chat and returns the server's response payload (dict).
        """
        self.conversation_history.append({"role": "user", "content": question})
        await self._ensure_session()
        try:
            payload = {"message": question}
            async with self._session.post(f"{self.server_url}/chat", json=payload) as resp:
                text = await resp.text()
                if resp.status == 200:
                    body = await resp.json()
                    # The existing chatbot_app returns shape: {"response": ..., "session_id":..., ...}
                    return body.get("response", body)
                else:
                    return {"status": "error", "message": f"HTTP {resp.status}: {text}"}
        except Exception as e:
            logger.exception("ask_question failed")
            return {"status": "error", "message": str(e)}

    async def reload_openapi_specs(self) -> Dict[str, Any]:
        return await self.call_tool("reload_openapi_specs")

    async def list_loaded_specs(self) -> Dict[str, Any]:
        return await self.call_tool("list_loaded_specs")

    async def list_api_endpoints(self) -> Dict[str, Any]:
        return await self.call_tool("list_api_endpoints")

    async def get_tool_meta(self, tool_name: str) -> Dict[str, Any]:
        """Fetch metadata for a given tool via HTTP proxy endpoint if available."""
        try:
            await self._ensure_session()
            async with self._session.get(f"{self.server_url}/tool_meta/{tool_name}") as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"status": "error", "message": f"HTTP {resp.status}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def call_llm_agent(self, message: str, model: Optional[str] = None) -> dict:
        """Call the /llm/agent endpoint on the MCP server.
        If the configured server_url includes '/mcp', strip it for LLM routes which live at the root ('/llm/*').
        """
        await self._ensure_session()
        payload = {'message': message}
        if model:
            payload['model'] = model
        # Derive base without trailing '/mcp' for LLM routes
        base_url = self.server_url.rstrip('/')
        if base_url.endswith('/mcp'):
            base_url = base_url[:-4]
        try:
            async with self._session.post(f"{base_url}/llm/agent", json=payload) as resp:
                if resp.status != 200:
                    detail = await resp.text()
                    return {"status": "error", "message": f"HTTP {resp.status}: {detail}"}
                return await resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # convenience
    def get_conversation_history(self):
        return list(self.conversation_history)

    def clear_conversation_history(self):
        self.conversation_history = []


# quick test runner (async)
async def _test():
    client = ChatbotFastMCPClient()
    ok = await client.health_check()
    print("server up:", ok)
    if ok:
        tools = await client.list_tools()
        print("tools:", tools)
    await client.close()

if __name__ == "__main__":
    asyncio.run(_test())
