"""Assistant core utilities (scoring, parsing, selection, synthesis).
Groq-only summarization with a simple fallback; no OpenAI/HF dependencies.
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
    """Summarize tool executions using Groq (if configured) or a concise heuristic fallback.

    Env vars:
        GROQ_API_KEY   - required to enable Groq summaries
        GROQ_MODEL     - optional, default 'llama-3.1-8b-instant'
    """
    if not executions:
        return "No tool executions were performed."

    import os, json as _json, requests

    tool_blocks: List[str] = []
    fallback_lines: List[str] = []
    for ex in executions:
        tool_name = ex.get('tool')
        if ex.get('status') != 'success':
            err = ex.get('error') or 'unknown error'
            hint = ex.get('hint')
            fallback_lines.append(f"{tool_name}: error {err}{(' (hint: '+hint+')') if hint else ''}")
            tool_blocks.append(f"Tool {tool_name} ERROR: {err}")
            continue
        result = ex.get('result')
        payload = result.get('response') if isinstance(result, dict) else result
        try:
            serialized = _json.dumps(payload, ensure_ascii=False)[:4000]
        except Exception:
            serialized = str(payload)[:4000]
        fallback_lines.append(f"{tool_name}: success")
        tool_blocks.append(f"Tool {tool_name} OUTPUT: {serialized}")

    prompt = (
        "You are an assistant summarizing financial API tool results. "
        "Produce a concise (<=120 words) factual summary highlighting balances, counts, statuses, totals. "
        "Do not invent fields. Merge overlapping info.\n\n" + "\n\n".join(tool_blocks)
    )
    # Groq path (OpenAI-compatible Chat Completions API)
    groq_key = os.environ.get('GROQ_API_KEY')
    if not groq_key:
        return "\n".join(fallback_lines)
    model = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {groq_key}',
        'Content-Type': 'application/json'
    }
    body = {
        'model': model,
        'messages': [
            {"role": "system", "content": "You convert raw JSON tool outputs into a factual concise summary."},
            {"role": "user", "content": prompt}
        ],
        'temperature': 0.2,
        'max_tokens': 300
    }
    try:
        r = requests.post(url, headers=headers, json=body, timeout=60)
        if r.status_code != 200:
            return "\n".join(fallback_lines + [f"(Groq summarization error {r.status_code})"])
        data = r.json()
        text = (data.get('choices') or [{}])[0].get('message', {}).get('content', '').strip()
        return text or "\n".join(fallback_lines)
    except Exception:
        return "\n".join(fallback_lines)
