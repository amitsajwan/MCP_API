#!/usr/bin/env python3
"""
MCP Client Launcher
Easy launcher for the MCP Tool Client with different modes.
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from mcp_tool_client import MCPToolClient

def main():
    """Main launcher function."""
    parser = argparse.ArgumentParser(description="MCP Tool Client Launcher")
    parser.add_argument("--mode", choices=["interactive", "web", "test", "example"], 
                       default="interactive", help="Mode to run the client in")
    parser.add_argument("--server", default="fastmcp_chatbot_server.py",
                       help="Server script to connect to")
    parser.add_argument("--args", nargs="*", default=["--transport", "stdio"],
                       help="Additional arguments for the server")
    parser.add_argument("--port", type=int, default=8000,
                       help="Port for web mode")
    parser.add_argument("--host", default="0.0.0.0",
                       help="Host for web mode")
    
    args = parser.parse_args()
    
    if args.mode == "interactive":
        run_interactive(args.server, args.args)
    elif args.mode == "web":
        run_web(args.server, args.args, args.host, args.port)
    elif args.mode == "test":
        run_tests()
    elif args.mode == "example":
        run_examples()

def run_interactive(server_script, server_args):
    """Run in interactive mode."""
    print("🚀 Starting MCP Tool Client in Interactive Mode")
    print(f"Server: {server_script}")
    print(f"Args: {' '.join(server_args)}")
    print()
    
    async def interactive():
        async with MCPToolClient(server_script, server_args) as client:
            await client.interactive_mode()
    
    asyncio.run(interactive())

def run_web(server_script, server_args, host, port):
    """Run in web mode."""
    print("🌐 Starting MCP Tool Client in Web Mode")
    print(f"Server: {server_script}")
    print(f"Args: {' '.join(server_args)}")
    print(f"Web interface: http://{host}:{port}")
    print()
    
    # Set environment variables for the web client
    os.environ["MCP_SERVER_SCRIPT"] = server_script
    os.environ["MCP_SERVER_ARGS"] = " ".join(server_args)
    
    import uvicorn
    from mcp_web_client import app
    uvicorn.run(app, host=host, port=port)

def run_tests():
    """Run test suite."""
    print("🧪 Running MCP Tool Client Tests")
    print()
    
    import subprocess
    result = subprocess.run([sys.executable, "test_mcp_client.py"], 
                          capture_output=False, text=True)
    return result.returncode

def run_examples():
    """Run example usage."""
    print("📚 Running MCP Tool Client Examples")
    print()
    
    import subprocess
    result = subprocess.run([sys.executable, "example_mcp_client_usage.py"], 
                          capture_output=False, text=True)
    return result.returncode

if __name__ == "__main__":
    main()