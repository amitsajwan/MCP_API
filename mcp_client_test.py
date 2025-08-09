import subprocess
import json
import sys

# Path to your server script
SERVER_CMD = [sys.executable, "server.py"]

# Start the MCP server
proc = subprocess.Popen(
    SERVER_CMD,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Helper to send JSON-RPC request
def send_request(method, params=None, id=1):
    req = {
        "jsonrpc": "2.0",
        "id": id,
        "method": method
    }
    if params is not None:
        req["params"] = params
    msg = json.dumps(req) + "\n"
    proc.stdin.write(msg)
    proc.stdin.flush()

# Example: Call "login" tool
send_request("tools/call", {
    "name": "login",
    "arguments": {}
})

# Read one response line
print("Response from MCP server:")
print(proc.stdout.readline())

# Cleanup
proc.terminate()
