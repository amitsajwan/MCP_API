from mcp.server.fastapi import FastAPIMCPServer
import os, json, yaml, logging
from login_flow import access_card_login, session, api_key_header_name, api_key_header_value, proxies
from token_cache import clear_token

logging.basicConfig(level=logging.INFO)
server = FastAPIMCPServer(name="multi-api-server")


@server.tool(name="login", description="Log in using access card. Cached token will be reused if valid.")
def login(load_balancer_url: str, login_alias: str, password: str):
    try:
        token = access_card_login(load_balancer_url, login_alias, password)
        return {"status": "success", "api_key_preview": token[:5] + "..."}
    except Exception as e:
        clear_token()
        return {"status": "error", "message": str(e)}

# rest of your register_tools_from_spec() remains same...
