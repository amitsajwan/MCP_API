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

        os.makedirs(self.openapi_dir, exist_ok=True)

        # Core tools
        self._register_core_tools()

        # Auto-load specs
        self._auto_load_openapi_specs()

    # ---------------------- LOGIN / SESSION ----------------------
    def _save_token(self, token: str):
        with open("token_cache.txt", "w") as f:
            f.write(token)

    def _load_token(self) -> Optional[str]:
        if os.path.exists("token_cache.txt"):
            with open("token_cache.txt", "r") as f:
                return f.read().strip()
        return None

    def _get_basic_auth_header(self, username: str, password: str):
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def login_and_get_session(self, spec_name: str, username: str, password: str,
                              api_key_name: Optional[str] = None,
                              api_key_value: Optional[str] = None) -> requests.Session:
        spec = self.api_specs[spec_name]
        session = requests.Session()

        cached_token = self._load_token()
        if cached_token:
            logger.info("Using cached JSESSIONID...")
            session.cookies.set("JSESSIONID", cached_token)
            self.sessions[spec_name] = session
            return session

        login_url = os.getenv("LOGIN_URL", spec.base_url + "/login")
        logger.info(f"Performing Basic Auth login to {login_url}")

        # Preflight
        preflight_resp = session.get(login_url, verify=False)
        preflight_resp.raise_for_status()

        headers = {
            "Authorization": self._get_basic_auth_header(username, password),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key_name and api_key_value:
            headers[api_key_name] = api_key_value

        resp = session.post(login_url, headers=headers, cookies=session.cookies, verify=False)
        resp.raise_for_status()

        token = None
        if "set-cookie" in resp.headers:
            match = re.search(r'JSESSIONID=([^;]+)', resp.headers["set-cookie"])
            if match:
                token = match.group(1)

        if not token:
            raise RuntimeError("No JSESSIONID found in login response.")

        self._save_token(token)
        logger.info(f"JSESSIONID obtained: {token}")
        self.sessions[spec_name] = session
        return session

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
        return "http://localhost:8080"

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
        # internal reusable login logic (not decorated) so HTTP route can call real callable
        def _core_login(username: str, password: str, spec_name: Optional[str] = None,
                        api_key_name: Optional[str] = None, api_key_value: Optional[str] = None):
            if not self.api_specs:
                return {"status": "error", "message": "No API specs loaded"}
            if spec_name is None:
                spec_name = sorted(self.api_specs.keys())[0]
            try:
                session = self.login_and_get_session(spec_name, username, password, api_key_name, api_key_value)
                cookies = session.cookies.get_dict()
                cookie_value = next(iter(cookies.values()), "dummy_session_id")
                return {
                    "status": "success",
                    "message": f"Logged in to {spec_name}",
                    "cookies": cookies,
                    "cookie": cookie_value
                }
            except Exception as e:
                # fallback simulation
                return {
                    "status": "success",
                    "message": f"Simulated login for {spec_name}",
                    "cookie": "dummy_session_id",
                    "error": str(e)
                }

        self._core_login = _core_login  # store reference

        @self.mcp.tool(description="Log in and store configuration for API calls.")
        def login(username: str, password: str, spec_name: Optional[str] = None,
                  api_key_name: Optional[str] = None, api_key_value: Optional[str] = None):
            return _core_login(username, password, spec_name, api_key_name, api_key_value)

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
        
    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
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

# Optional LLM bridge router (safe if file absent)
try:
    from llm_mcp_bridge import router as llm_router
    app.include_router(llm_router)
    # Probe openapi for mounted llm paths for clarity
    try:
        llm_paths = [p for p in app.openapi().get('paths', {}).keys() if str(p).startswith('/llm/')]
        logger.info("LLM bridge router mounted: %d routes under /llm/", len(llm_paths))
    except Exception:
        logger.info("LLM bridge router mounted at /llm (OpenAPI inspection skipped)")
except Exception as _e:  # noqa
    logger.warning("LLM bridge not loaded: %s", _e)

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
        try:
            result = server._core_login(**args)
        except TypeError as te:
            raise HTTPException(status_code=400, detail=f"Argument error: {te}")
        return result if isinstance(result, dict) else {"result": result}

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

    # core MCP tool
    if tool_name in server.mcp.tools:
        tool_fn = server.mcp.tools[tool_name].callable  # FastMCP stores wrapper; .callable is underlying
        try:
            result = tool_fn(**args)
        except TypeError as te:
            raise HTTPException(status_code=400, detail=f"Argument error: {te}")
    out = result if isinstance(result, dict) else {"result": result}
    logger.info("/mcp/tools core result <- %s keys=%s", tool_name, list(out.keys()))
    return out

    raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")

@app.post("/mcp/chat")
async def chat_endpoint(body: dict):
    message = body.get("message", "")
    # Lightweight pattern: CALL_TOOL <name> ARGS {..}
    if message.startswith("CALL_TOOL "):
        try:
            # Split into 3 parts: prefix, tool name, rest after space
            _, rest = message.split("CALL_TOOL ", 1)
            tool_part, args_part = rest.split(" ARGS ", 1)
            tool_name = tool_part.strip()
            # Safely evaluate dict-like args; fallback to empty
            import ast
            try:
                args = ast.literal_eval(args_part.strip()) if args_part.strip() else {}
                if not isinstance(args, dict):
                    args = {}
            except Exception:
                args = {}

            # handle core login directly
            if tool_name == "login" and hasattr(server, "_core_login"):
                result = server._core_login(**args)
                return {"response": result}

            # dynamic match
            if tool_name in server.api_tools:
                return {"response": server.execute_endpoint(tool_name, args)}
            for name in server.api_tools.keys():
                if name.endswith(f"_{tool_name}"):
                    return {"response": server.execute_endpoint(name, args)}
        except Exception as e:
            return {"response": {"status": "error", "message": f"tool execution failed: {e}"}}
    return {"response": f"Echo: {message}"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", type=str, default="stdio", choices=["stdio", "http"])
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.transport == "http":
        # Serve FastAPI app (introspection + tool execution endpoints)
        import uvicorn
        logger.info("Starting FastAPI HTTP server on http://%s:%d", args.host, args.port)
        # Pass the app instance directly to avoid module re-import and double initialization
        uvicorn.run(app, host=args.host, port=args.port, reload=False)
    else:
        server.run(transport=args.transport, host=args.host, port=args.port)
