#!/usr/bin/env python3
"""
Test WebSocket communication with the chatbot app
"""

import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket communication with chatbot app."""
    uri = "ws://localhost:9099/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send a test message
            test_message = "Hello, can you show me my portfolio?"
            print(f"📤 Sending: {test_message}")
            await websocket.send(test_message)
            
            # Wait for multiple responses
            for i in range(3):  # Wait for up to 3 responses
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"📥 Received {i+1}: {response}")
                    
                    # Try to parse as JSON
                    try:
                        response_data = json.loads(response)
                        print(f"📋 Parsed response {i+1}: {json.dumps(response_data, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"📋 Raw response {i+1}: {response}")
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout waiting for response {i+1}")
                    break
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())