import logging
import requests
from fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)

USERNAME = "myuser"
PASSWORD = "mypass"
LOGIN_URL = "http://localhost:8081/api/v1/employee/login"

session = requests.Session()

mcp = FastMCP(name="employee API MCP")

@mcp.tool(description="Log in to employee API using Basic Auth and return session cookies")
def login():
    headers = {
        "Authorization": requests.auth._basic_auth_str(USERNAME, PASSWORD),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    logging.info(f"Logging in as {USERNAME}")
    resp = session.post(LOGIN_URL, headers=headers, verify=False)
    resp.raise_for_status()
    return {"cookies": session.cookies.get_dict()}

@mcp.tool(
    description="Fetch banks for a given module ID",
    parameters={
        "module": {
            "type": "string",
            "description": "Module ID to fetch banks for"
        }
    }
)
def get_banks(module: str):
    url = f"http://localhost:8081/api/v1/employee/banks?module={module}"
    resp = session.get(url, verify=False)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    logging.info("🚀 Starting MCP server...")
    mcp.run(transport="http")
