#!/usr/bin/env python3
import requests
import json

# Test the MCP client directly
from mcp_client import MCPClient

print("Testing MCP Client directly...")
client = MCPClient()
response = client.process_query("What is my cash balance?")
print(f"Response: {json.dumps(response, indent=2)}")
print(f"Summary: {response.get('summary', 'No summary')}")
print(f"Status: {response.get('status', 'No status')}")