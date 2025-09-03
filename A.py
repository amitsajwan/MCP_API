import asyncio
import json
import websockets
from typing import Any, Dict, Optional


class MCPClient:
    def __init__(self, uri: str):
        """
        Initialize MCP client with server WebSocket URI.
        Example: ws://localhost:8000/mcp
        """
        self.uri = uri
        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        self.message_id = 0
        self.pending_responses: Dict[str, asyncio.Future] = {}

    async def connect(self):
        """Connect to the MCP server."""
        self.connection = await websockets.connect(self.uri)
        asyncio.create_task(self._listen())

    async def _listen(self):
        """Listen for incoming messages and route responses."""
        try:
            async for message in self.connection:
                data = json.loads(message)
                msg_id = str(data.get("id"))

                if msg_id in self.pending_responses:
                    # Resolve the future waiting for this response
                    future = self.pending_responses.pop(msg_id)
                    if not future.done():
                        future.set_result(data)
                else:
                    # Unmatched message (not a tool response) → log gracefully
                    print(f"[MCPClient] Unhandled message: {data}")

        except websockets.ConnectionClosed:
            print("[MCPClient] Connection closed")

    async def _send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send payload and wait for response by id."""
        if not self.connection:
            raise RuntimeError("MCP client is not connected")

        self.message_id += 1
        msg_id = str(self.message_id)
        payload["id"] = msg_id

        future = asyncio.get_event_loop().create_future()
        self.pending_responses[msg_id] = future

        await self.connection.send(json.dumps(payload))
        return await future

    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call a tool exposed by the MCP server.
        arguments must be a dict (empty dict `{}` if no arguments).
        """
        payload = {
            "type": "call_tool",
            "tool": tool_name,
            "arguments": arguments or {}
        }
        response = await self._send(payload)

        if "error" in response:
            raise RuntimeError(f"Tool call failed: {response['error']}")
        return response.get("result", {})

    async def close(self):
        """Close the WebSocket connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None


async def main():
    client = MCPClient("ws://localhost:8000/mcp")
    await client.connect()

    try:
        # Example tool call with arguments
        result = await client.call_tool(
            "set_credentials",
            {
                "username": "demo",
                "password": "demo123",
                "api_key_name": "test",
                "api_key_value": "xyz",
                "login_url": "http://example.com/login"
            }
        )
        print("Tool response:", result)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
