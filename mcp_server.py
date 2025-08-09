from fastmcp import FastMCP
import requests
import logging
import os

logging.basicConfig(level=logging.INFO)

LOGIN_URL = os.getenv(
    "LOGIN_URL",
    "http://localhost:8080/app/FA7/1/v1/s2s/keylink/authentication/login"
)
USERNAME = os.getenv("USERNAME", "AmitS")
PASSWORD = os.getenv("PASSWORD", "mypassword")

session = requests.Session()
mcp = FastMCP(name="KeyLink API MCP")

@mcp.tool
def login():
    """Log in with Basic Auth and store JSESSIONID cookie."""
    headers = {
        "Authorization": requests.auth._basic_auth_str(USERNAME, PASSWORD),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    resp = session.post(LOGIN_URL, headers=headers, verify=False)
    resp.raise_for_status()
    logging.info("Login successful.")
    return {"cookies": session.cookies.get_dict()}

@mcp.tool
def get_banks(module: str):
    """Fetch banks by module using existing session."""
    url = f"http://localhost:8080/app/FA7/1/v1/s2s/keylink/banks?module={module}"
    resp = session.get(url, verify=False)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    mcp.run()
