"""Assistant core utilities (scoring, parsing, selection, synthesis).
Kept deliberately small & dependency-free.
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
    if not executions:
        return "No tool executions were performed."
    lines = []
    aggregate = []
    for ex in executions:
        tool = ex.get('tool')
        if ex.get('status') != 'success':
            lines.append(f"{tool}: error {ex.get('error')}")
            continue
        res = ex.get('result')
        payload = res.get('response') if isinstance(res, dict) else res
        count = None
        if isinstance(payload, list):
            count = (len(payload), 'items')
        elif isinstance(payload, dict):
            best_key, best_len = None, -1
            for k,v in payload.items():
                if isinstance(v, list) and len(v) > best_len:
                    best_key, best_len = k, len(v)
            if best_key is not None:
                count = (best_len, best_key)
        if count:
            n, label = count
            aggregate.append((tool, n))
            lines.append(f"{tool}: {n} {label}")
        else:
            lines.append(f"{tool}: succeeded")
    if not aggregate:
        return "; ".join(lines)
    total = sum(n for _, n in aggregate)
    parts = [f"{n} from {t}" for t, n in aggregate]
    return "; ".join(lines) + f". Total items: {total} (" + ", ".join(parts) + ")"
