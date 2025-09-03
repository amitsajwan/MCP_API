#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:9099/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            
            # Send a test message
            test_message = "What is my cash balance?"
            await websocket.send(test_message)
            print(f"Sent: {test_message}")
            
            # Wait for acknowledgment
            ack_response = await websocket.recv()
            print(f"Acknowledgment: {ack_response}")
            
            # Wait for actual response
            response = await websocket.recv()
            print(f"Response: {response}")
            
            # Try to parse as JSON
            try:
                response_data = json.loads(response)
                print(f"Parsed response: {json.dumps(response_data, indent=2)}")
            except json.JSONDecodeError:
                print(f"Response is not JSON: {response}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())