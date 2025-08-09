import os
import logging
import requests
from mcp.server.fastapi import FastAPIMCPServer

# ----------------------------
# Configuration
# ----------------------------
LOGIN_URL = os.getenv(
    "LOGIN_URL",
    "http://localhost:8080/app/FA7/1/v1/s2s/keylink/authentication/login"
)

USERNAME = os.getenv("USER_NAME", "AmitS")
PASSWORD = os.getenv("PASSWORD", "mypassword")

# Optional API key headers
API_KEY_HEADER_NAME = os.getenv("API_KEY_HEADER_NAME", "")
API_KEY_HEADER_VALUE = os.getenv("API_KEY_HEADER_VALUE", "")

logging.basicConfig(level=logging.INFO)

# Shared session
session = requests.Session()

# ----------------------------
# MCP Server Initialization
# ----------------------------
server = FastAPIMCPServer(name="KeyLink API MCP")

# ----------------------------
# Login Tool
# ----------------------------
@server.tool(
    name="login",
    description="Log in using Basic Auth, stores session cookies for future API calls."
)
def login_tool(username: str = USERNAME, password: str = PASSWORD):
    try:
        logging.info("Performing Basic Auth login...")
        headers = {
            "Authorization": requests.auth._basic_auth_str(username, password),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if API_KEY_HEADER_NAME and API_KEY_HEADER_VALUE:
            headers[API_KEY_HEADER_NAME] = API_KEY_HEADER_VALUE

        resp = session.post(LOGIN_URL, headers=headers, verify=False)
        resp.raise_for_status()
        logging.info("Login successful.")
        return {"status": "success", "cookies": session.cookies.get_dict()}
    except Exception as e:
        logging.error(f"Login failed: {e}")
        return {"status": "error", "message": str(e)}

# ----------------------------
# Example API Tool
# ----------------------------
@server.tool(
    name="get_banks",
    description="Fetch banks by module. Requires login first."
)
def get_banks(module: str):
    try:
        url = f"http://localhost:8080/app/FA7/1/v1/s2s/keylink/banks?module={module}"
        resp = session.get(url, verify=False)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------------------
# Run MCP Server
# ----------------------------
if __name__ == "__main__":
    server.run()
