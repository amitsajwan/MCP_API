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
from openapi_mcp_server import server  # reuse existing singleton

logger = logging.getLogger("llm_mcp_bridge")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/llm", tags=["llm"])

# Debug snapshot of last agent invocation
LAST_LLM_DEBUG: dict | None = None

class LLMToolCall(BaseModel):
    tool: str
    arguments: Dict[str, Any] = {}

class LLMRouteRequest(BaseModel):
    message: str | None = None
    call: LLMToolCall | None = None

class LLMPlanStep(BaseModel):
    tool: str
    arguments: Dict[str, Any] = {}
    reason: Optional[str] = None

class LLMAgentRequest(BaseModel):
    message: str
    max_steps: int = 3
    dry_run: bool = False
    model: str | None = None  # optional override

class LLMAgentResponse(BaseModel):
    status: str
    plan: List[LLMPlanStep]
    executions: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None

@router.post("/route")
def llm_route(body: LLMRouteRequest):
    # If explicit tool call provided, execute directly
    if body.call:
        t = body.call.tool
        args = body.call.arguments or {}
        # mimic /mcp/tools/{tool}
        if t in server.api_tools:
            return {"status": "success", "result": server.execute_endpoint(t, args)}
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
            return {"status": "success", "intent": "list_tools", "grouped": grouped}
        return {"status": "echo", "message": body.message}
    return {"status": "no_action"}


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
    return steps[:1]

@router.post('/agent', response_model=LLMAgentResponse)
def llm_agent(req: LLMAgentRequest):
    """Experimental agent endpoint.
    Uses OpenAI (if OPENAI_API_KEY present) to plan tool steps; falls back to rule-based heuristic.
    """
    try:
        tool_names = list(server.api_tools.keys())
        executions: List[Dict[str, Any]] = []
        used_llm = False
        api_key = os.environ.get('OPENAI_API_KEY')
        debug: dict = {"message": req.message, "api_key_present": bool(api_key), "used_llm": False, "error": None}

        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                system_prompt = (
                    "You are a tool planner. Given user request and tool list, respond with JSON array of steps. "
                    "Each step: {tool, arguments, reason}. Only include tools that exist. Keep arguments simple."
                )
                tool_list_text = "\n".join(tool_names)
                content = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Tools:\n{tool_list_text}\n\nUser: {req.message}"}
                ]
                resp = client.chat.completions.create(model=req.model or 'gpt-4o-mini', messages=content, temperature=0)
                raw = resp.choices[0].message.content.strip()
                import json as _json
                try:
                    parsed = _json.loads(raw)
                    debug["raw_excerpt"] = raw[:400]
                    if isinstance(parsed, dict):
                        parsed = [parsed]
                    plan: List[LLMPlanStep] = []
                    for item in parsed:
                        t = item.get('tool')
                        if t in tool_names:
                            plan.append(LLMPlanStep(tool=t, arguments=item.get('arguments', {}), reason=item.get('reason')))
                    if not plan:
                        plan = _basic_intent_parse(req.message, tool_names)
                    used_llm = True
                    logger.info("[LLM] planning succeeded: steps=%d", len(plan))
                    debug["plan_len"] = len(plan)
                except Exception:
                    logger.warning("Failed to parse LLM response; falling back to rule-based planner.")
                    debug["parse_error"] = True
                    plan = _basic_intent_parse(req.message, tool_names)
            except Exception as e:
                logger.warning("LLM planning error: %s -- falling back to rule-based", e)
                debug["error"] = str(e)
                plan = _basic_intent_parse(req.message, tool_names)
        else:
            logger.info("No OPENAI_API_KEY present; using rule-based planning.")
            plan = _basic_intent_parse(req.message, tool_names)

        if not req.dry_run:
            for step in plan[: req.max_steps]:
                try:
                    result = server.execute_endpoint(step.tool, step.arguments)
                    executions.append({'tool': step.tool, 'status': 'success', 'result': result})
                except Exception as e:
                    executions.append({'tool': step.tool, 'status': 'error', 'error': str(e)})

        note = 'llm_plan' if used_llm else 'rule_based_plan'
        debug["used_llm"] = used_llm
        debug["plan_tools"] = [s.tool for s in plan]
        debug["note"] = note
        if not req.dry_run:
            debug["executions"] = [{"tool": e.get("tool"), "status": e.get("status")} for e in executions]
        global LAST_LLM_DEBUG
        LAST_LLM_DEBUG = debug
        return LLMAgentResponse(status='success', plan=plan, executions=None if req.dry_run else executions, notes=note)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get('/status')
def llm_status():
    """Report whether the OpenAI API key is detected and a count of tools."""
    api_key_present = bool(os.environ.get('OPENAI_API_KEY'))
    return {
        'openai_api_key_present': api_key_present,
        'tool_count': len(server.api_tools),
        'note': 'Set OPENAI_API_KEY before starting server to enable LLM planning.' if not api_key_present else 'LLM planning path available.'
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
