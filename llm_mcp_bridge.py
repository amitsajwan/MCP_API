"""LLM MCP Bridge (Conceptual Stub)

Purpose:
  Provide a simple callable that an external LLM client (e.g. OpenAI Assistants, Claude, etc.)
  can invoke over HTTP to:
    1. List available MCP tools (already exposed at /mcp/tools)
    2. Execute a tool safely with arguments (POST /mcp/tools/{tool})
    3. Optionally transform natural language into a CALL_TOOL directive

This stub shows how you might wrap the existing openapi_mcp_server FastAPI app endpoints to
allow a generic LLM orchestrator to call a single /llm/route endpoint with a JSON envelope.

Extend this with auth (API keys / JWT) and rate limiting before production use.
"""
from fastapi import APIRouter, HTTPException
import logging
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
# from openapi_mcp_server import server  # reuse existing singleton

logger = logging.getLogger("llm_mcp_bridge")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/llm", tags=["llm"])
logger.info("LLM bridge module imported; router ready at prefix /llm")

# Debug snapshot of last agent invocation
LAST_LLM_DEBUG: Optional[dict] = None

class LLMToolCall(BaseModel):
    tool: str
    arguments: Dict[str, Any] = {}

class LLMRouteRequest(BaseModel):
    message: Optional[str] = None
    call: Optional[LLMToolCall] = None

class LLMPlanStep(BaseModel):
    tool: str
    arguments: Dict[str, Any] = {}
    reason: Optional[str] = None

class LLMAgentRequest(BaseModel):
    message: str
    max_steps: int = 3
    dry_run: bool = False
    model: Optional[str] = None  # optional override

class LLMAgentResponse(BaseModel):
    status: str
    plan: List[LLMPlanStep]
    executions: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    # Simple, direct fields for easy client consumption
    agent_note: Optional[str] = None
    selected: Optional[List[str]] = None
    arguments: Optional[Dict[str, Dict[str, Any]]] = None
    executed: Optional[bool] = None
    results: Optional[Dict[str, Any]] = None
    answer: Optional[str] = None

def _get_value_at_path(obj: Any, path: str) -> Any:
    """Walk obj by dot-path; supports dict keys and list indices."""
    cur = obj
    for part in path.split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            try:
                idx = int(part)
                if isinstance(cur, list) and 0 <= idx < len(cur):
                    cur = cur[idx]
                else:
                    return None
            except ValueError:
                return None
    return cur

def _resolve_placeholders(value: Any, ctx: Dict[str, Any]) -> Any:
    """Replace strings like ${TOOL.key.path} with values from ctx[TOOL]."""
    if isinstance(value, str):
        if value.startswith('${') and value.endswith('}'):
            inner = value[2:-1].strip()
            if '.' in inner:
                tool, path = inner.split('.', 1)
                base = ctx.get(tool)
                if base is not None:
                    got = _get_value_at_path(base, path)
                    return got if got is not None else value
    elif isinstance(value, dict):
        return {k: _resolve_placeholders(v, ctx) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_placeholders(v, ctx) for v in value]
    return value


def _strip_code_fences(text: str) -> str:
    """Remove common markdown code fences like ```json ... ``` or ``` ... ```."""
    if not text:
        return text
    t = text.strip()
    if t.startswith("```"):
        # drop first line fence and last fence if present
        lines = t.splitlines()
        if lines:
            # remove first fence line
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return t

def _extract_json_payload(text: str):
    """Best-effort: try full text, then fenced block, then bracket slicing."""
    import json as _json
    t = text.strip()
    # try raw
    try:
        return _json.loads(t)
    except Exception:
        pass
    # try stripped fences
    try:
        t2 = _strip_code_fences(t)
        if t2 and t2 != t:
            return _json.loads(t2)
    except Exception:
        pass
    # try slice from first '['..last ']' or first '{'..last '}'
    lbi, rbi = t.find('['), t.rfind(']')
    if lbi != -1 and rbi != -1 and rbi > lbi:
        frag = t[lbi:rbi+1]
        try:
            return _json.loads(frag)
        except Exception:
            pass
    lci, rci = t.find('{'), t.rfind('}')
    if lci != -1 and rci != -1 and rci > lci:
        frag = t[lci:rci+1]
        try:
            return _json.loads(frag)
        except Exception:
            pass
    raise ValueError("No JSON payload found in LLM response")

def _coerce_args_to_dict(args: Any) -> Dict[str, Any]:
    """Ensure arguments is a dict; convert common list encodings to dict."""
    if isinstance(args, dict):
        return args
    out: Dict[str, Any] = {}
    if isinstance(args, list):
        for item in args:
            if isinstance(item, dict):
                # support {key:..., value:...} or {name:..., value:...}
                key = item.get('key') or item.get('name') or item.get('param')
                if key is not None and 'value' in item:
                    out[str(key)] = item.get('value')
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                k, v = item
                out[str(k)] = v
    # fallback empty if nothing parsed
    return out

def _groq_chat(messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
    """Single place to call Groq chat completions and return the assistant text."""
    from groq import Groq
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    client = Groq(api_key=api_key)
    selected_model = model or os.environ.get('GROQ_MODEL') or 'llama-3.1-8b-instant'
    resp = client.chat.completions.create(model=selected_model, messages=messages, temperature=0)
    content = (resp.choices[0].message.content or '').strip()
    return content

def _summarize_executions_with_groq(executions: List[Dict[str, Any]], model: Optional[str] = None) -> Optional[str]:
    """Summarize tool executions with a concise, generic financial helper prompt. Returns None if Groq unavailable."""
    import os, json as _json
    if not executions:
        return None
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return None
    tool_blocks: List[str] = []
    for ex in executions:
        t = ex.get('tool'); status = ex.get('status')
        if str(t).lower() in {"login","set_session_cookie","clear_session_cookie"}:
            continue
        if status != 'success':
            err = ex.get('error') or 'unknown error'
            tool_blocks.append(f"Tool {t} ERROR: {err}")
        else:
            res = ex.get('result'); payload = res.get('response') if isinstance(res, dict) else res
            try:
                serialized = _json.dumps(payload, ensure_ascii=False)[:4000]
            except Exception:
                serialized = str(payload)[:4000]
            tool_blocks.append(f"Tool {t} OUTPUT: {serialized}")
    if not tool_blocks:
        return None
    sys = "You are a financial APIs assistant. Use only the provided tool outputs to answer the user's request concisely and factually."
    usr = (
        "You are a financial APIs helper. Summarize the tool results concisely (<=120 words), "
        "answering the user's request based only on these outputs. Do not invent fields or facts. "
        "Prefer balances, counts, statuses, totals if present. If outputs are heterogeneous, provide a short, factual synthesis.\n\n"
        + "\n\n".join(tool_blocks)
    )
    try:
        return _groq_chat([
            {"role": "system", "content": sys},
            {"role": "user", "content": usr}
        ], model=model)
    except Exception:
        return None

@router.post("/route")
def llm_route(body: LLMRouteRequest):
    from openapi_mcp_server import server
    logger.info("/llm/route called message_empty=%s call=%s", not bool(body.message), bool(body.call))
    # If explicit tool call provided, execute directly
    if body.call:
        t = body.call.tool
        args = body.call.arguments or {}
        # mimic /mcp/tools/{tool}
        if t in server.api_tools:
            res = server.execute_endpoint(t, args)
            logger.info("/llm/route exec %s -> %s", t, res.get('status'))
            return {"status": "success", "result": res}
        # suffix alias
        for name in server.api_tools:
            if name.endswith(f"_{t}"):
                return {"status": "success", "result": server.execute_endpoint(name, args)}
        raise HTTPException(404, f"Tool {t} not found")

    # If natural language message: naive heuristic -> list endpoints if user asks
    if body.message:
        lower = body.message.lower()
        if any(k in lower for k in ("what tools", "list tools", "available endpoints", "list endpoints")):
            grouped = {}
            for name, tool in server.api_tools.items():
                grouped.setdefault(tool.spec_name, []).append(name)
            logger.info("/llm/route intent=list_tools")
            return {"status": "success", "intent": "list_tools", "grouped": grouped}
    logger.info("/llm/route echo")
    return {"status": "echo", "message": body.message}


def _basic_intent_parse(message: str, tool_names: List[str]) -> List[LLMPlanStep]:
    """Fallback rule-based intent to tool mapping (no external LLM)."""
    m = message.lower()
    steps: List[LLMPlanStep] = []
    # simple keyword mapping
    intents = [
        ("pending payments", ["status", "pending"], "payments"),
        ("payments", [], "payments"),
        ("transactions", [], "transactions"),
        ("summary", [], "summary"),
    ]
    for phrase, kv, key in intents:
        if phrase in m:
            # pick first tool containing key tokens
            for tn in tool_names:
                if key in tn.lower():
                    args = {}
                    if kv:
                        # e.g. ['status','pending'] -> {'status':'pending'}
                        for i in range(0, len(kv), 2):
                            if i+1 < len(kv):
                                args[kv[i]] = kv[i+1]
                    # implicit inference: if user says 'pending' and no status arg, set status=pending
                    if 'pending' in m and 'status' not in args:
                        args['status'] = 'pending'
                    steps.append(LLMPlanStep(tool=tn, arguments=args, reason=f"Matched phrase '{phrase}'"))
                    break
    if not steps and tool_names:
        # default fallback: first tool
        steps.append(LLMPlanStep(tool=tool_names[0], reason="Default first tool fallback"))
    # Return all matched steps in order; caller will cap to max_steps
    return steps

def _generate_plan_summary(plan: List[LLMPlanStep], user_message: str) -> str:
    """Generate a human-readable summary of the execution plan."""
    if not plan:
        return "No execution steps planned."
    
    summary_parts = [f"**Execution Plan for:** {user_message}\n"]
    
    for i, step in enumerate(plan, 1):
        tool_name = step.tool.replace('cash_api_', '').replace('_', ' ').title()
        reason = step.reason or f"Execute {tool_name}"
        args_str = ""
        if step.arguments:
            key_args = [f"{k}={v}" for k, v in step.arguments.items() if v]
            if key_args:
                args_str = f" (with {', '.join(key_args)})"
        
        summary_parts.append(f"**Step {i}:** {reason}{args_str}")
        summary_parts.append(f"   - API Call: `{step.tool}`")
        if step.arguments:
            summary_parts.append(f"   - Parameters: {step.arguments}")
        summary_parts.append("")
    
    summary_parts.append("**Expected Flow:**")
    if len(plan) == 1:
        summary_parts.append("- Single API call to retrieve requested data")
    else:
        summary_parts.append("- Sequential execution with data chaining between steps")
        summary_parts.append("- Each step builds upon previous results")
    
    return "\n".join(summary_parts)

class LLMPlanRequest(BaseModel):
    message: str
    max_steps: int = 3
    model: Optional[str] = None

class LLMPlanResponse(BaseModel):
    status: str
    plan: List[LLMPlanStep]
    plan_summary: str
    estimated_execution_time: Optional[str] = None
    data_sources: List[str] = []
    expected_outputs: List[str] = []
    notes: Optional[str] = None

@router.post('/agent', response_model=LLMAgentResponse)
def llm_agent(req: LLMAgentRequest):
    from openapi_mcp_server import server
    """Experimental agent endpoint using Groq only for planning (fallback to rule-based)."""
    try:
        tool_names = list(server.api_tools.keys())
        if not tool_names:
            return LLMAgentResponse(
                status='success',
                plan=[],
                notes='no_tools_available',
                answer='No tools are currently available. Please check if OpenAPI specs are loaded.'
            )
            
        executions: List[Dict[str, Any]] = []
        used_llm = False
        debug: dict = {"message": str(req.message), "provider": "groq", "used_llm": False, "error": None}

        # Build a compact tool catalog (name, description, parameters)
        catalog_lines: List[str] = []
        for name in tool_names:
            t = server.api_tools.get(name)
            if not t:
                continue
            params = []
            for p, info in (t.parameters or {}).items():
                req_param = 'required' if info.get('required') else 'optional'
                ptype = info.get('type') or 'string'
                params.append(f"{p}:{ptype}({req_param})")
            ptxt = ", ".join(params)
            desc = (t.summary or t.description or '').strip()
            catalog_lines.append(f"- {name}: {desc}{(' | params: '+ptxt) if ptxt else ''}")
        tool_catalog = "\n".join(catalog_lines)

        system_prompt = (
            "You are a financial APIs assistant and tool planner.\n"
            "Goal: solve the user's request by selecting and ordering tool calls.\n"
            "Output a JSON array of steps. Each step: {tool, arguments, reason}.\n"
            "Rules:\n"
            "- Use only the listed tools. Prefer minimal steps (<= max_steps).\n"
            "- Fill arguments from the user's message; if a value depends on earlier output, use a placeholder ${TOOL.key.path}.\n"
            "- If authentication is needed, include a 'login' step first (with placeholders if credentials are unknown), or use 'set_session_cookie' if a JSESSIONID is available.\n"
            "- Do not invent fields or tools. If critical required fields are missing, proceed with placeholders and explain in 'reason'.\n"
            "- Keep arguments simple (strings/numbers/booleans)."
        )
        content = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Available tools:\n{tool_catalog}\n\nUser request: {req.message}\nReturn: JSON array of steps."}
        ]

        try:
            # Check if GROQ_API_KEY is available
            import os
            if not os.environ.get('GROQ_API_KEY'):
                logger.warning("GROQ_API_KEY not set, falling back to rule-based parsing")
                raise RuntimeError("GROQ_API_KEY not configured")
                
            raw = _groq_chat(content, model=req.model)
            parsed = _extract_json_payload(raw)
            if isinstance(parsed, dict):
                parsed = [parsed]
            plan: List[LLMPlanStep] = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                t = item.get('tool')
                if t and t in tool_names:
                    args = _coerce_args_to_dict(item.get('arguments', {}))
                    plan.append(LLMPlanStep(tool=t, arguments=args, reason=item.get('reason')))
            if not plan:
                plan = _basic_intent_parse(req.message, tool_names)
            used_llm = True
            logger.info("[LLM] Groq planning steps=%d", len(plan))
            debug["plan_len"] = len(plan)
        except Exception as e:
            logger.warning("Groq planning error: %s -- falling back to rule-based", e)
            debug["error"] = str(e)
            try:
                plan = _basic_intent_parse(req.message, tool_names)
            except Exception as fallback_error:
                logger.error("Fallback rule-based parsing failed: %s", fallback_error)
                raise HTTPException(500, f"Both LLM and rule-based parsing failed: {fallback_error}")

        selected = [s.tool for s in plan]
        argmap: Dict[str, Dict[str, Any]] = {s.tool: s.arguments for s in plan}
        results_map: Dict[str, Any] = {}

        if not req.dry_run:
            for idx, step in enumerate(plan[: req.max_steps]):
                try:
                    # Resolve placeholders from previously collected results_map
                    resolved_args = _resolve_placeholders(step.arguments or {}, results_map)
                    # Handle core tools explicitly; else execute API endpoint tool
                    if step.tool == 'login' and hasattr(server, '_core_login'):
                        result = server._core_login(**resolved_args)
                    elif step.tool == 'set_session_cookie' and hasattr(server, '_core_set_session'):
                        # expects jsessionid and optional spec_name
                        result = server._core_set_session(resolved_args.get('spec_name'), resolved_args.get('jsessionid'))
                    elif step.tool == 'clear_session_cookie' and hasattr(server, '_core_clear_session'):
                        result = server._core_clear_session(resolved_args.get('spec_name'))
                    else:
                        result = server.execute_endpoint(step.tool, resolved_args)
                    executions.append({'tool': step.tool, 'status': 'success', 'result': result})
                    if isinstance(result, dict) and 'response' in result:
                        results_map[step.tool] = result['response']
                    else:
                        results_map[step.tool] = result
                except Exception as e:
                    executions.append({'tool': step.tool, 'status': 'error', 'error': str(e)})
                    results_map[step.tool] = {'status': 'error', 'error': str(e)}
        # Optional final answer via Groq summarization
        answer_text: Optional[str] = None
        if not req.dry_run:
            answer_text = _summarize_executions_with_groq(executions, model=req.model)

        note = 'llm_plan' if used_llm else 'rule_based_plan'
        debug["used_llm"] = used_llm
        debug["plan_tools"] = [s.tool for s in plan]
        debug["note"] = note
        if not req.dry_run:
            debug["executions"] = [{"tool": e.get("tool"), "status": e.get("status")} for e in executions]
        global LAST_LLM_DEBUG
        LAST_LLM_DEBUG = debug
        logger.info("/llm/agent selected=%s executed=%s", selected, not req.dry_run)
        return LLMAgentResponse(
            status='success',
            plan=plan,
            executions=None if req.dry_run else executions,
            notes=note,
            agent_note=note,
            selected=selected,
            arguments=argmap,
            executed=(not req.dry_run),
            results=None if req.dry_run else results_map,
            answer=answer_text,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get('/status')
def llm_status():
    """Report Groq availability, selected model, and tool count."""
    groq_present = bool(os.environ.get('GROQ_API_KEY'))
    model = os.environ.get('GROQ_MODEL') or 'llama-3.1-8b-instant'
    return {
        'provider': 'groq',
        'groq_api_key_present': groq_present,
        'model': model,
        'tool_count': len(server.api_tools),
        'note': 'Set GROQ_API_KEY and optionally GROQ_MODEL. Agent uses Groq only; OpenAI is ignored.'
    }

@router.get('/debug')
def llm_debug():
    """Return the last LLM agent debug snapshot (or placeholder if none)."""
    global LAST_LLM_DEBUG
    return LAST_LLM_DEBUG or {"status": "no_invocation"}

# To integrate, in openapi_mcp_server.py after FastAPI app definition:
#   from llm_mcp_bridge import router as llm_router
#   app.include_router(llm_router)
# (We avoid editing again automatically to keep patch minimal.)
