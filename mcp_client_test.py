import subprocess
import json
import sys

SERVER_CMD = [sys.executable, "server.py"]

proc = subprocess.Popen(
    SERVER_CMD,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

def send(req):
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()

def read():
    return json.loads(proc.stdout.readline())

# 1. Initialize handshake
send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
print("INIT RESP:", read())

# 2. List tools
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
tools_resp = read()
print("TOOLS:", tools_resp)

# Find the login tool name
tool_name = None
for t in tools_resp.get("result", {}).get("tools", []):
    if t["name"] == "login":
        tool_name = t["name"]
        break

if not tool_name:
    print("Login tool not found!")
    proc.terminate()
    sys.exit(1)

# 3. Call login tool
send({
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": tool_name,
        "arguments": {}  # if tool has params, pass them here
    }
})
print("LOGIN RESP:", read())

proc.terminate()
