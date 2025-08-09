import os
import sys
import logging
import requests
from fastmcp import FastMCP

# Send logs to stderr so MCP stdout is clean
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Config
LOGIN_URL = os.getenv("LOGIN_URL", "http://localhost:8081/api/v1/keylink/authentication/login")
USERNAME = os.getenv("USERNAME", "AmitS")
PASSWORD = os.getenv("PASSWORD", "mypassword")

# Global session
session = requests.Session()

# MCP Server
mcp = FastMCP(name="KeyLink API MCP", description="MCP server for KeyLink APIs")

@mcp.tool()
def login():
    """Log in with Basic Auth and store JSESSIONID cookie."""
    headers = {
        "Authorization": requests.auth._basic_auth_str(USERNAME, PASSWORD),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logging.info(f"Logging in to {LOGIN_URL} as {USERNAME}")
    resp = session.post(LOGIN_URL, headers=headers, verify=False)
    resp.raise_for_status()
    logging.info("Login successful.")
    return {"cookies": session.cookies.get_dict()}

@mcp.tool()
def get_banks(module: str):
    """Fetch banks by module using existing session."""
    url = f"http://localhost:8081/api/v1/keylink/banks?module={module}"
    logging.info(f"Fetching banks for module={module}")
    resp = session.get(url, verify=False)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    logging.info("✅ Starting MCP server...")
    mcp.run()
