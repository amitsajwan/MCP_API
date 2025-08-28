#!/usr/bin/env python3
"""
OpenAPI MCP Server
- Loads OpenAPI specs from ./openapi_specs
- Registers every API endpoint as an MCP tool
- Preserves login/session headers for subsequent calls
- Exposes FastAPI routes for introspection
"""

import os
import glob
import json
import yaml
import base64
import re
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from inspect import Signature, Parameter
import requests
from dataclasses import dataclass
from dotenv import load_dotenv
from fastmcp import FastMCP
# from openapi_spec_validator import validate_v3_spec, validate_v2_spec
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openapi_mcp_server")


@dataclass
class APISpec:
    name: str
    spec: Dict[str, Any]
    base_url: str
    file_path: Optional[str] = None


class APITool(BaseModel):
    name: str
    description: str
    method: str
    path: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    spec_name: str = ""
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    operation_id: Optional[str] = None


class OpenAPIMCPServer:
    def __init__(self, openapi_dir: str = "./openapi_specs"):
        self.mcp = FastMCP(name="OpenAPI MCP Server")
        self.openapi_dir = openapi_dir
        self.api_specs: Dict[str, APISpec] = {}
        self.api_tools: Dict[str, APITool] = {}
        self.sessions: Dict[str, requests.Session] = {}
        
        # Simple authentication - store credentials globally
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.api_key_name: Optional[str] = None
        self.api_key_value: Optional[str] = None
        self.login_url: Optional[str] = None

        os.makedirs(self.openapi_dir, exist_ok=True)

        # Core tools
        self._register_core_tools()

        # Auto-load specs
        self._auto_load_openapi_specs()

    # ---------------------- AUTHENTICATION MANAGEMENT ----------------------


    def set_credentials(self, username: str, password: str, 
                       api_key_name: Optional[str] = None, api_key_value: Optional[str] = None,
                       login_url: Optional[str] = None):
        """Set credentials for authentication."""
        self.username = username
        self.password = password
        self.api_key_name = api_key_name
        self.api_key_value = api_key_value
        self.login_url = login_url
        logger.info("Credentials set for authentication")

    def has_valid_session(self) -> bool:
        """Check if we have a valid session."""
        # Check if any session has a valid JSESSIONID
        for session in self.sessions.values():
            jsessionid = session.cookies.get("JSESSIONID")
            if jsessionid and jsessionid != "dummy_session_id":
                return True
        return False

    def ensure_authenticated(self) -> bool:
        """Ensure we have a valid session, auto-login if needed."""
        if self.has_valid_session():
            return True
        
        if not self.username or not self.password:
            logger.warning("No credentials set for authentication")
            return False
            
        try:
            # Use the login tool to authenticate
            login_result = self._perform_login()
            return login_result.get("status") == "success"
        except Exception as e:
            logger.error(f"Auto-login failed: {e}")
            return False

    def _save_token(self, token: str):
        with open("token_cache.txt", "w") as f:
            f.write(token)

    def _load_token(self) -> Optional[str]:
        if os.path.exists("token_cache.txt"):
            with open("token_cache.txt", "r") as f:
                return f.read().strip()
        return None

    def _clear_token(self):
        try:
            if os.path.exists("token_cache.txt"):
                os.remove("token_cache.txt")
        except Exception:
            pass

    def _get_basic_auth_header(self, username: str, password: str):
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _perform_login(self) -> Dict[str, Any]:
        """Perform login using Basic Auth and return session status."""
        cached_token = self._load_token()
        session = requests.Session()

        if cached_token:
            logger.info("✅ Using cached JSESSIONID")
            session.cookies.set("JSESSIONID", cached_token)
            # Set session for all specs
            for spec_name in self.api_specs.keys():
                self.sessions[spec_name] = session
            return {
                "status": "success",
                "message": "Using cached JSESSIONID.",
                "token": cached_token
            }

        if not self.username or not self.password:
            return {"status": "error", "message": "No credentials set. Use set_credentials first."}

        # Determine login URL
        login_url = self.login_url
        if not login_url:
            # Use first spec's base URL + /login
            if self.api_specs:
                first_spec = list(self.api_specs.values())[0]
                login_url = first_spec.base_url.rstrip('/') + '/login'
            else:
                return {"status": "error", "message": "No API specs loaded and no login URL set."}

        logger.info(f"🔐 Performing Basic Auth login to {login_url}...")

        headers = {
            "Authorization": self._get_basic_auth_header(self.username, self.password),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if self.api_key_name and self.api_key_value:
            headers[self.api_key_name] = self.api_key_value

        try:
            resp = session.post(login_url, headers=headers, cookies=session.cookies, verify=False)
            resp.raise_for_status()

            token = None
            if "set-cookie" in resp.headers:
                match = re.search(r'JSESSIONID=([^;]+)', resp.headers["set-cookie"])
                if match:
                    token = match.group(1)

            if not token:
                return {"status": "error", "message": "No JSESSIONID found in login response."}

            self._save_token(token)
            logger.info(f"✅ JSESSIONID obtained: {token}")
            
            # Set session for all specs
            for spec_name in self.api_specs.keys():
                self.sessions[spec_name] = session
                
            return {
                "status": "success",
                "message": "Login successful",
                "token": token
            }

        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return {"status": "error", "message": f"Login failed: {str(e)}"}



    # ---------------------- SPEC LOADING ----------------------
    def _validate_openapi_spec(self, spec: dict):
        """Placeholder for OpenAPI spec validation (currently disabled)."""
        return True

    def _extract_base_url(self, spec: Dict[str, Any]) -> str:
        if "servers" in spec and spec["servers"]:
            first = spec["servers"][0]
            if isinstance(first, dict) and "url" in first:
                return first["url"]
        if "host" in spec:  # Swagger 2
            scheme = "https" if "schemes" in spec and "https" in spec["schemes"] else "http"
            base_path = spec.get("basePath", "")
            return f"{scheme}://{spec['host']}{base_path}"
        return "http://localhost:9080"

    def _auto_load_openapi_specs(self):
        logger.info("Scanning for OpenAPI specs in %s", self.openapi_dir)
        patterns = ["*.yaml", "*.yml", "*.json"]
        openapi_files = []
        for pattern in patterns:
            openapi_files.extend(glob.glob(os.path.join(self.openapi_dir, pattern)))
            openapi_files.extend(glob.glob(os.path.join(self.openapi_dir, "**", pattern), recursive=True))

        if not openapi_files:
            logger.warning("No OpenAPI files found.")
            return

        for file_path in openapi_files:
            try:
                spec_name = Path(file_path).stem
                with open(file_path, "r", encoding="utf-8") as f:
                    spec = json.load(f) if file_path.endswith(".json") else yaml.safe_load(f)

                # self._validate_openapi_spec(spec)
                base_url = self._extract_base_url(spec)
                # Allow environment variable override for local mock usage.
                # FORCE_BASE_URL overrides all specs. FORCE_BASE_URL_<SPECNAME_UPPER> overrides by spec.
                override_global = os.getenv("FORCE_BASE_URL")
                override_spec = os.getenv(f"FORCE_BASE_URL_{spec_name.upper()}")
                mock_all = os.getenv("MOCK_ALL")
                mock_base = os.getenv("MOCK_API_BASE_URL", "http://localhost:9001").rstrip('/')
                if override_spec:
                    base_url = override_spec.rstrip('/'); logger.warning("Overriding base_url for %s -> %s", spec_name, base_url)
                elif override_global:
                    base_url = override_global.rstrip('/'); logger.warning("Overriding base_url (global) for %s -> %s", spec_name, base_url)
                elif mock_all:
                    base_url = mock_base; logger.warning("MOCK_ALL active: base_url for %s -> %s", spec_name, base_url)

                api_spec = APISpec(name=spec_name, spec=spec, base_url=base_url, file_path=file_path)
                self.api_specs[spec_name] = api_spec
                self.sessions[spec_name] = requests.Session()

                created = self._generate_tools_from_spec(api_spec)
                logger.info("Loaded spec %s (%d tools)", spec_name, created)
            except Exception as e:
                logger.error("Failed to load '%s': %s", file_path, e)

        logger.debug("Registered tools: %s", list(self.api_tools.keys()))

    # ---------------------- TOOL REGISTRATION ----------------------
    def execute_endpoint(self, endpoint_name: str, parameters: Dict[str, Any]):
        if endpoint_name not in self.api_tools:
            return {"status": "error", "message": f"Endpoint {endpoint_name} not found"}
        tool = self.api_tools[endpoint_name]
        spec = self.api_specs[tool.spec_name]
        session = self.sessions[tool.spec_name]

        url = f"{spec.base_url.rstrip('/')}{tool.path}"
        query_params, header_params, body_data = {}, {}, {}

        for name, value in parameters.items():
            param_info = tool.parameters.get(name)
            if not param_info:
                continue
            location = param_info.get("location")
            if location == "path":
                url = url.replace(f"{{{name}}}", str(value))
            elif location == "query":
                query_params[name] = value
            elif location == "header":
                header_params[name] = str(value)
            elif location == "body":
                body_data[name] = value

        # Ensure we have a valid session (auto-login if needed)
        if not self.ensure_authenticated():
            return {
                "status": "auth_required",
                "message": "Authentication required. Please set credentials and login first.",
                "hint": "Use set_credentials() then login()"
            }

        auto_mock = bool(os.getenv('AUTO_MOCK_FALLBACK'))
        mock_base = os.getenv('MOCK_API_BASE_URL', 'http://localhost:9001').rstrip('/')
        attempted_fallback = False
        try:
            logger.info("[API CALL] %s %s params=%s headers=%s bodyKeys=%s", tool.method, url, list(query_params.keys()), list(header_params.keys()), list(body_data.keys()))
            resp = session.request(tool.method, url, params=query_params, headers=header_params,
                                   json=body_data if body_data else None, verify=False, timeout=15)
        except Exception as e:  # network / DNS / TLS
            hint = None
            if 'api.company.com' in url and not os.getenv('FORCE_BASE_URL'):
                hint = "Set $env:FORCE_BASE_URL='http://localhost:9001' (PowerShell) before starting or set AUTO_MOCK_FALLBACK=1 for auto retry."
            # Optional automatic fallback
            if auto_mock and 'api.company.com' in url:
                attempted_fallback = True
                original = spec.base_url
                spec.base_url = mock_base
                new_url = f"{spec.base_url.rstrip('/')}{tool.path}"
                try:
                    logger.info("[API CALL:FALLBACK] %s %s", tool.method, new_url)
                    resp = session.request(tool.method, new_url, params=query_params, headers=header_params,
                                           json=body_data if body_data else None, verify=False, timeout=15)
                except Exception as e2:
                    return {"status": "error", "url": url, "message": f"Connection failed (and fallback failed): {e2}", "hint": hint}
            else:
                return {"status": "error", "url": url, "message": f"Connection failed: {e}", "hint": hint}

        # If unauthorized/forbidden, signal the agent to run the login tool
        if getattr(resp, 'status_code', None) in (401, 403):
            return {
                "status": "auth_required",
                "url": getattr(resp, 'url', url),
                "status_code": resp.status_code,
                "message": "Authentication required or session expired. Please run the 'login' tool or set a JSESSIONID via 'set_session_cookie'."
            }

        try:
            data = resp.json()
        except Exception:
            data = {"text": resp.text}
        result = {"status": "success", "url": resp.url, "status_code": resp.status_code, "response": data}
        try:
            preview = data if isinstance(data, (str, list)) else (list(data.keys()) if isinstance(data, dict) else str(type(data)))
            logger.info("[API RESP] %s -> %s keys=%s", resp.url, resp.status_code, preview if isinstance(preview, list) else None)
        except Exception:
            pass
        if attempted_fallback:
            result["note"] = "auto-mock-fallback"
            result["base_url"] = spec.base_url
        return result

    def _register_core_tools(self):



        @self.mcp.tool(description="Login using Basic Auth and return session status.")
        def login():
            return self._perform_login()

        @self.mcp.tool(description="Reload OpenAPI specifications from disk.")
        def reload_openapi_specs():
            self.api_specs.clear()
            self.api_tools.clear()
            self.sessions.clear()
            self._auto_load_openapi_specs()
            return {"status": "success", "message": "Reloaded specs"}

        @self.mcp.tool(description="List loaded OpenAPI spec names.")
        def list_loaded_specs():
            return {"status": "success", "specs": [
                {"name": spec.name, "base_url": spec.base_url} for spec in self.api_specs.values()
            ]}

        @self.mcp.tool(description="List all generated API endpoint tools.")
        def list_api_endpoints():
            # group by spec prefix
            grouped: Dict[str, list] = {}
            for name, tool in self.api_tools.items():
                grouped.setdefault(tool.spec_name, []).append(name)
            return {"status": "success", "count": len(self.api_tools), "grouped": grouped}



        @self.mcp.tool(description="Set credentials for authentication. Once set, use login() to authenticate.")
        def set_credentials(username: str, password: str, api_key_name: Optional[str] = None, 
                          api_key_value: Optional[str] = None, login_url: Optional[str] = None):
            self.set_credentials(username, password, api_key_name, api_key_value, login_url)
            return {
                "status": "success", 
                "message": "Credentials set. Use login() to authenticate.",
                "username": username
            }


    def _generate_tools_from_spec(self, api_spec: APISpec) -> int:
        spec = api_spec.spec
        tools_created = 0
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue

                operation_id = details.get("operationId")
                if operation_id:
                    tool_name = f"{api_spec.name}_{operation_id}"
                else:
                    clean = path.strip("/").replace("/", "_") \
                                .replace("{", "").replace("}", "") \
                                .replace("-", "_")
                    tool_name = f"{api_spec.name}_{method.lower()}_{clean or 'root'}"

                base_name = tool_name
                i = 1
                while tool_name in self.api_tools:
                    tool_name = f"{base_name}_{i}"
                    i += 1

                summary     = details.get("summary", "")
                description = details.get("description", "")
                tags        = details.get("tags", [])
                full_desc   = (summary + " - " + description).strip(" - ") or f"{method.upper()} {path}"
                full_desc += f" (Auto-authenticates with {api_spec.name} credentials)"

                parameters: Dict[str, Any] = {}
                for param in details.get("parameters", []):
                    pname  = param.get("name")
                    schema = param.get("schema", {}) or {}
                    if not pname:
                        continue
                    parameters[pname] = {
                        "type":        schema.get("type", "string"),
                        "description": param.get("description", ""),
                        "required":    param.get("required", False),
                        "location":    param.get("in", "query")
                    }

                if "requestBody" in details:
                    rb      = details["requestBody"]
                    content = rb.get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {}) or {}
                        if schema.get("type") == "object" and "properties" in schema:
                            for prop, prop_schema in schema["properties"].items():
                                parameters[prop] = {
                                    "type":        prop_schema.get("type", "string"),
                                    "description": prop_schema.get("description", ""),
                                    "required":    prop in schema.get("required", []),
                                    "location":    "body"
                                }

                self.api_tools[tool_name] = APITool(
                    name        = tool_name,
                    description = full_desc,
                    method      = method.upper(),
                    path        = path,
                    parameters  = parameters,
                    tags        = tags,
                    summary     = summary,
                    operation_id= operation_id,
                    spec_name   = api_spec.name
                )

                def make_runner(name: str, param_names: list):
                    def runner(**kwargs):
                        return self.execute_endpoint(name, kwargs)
                    sig_params = [Parameter(p, kind=Parameter.POSITIONAL_OR_KEYWORD) for p in param_names]
                    runner.__signature__ = Signature(sig_params)
                    runner.__name__ = f"{name}_runner"
                    return runner

                runner_fn = make_runner(tool_name, list(parameters.keys()))
                self.mcp.tool(name=tool_name, description=summary or full_desc)(runner_fn)
                tools_created += 1
        return tools_created
        
    def run(self, transport: str = "stdio", host: str = None, port: int = None):
        if host is None:
            host = os.getenv('MCP_HOST', '127.0.0.1')
        if port is None:
            port = int(os.getenv('MCP_PORT', '9000'))
        logger.info("Starting OpenAPI MCP Server")
        self.mcp.run(transport=transport)


# ---------------------- FastAPI Introspection ----------------------
app = FastAPI(title="OpenAPI MCP Server")

# Structured access logging middleware
@app.middleware("http")
async def access_log(request: Request, call_next):
    logger.info("HTTP %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception("Request failed: %s %s -> %s", request.method, request.url.path, e)
        raise
    logger.info("HTTP %s %s -> %s", request.method, request.url.path, getattr(response, 'status_code', '?'))
    return response
OPENAPI_DIR = os.getenv("OPENAPI_DIR", "./openapi_specs")
server = OpenAPIMCPServer(openapi_dir=OPENAPI_DIR)

# Pure MCP server - no LLM planning logic
logger.info("Pure MCP server running - tools only, no LLM planning")

@app.get("/mcp/tools")
async def list_tools():
    tool_map = await server.mcp.get_tools()
    seen = set()
    tools = []
    for name, tool in tool_map.items():
        base = name
        if re.search(r'_\d+$', name):
            base = re.sub(r'_\d+$', '', name)
            if base in seen:
                continue
        if base in seen:
            # already captured (canonical wins)
            continue
        seen.add(base)
        tools.append({"name": name, "description": tool.description})
    return {"tools": tools}

@app.get("/mcp/endpoints")
async def list_endpoints():
    return {"endpoints": list(server.api_tools.keys())}

@app.get("/mcp/prompts")
async def mcp_prompts():
    """Return simple prompt templates a client can show for quick starts."""
    tools = list(server.api_tools.values())
    examples = []
    for t in tools[:10]:
        param_keys = list(t.parameters.keys())[:2]
        arg_hint = " ".join(f"{k}=<value>" for k in param_keys)
        examples.append({
            "title": t.summary or t.name,
            "prompt": f"{t.name} {arg_hint}".strip(),
            "description": (t.description or '')[:120]
        })
    core = [
        {"title": "Pending Payments Summary", "prompt": "pending payments status=pending", "description": "Retrieve all pending payments."},
        {"title": "List Specs", "prompt": "list specs", "description": "List loaded API specs."},
        {"title": "Cash + Securities", "prompt": "cash summary and securities positions", "description": "Run multiple related tools."}
    ]
    return {"prompts": core + examples}

@app.get("/mcp/specs")
async def http_list_specs():
    """List loaded specs and their current base URLs."""
    return {
        "specs": [
            {"name": spec.name, "base_url": spec.base_url} for spec in server.api_specs.values()
        ]
    }

@app.post("/mcp/spec_base_url")
async def http_set_spec_base_url(body: dict):
    """Set base_url for a specific spec or all specs.
    Body: {"base_url": "http://...", "spec_name": "cash_api" | null}
    """
    base_url = (body or {}).get("base_url")
    spec_name = (body or {}).get("spec_name")
    if not base_url or not isinstance(base_url, str):
        raise HTTPException(status_code=400, detail="base_url required")
    base_url = base_url.rstrip('/')

    updated = []
    if spec_name:
        if spec_name not in server.api_specs:
            raise HTTPException(status_code=404, detail="Spec not found")
        server.api_specs[spec_name].base_url = base_url
        updated.append({"name": spec_name, "base_url": base_url})
    else:
        for name, spec in server.api_specs.items():
            spec.base_url = base_url
            updated.append({"name": name, "base_url": base_url})
    logger.info("Spec base_url updated -> %s", updated)
    return {"status": "success", "updated": updated}

@app.get("/mcp/tool_meta/{tool_name}")
async def tool_meta(tool_name: str):
    # direct match
    if tool_name in server.api_tools:
        t = server.api_tools[tool_name]
    else:
        # suffix alias resolution
        t = None
        for name in server.api_tools.keys():
            if name.endswith(f"_{tool_name}"):
                t = server.api_tools[name]
                break
        if t is None:
            raise HTTPException(status_code=404, detail="Tool not found")
    return {
        "name": t.name,
        "description": t.description,
        "method": t.method,
        "path": t.path,
        "spec_name": t.spec_name,
        "parameters": [
            {
                "name": pname,
                **pinfo
            } for pname, pinfo in t.parameters.items()
        ]
    }

@app.post("/mcp/tools/{tool_name}")
async def call_tool(tool_name: str, body: dict):
    args = body.get("arguments", {}) if body else {}
    logger.info("/mcp/tools call -> %s args=%s", tool_name, args)
    # explicit handling for core login tool via internal callable
    if tool_name == "login" and hasattr(server, "_core_login"):
        # Missing credentials: if we have a token/session, treat as already logged-in; else ask for creds
        if not args or not args.get("username") or not args.get("password"):
            token = server._load_token()
            if token:
                # ensure sessions carry the cookie
                for name, sess in server.sessions.items():
                    try:
                        if "JSESSIONID" not in sess.cookies.get_dict():
                            sess.cookies.set("JSESSIONID", token)
                    except Exception:
                        pass
                return {"status": "success", "message": "Already logged in (session cookie present)", "cookie": token}
            return {"status": "auth_required", "message": "Credentials required. Please provide username and password."}
        try:
            result = server._core_login(**args)
        except TypeError as te:
            return {"status": "auth_required", "message": f"Credentials required: {te}"}
        return result if isinstance(result, dict) else {"result": result}

    # Explicit handling for built-in server core tools without relying on FastMCP internals
    if tool_name == "reload_openapi_specs":
        server.api_specs.clear()
        server.api_tools.clear()
        server.sessions.clear()
        server._auto_load_openapi_specs()
        return {"status": "success", "message": "Reloaded specs"}
    if tool_name == "list_loaded_specs":
        return {"status": "success", "specs": [
            {"name": spec.name, "base_url": spec.base_url} for spec in server.api_specs.values()
        ]}
    if tool_name == "list_api_endpoints":
        grouped: Dict[str, list] = {}
        for name, t in server.api_tools.items():
            grouped.setdefault(t.spec_name, []).append(name)
        return {"status": "success", "count": len(server.api_tools), "grouped": grouped}

    # Session helpers
    if tool_name == "set_session_cookie" and hasattr(server, "_core_set_session"):
        try:
            result = server._core_set_session(args.get("spec_name"), args.get("jsessionid"))
        except TypeError as te:
            raise HTTPException(status_code=400, detail=f"Argument error: {te}")
        return result
    if tool_name == "clear_session_cookie" and hasattr(server, "_core_clear_session"):
        try:
            result = server._core_clear_session(args.get("spec_name"))
        except TypeError as te:
            raise HTTPException(status_code=400, detail=f"Argument error: {te}")
        return result

    # direct dynamic tool name
    if tool_name in server.api_tools:
        result = server.execute_endpoint(tool_name, args)
        logger.info("/mcp/tools result <- %s status=%s code=%s", tool_name, result.get('status'), result.get('status_code'))
        return result

    # allow alias without spec prefix e.g. 'get_banks' matching 'cash_api_get_banks'
    dynamic_match = None
    for name in server.api_tools.keys():
        if name.endswith(f"_{tool_name}"):
            dynamic_match = name
            break
    if dynamic_match:
        result = server.execute_endpoint(dynamic_match, args)
        logger.info("/mcp/tools result <- %s status=%s code=%s", dynamic_match, result.get('status'), result.get('status_code'))
        return result

    # Unknown tool
    raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")


## Note: Removed /mcp/chat for strict separation. Use /mcp/* endpoints from clients.

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", type=str, default="stdio", choices=["stdio", "http"])
    parser.add_argument("--host", type=str, default=os.getenv('MCP_HOST', '127.0.0.1'))
    parser.add_argument("--port", type=int, default=int(os.getenv('MCP_PORT', '9000')))
    args = parser.parse_args()
    if args.transport == "http":
        # Serve FastAPI app (introspection + tool execution endpoints)
        import uvicorn
        logger.info("Starting FastAPI HTTP server on http://%s:%d", args.host, args.port)
        # Pass the app instance directly to avoid module re-import and double initialization
        uvicorn.run(app, host=args.host, port=args.port, reload=False)
    else:
        server.run(transport=args.transport, host=args.host, port=args.port)
