const BASE_URL = 'http://localhost:8080';

async function jsonFetch(path: string, init?: RequestInit) {
  const res = await fetch(BASE_URL + path, { headers: { 'Content-Type': 'application/json' }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// Exported low-level helpers for components needing direct calls
export async function fetchJSON(path: string, init?: RequestInit) {
  return jsonFetch(path, init);
}

export async function postJSON(path: string, body: any) {
  return jsonFetch(path, { method: 'POST', body: JSON.stringify(body) });
}

export const api = {
  async getTools(): Promise<string[]> {
    const data = await jsonFetch('/tools');
    // backend returns array of tool names or objects {name, description}
    if (Array.isArray(data) && data.length && typeof data[0] === 'string') return data;
    if (Array.isArray(data)) return data.map((t:any) => t.name || String(t));
    if (data.tools) return data.tools.map((t:any)=> t.name);
    return [];
  },
  async getQuickActions() { return jsonFetch('/quick_actions'); },
  async getToolMeta(name: string) { return jsonFetch(`/tool_meta/${name}`); },
  async runTool(tool: string, args: Record<string, any> = {}) { return jsonFetch('/run_tool', { method: 'POST', body: JSON.stringify({ tool_name: tool, arguments: args }) }); },
  async sendChat(message: string, sessionId = 'default') { return jsonFetch('/chat', { method: 'POST', body: JSON.stringify({ message, session_id: sessionId }) }); },
  async assistantChat(message: string, opts: {sessionId?:string; autoExecute?:boolean; maxTools?:number} = {}) {
    const body = {
      message,
      session_id: opts.sessionId || 'default',
      auto_execute: opts.autoExecute !== false,
      max_tools: opts.maxTools || 1
    };
    return jsonFetch('/assistant/chat', { method: 'POST', body: JSON.stringify(body) });
  },
  async getStatus() { return jsonFetch('/status'); },
  async getMcpPrompts() { return jsonFetch('/mcp/prompts'); },
  async configure(credentials: {username:string; password:string; base_url:string; environment?:string; session_id?:string}) {
    return jsonFetch('/configure', { method: 'POST', body: JSON.stringify(credentials) });
  },
  async llmAgent(message: string, opts: {dryRun?:boolean; maxSteps?:number; model?:string} = {}) {
    const body = {
      message,
      dry_run: !!opts.dryRun,
      max_steps: opts.maxSteps || 3,
      model: opts.model
    };
    return jsonFetch('/llm/agent', { method: 'POST', body: JSON.stringify(body) });
  },
  ws(sessionId='default') {
    const base = BASE_URL.replace('http','ws');
    return `${base}/ws/${sessionId}`;
  }
};
