import logging
import requests
from fastmcp import FastMCP

# ===== CONFIG =====
USERNAME = "testuser"
PASSWORD = "testpass"
LOGIN_URL = "http://localhost:8081/api/v1/keylink/login"
BANKS_URL = "http://localhost:8081/api/v1/keylink/banks"
# ==================

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
session = requests.Session()

# MCP Server
mcp = FastMCP(name="KeyLink API MCP")

@mcp.tool()
def login():
    """Log in with Basic Auth and store JSESSIONID cookie."""
    headers = {
        "Authorization": requests.auth._basic_auth_str(USERNAME, PASSWORD),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logging.info(f"Logging in to {LOGIN_URL} as {USERNAME}...")
    resp = session.post(LOGIN_URL, headers=headers, verify=False)
    resp.raise_for_status()
    logging.info("Login successful.")
    return {"cookies": session.cookies.get_dict()}

@mcp.tool()
def get_banks(module: str):
    """Fetch banks by module using existing session."""
    url = f"{BANKS_URL}?module={module}"
    logging.info(f"Fetching banks for module={module}")
    resp = session.get(url, verify=False)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    logging.info("🚀 Starting MCP server on http://127.0.0.1:8000/mcp")
    mcp.run(transport="http", host="127.0.0.1", port=8000)
