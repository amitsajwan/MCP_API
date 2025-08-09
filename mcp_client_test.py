import asyncio
import json
import sys
from websockets import connect

# MCP WebSocket server URL (change to your backend's MCP route if needed)
MCP_URL = "ws://localhost:8000/mcp"  # example — replace if your server has a different path

async def test_mcp():
    async with connect(MCP_URL) as websocket:
        print("[Client] Connected to MCP server")

        # Send a request to list tools
        request = {
            "type": "list_tools",
            "id": "1",
            "params": {}
        }
        await websocket.send(json.dumps(request))
        print("[Client] Sent list_tools request")

        # Receive and print the response
        response = await websocket.recv()
        print("[Client] Response:", response)

        # OPTIONAL: Call a tool if it exists
        tools_data = json.loads(response)
        if "tools" in tools_data.get("result", {}):
            first_tool = tools_data["result"]["tools"][0]["name"]
            call_request = {
                "type": "call_tool",
                "id": "2",
                "params": {
                    "name": first_tool,
                    "arguments": {}
                }
            }
            await websocket.send(json.dumps(call_request))
            call_response = await websocket.recv()
            print("[Client] Tool Call Response:", call_response)

if __name__ == "__main__":
    asyncio.run(test_mcp())
