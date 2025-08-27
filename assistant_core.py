"""Assistant core utilities (scoring, parsing, selection, synthesis).
OpenAI summarization with a simple fallback; no Groq dependencies.
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Set

def tokenize(message: str) -> List[str]:
    return [t.lower().strip(',.!?') for t in message.split() if t]

def parse_inline_args(message: str) -> Dict[str, Any]:
    args: Dict[str, Any] = {}
    for part in message.split():
        if '=' in part:
            k, v = part.split('=', 1)
            k = k.strip().lower()
            v = v.strip().strip(',')
            if v.isdigit():
                args[k] = int(v)
            else:
                try:
                    args[k] = float(v)
                except ValueError:
                    args[k] = v
    return args

def score_tool(message_tokens: Set[str], tool_name: str, description: str) -> Tuple[float, Set[str]]:
    name_tokens = {t.lower() for t in tool_name.replace('_', ' ').split()}
    desc_tokens = {t.lower() for t in (description or '').replace('_', ' ').split()}
    all_tokens = name_tokens | desc_tokens
    overlap = message_tokens & all_tokens
    if not overlap:
        return 0.0, set()
    score = 0.0
    for tok in overlap:
        score += 1.5 if tok in name_tokens else 1.0
    score /= (len(all_tokens) ** 0.5 or 1)
    return score, overlap

def select_tools(scored: List[Dict[str, Any]], max_tools: int, message_tokens: Set[str]) -> List[str]:
    want_multi = any(t in message_tokens for t in {'all','both','summary'}) or max_tools > 1
    limit = max_tools if want_multi else 1
    return [c['tool'] for c in scored[: max(1, limit)]]

def synthesize_answer(executions: List[Dict[str, Any]]) -> str:
    """Summarize tool executions using OpenAI (if configured) or a richer heuristic fallback.

    - If AZURE_OPENAI_ENDPOINT is set, uses Azure OpenAI chat-completions to generate a concise summary.
    - Otherwise, produces natural text for known payload shapes (CashSummary, payments, transactions).

    Env vars:
        AZURE_OPENAI_ENDPOINT   - enable Azure OpenAI summaries when set
        AZURE_OPENAI_DEPLOYMENT - optional, default 'gpt-4'
    """
    if not executions:
        return "No tool executions were performed."

    import os, json as _json, requests

    def _fmt_num(x: Any) -> str:
        try:
            if isinstance(x, int):
                return f"{x:,}"
            if isinstance(x, float):
                # Trim trailing zeros
                s = f"{x:,.2f}"
                return s.rstrip('0').rstrip('.')
        except Exception:
            pass
        return str(x)

    # Build an OpenAI prompt and a generic fallback paragraph
    tool_blocks: List[str] = []
    generic_lines: List[str] = []
    for ex in executions:
        tool_name = ex.get('tool')
        # Ignore auth/session helper tools in summaries
        if str(tool_name).lower() in {"login", "set_session_cookie", "clear_session_cookie"}:
            continue
        if ex.get('status') != 'success':
            err = ex.get('error') or 'unknown error'
            hint = ex.get('hint')
            generic_lines.append(f"{tool_name}: error {err}{(' (hint: '+hint+')') if hint else ''}")
            tool_blocks.append(f"Tool {tool_name} ERROR: {err}")
            continue
        result = ex.get('result')
        payload = result.get('response') if isinstance(result, dict) else result
        # Generic success line (schema-agnostic)
        generic_lines.append(f"{tool_name}: done.")
        # For OpenAI prompt
        try:
            serialized = _json.dumps(payload, ensure_ascii=False)[:4000]
        except Exception:
            serialized = str(payload)[:4000]
        tool_blocks.append(f"Tool {tool_name} OUTPUT: {serialized}")

    # If no Azure OpenAI, either use heuristic fallback (default) or a minimal LLM-only mode (no shape logic)
    azure_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
    if not azure_endpoint:
        mode = (os.environ.get('SUMMARIZER_MODE') or 'llm_only').lower()
        if mode == 'llm_only':
            # Avoid any hard-coded schema logic; report tool-level completion/errors only
            return " ".join(s.strip() for s in generic_lines if s).strip()
        # Default hybrid: use generic lines (schema-agnostic)
        return " ".join(s.strip() for s in generic_lines if s).strip()

    # Azure OpenAI path
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI
    
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    deployment = os.environ.get('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')
    
    client = AzureOpenAI(
        api_version="2024-02-01",
        azure_endpoint=azure_endpoint,
        azure_ad_token_provider=token_provider,
    )
    prompt = (
        "You are a financial APIs helper. Summarize the tool results concisely (<=120 words), "
        "answering the user's request based only on these outputs. "
        "Do not invent fields or facts. Prefer balances, counts, statuses, totals if present. "
        "If the outputs are heterogeneous, provide a short, factual synthesis.\n\n" + "\n\n".join(tool_blocks)
    )
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a financial APIs assistant. Use only the provided tool outputs to answer the user's request concisely and factually."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=300
        )
        text = response.choices[0].message.content.strip() if response.choices else ''
        return text or " ".join(s.strip() for s in generic_lines if s).strip()
    except Exception:
        return " ".join(s.strip() for s in generic_lines if s).strip()
