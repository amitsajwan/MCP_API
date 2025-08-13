import React, { useState, useEffect, useRef } from 'react';
import { api } from '../util/api';
import './simple.css';

interface ChatEntry { id: string; role: 'user'|'assistant'|'system'; content: string; ts: string; }

export const SimpleChatApp: React.FC = () => {
  const [messages, setMessages] = useState<ChatEntry[]>([{
    id: 'welcome', role: 'system', ts: new Date().toISOString(),
    content: 'Hi, ask me about payments, transactions, or a cash summary. Example: "pending payments status=pending"'
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [assistantMode, setAssistantMode] = useState(true);
  const [maxTools, setMaxTools] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [prompts, setPrompts] = useState<{title:string;prompt:string;description?:string}[]>([]);
  const [showLogin, setShowLogin] = useState(false);
  const [loginData, setLoginData] = useState({username:'', password:'', base_url:'http://localhost:9001', environment:'DEV'});
  const [loginStatus, setLoginStatus] = useState<string>('');
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(()=>{ if(logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [messages]);
  useEffect(()=>{
    api.getMcpPrompts()
      .then(d=> setPrompts(d.prompts||[]))
      .catch(()=>{});
  },[]);

  const push = (role: ChatEntry['role'], content: string) => {
    setMessages((m: ChatEntry[]) => [...m, { id: Math.random().toString(36).slice(2), role, content, ts: new Date().toISOString() }]);
  };

  const send = async () => {
    const text = input.trim();
    if(!text || loading) return;
    setInput('');
    push('user', text);
    setLoading(true); setError(null);
    try {
      let resp: any;
      if(assistantMode) {
        resp = await api.assistantChat(text, { maxTools });
        const plan = resp.plan || resp.response || resp;
        push('assistant', JSON.stringify(plan, null, 2));
      } else {
        resp = await api.sendChat(text);
        push('assistant', JSON.stringify(resp, null, 2));
      }
    } catch(e:any){
      setError(e.message);
      push('assistant', 'Error: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if(e.key==='Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <div className="simple-shell">
      <header className="simple-header">API Chatbot <span className="mode-tag">{assistantMode ? 'Assistant' : 'Direct'}</span></header>
      <div className="controls">
  <label><input type='checkbox' checked={assistantMode} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setAssistantMode(e.target.checked)} /> Assistant Mode</label>
        {assistantMode && (
          <label>Max Tools <input type='number' min={1} max={5} value={maxTools} onChange={(e: React.ChangeEvent<HTMLInputElement>)=>setMaxTools(Math.max(1, Math.min(5, parseInt(e.target.value)||1)))} /></label>
        )}
  <button type='button' onClick={()=> setShowLogin((s: boolean)=>!s)} disabled={loading}>{showLogin ? 'Close Login' : 'Login'}</button>
        <button onClick={()=>window.location.reload()} disabled={loading}>Reset</button>
        <button disabled={loading} onClick={async ()=>{
          const base = input.trim() || 'pending payments summary';
          push('user', `[LLM PLAN] ${base}`);
          setLoading(true);
          try {
            const plan = await api.llmAgent(base, { maxSteps: 3, dryRun: true });
            push('assistant', JSON.stringify(plan, null, 2));
          } catch(e:any){
            push('assistant', 'LLM plan error: ' + e.message);
          } finally { setLoading(false);} 
        }}>LLM Plan</button>
      </div>
      {showLogin && (
        <div className="login-panel">
          <form onSubmit={async e=>{e.preventDefault(); setLoading(true); setLoginStatus(''); try { const res = await api.configure({...loginData}); setLoginStatus('Saved'); push('assistant', 'Configuration stored.'); } catch(err:any){ setLoginStatus(err.message); push('assistant', 'Login error: '+ err.message);} finally { setLoading(false);} }}>
            <div className="row">
              <label>Username <input value={loginData.username} onChange={e=>setLoginData(d=>({...d, username:e.target.value}))} /></label>
              <label>Password <input type='password' value={loginData.password} onChange={e=>setLoginData(d=>({...d, password:e.target.value}))} /></label>
              <label>Base URL <input value={loginData.base_url} onChange={e=>setLoginData(d=>({...d, base_url:e.target.value}))} /></label>
              <label>Env <input value={loginData.environment} onChange={e=>setLoginData(d=>({...d, environment:e.target.value}))} style={{width:'70px'}} /></label>
              <button type='submit' disabled={loading || !loginData.username}>Save</button>
            </div>
            {loginStatus && <div className="login-status">{loginStatus}</div>}
          </form>
        </div>
      )}
      <div className="prompt-bar">
        {prompts.slice(0,6).map((p: {title:string;prompt:string;description?:string})=> (
          <button key={p.title} title={p.description} onClick={()=> setInput(p.prompt)}>{p.title}</button>
        ))}
      </div>
      <div className="log" ref={logRef}>
        {messages.map(m => (
          <div key={m.id} className={`line ${m.role}`}>
            <div className="meta">{m.role}</div>
            <pre className="bubble">{m.content}</pre>
          </div>
        ))}
      </div>
      {error && <div className="error">{error}</div>}
      <div className="input-row">
        <input
          value={input}
            onChange={e=>setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder={assistantMode ? 'Ask about APIs (e.g. pending payments status=pending)' : 'Send message...'}
        />
        <button onClick={send} disabled={loading}>{loading ? '...' : 'Send'}</button>
      </div>
      <footer className="foot">Simple Chatbot • /assistant/chat {assistantMode ? 'enabled' : 'disabled'}</footer>
    </div>
  );
};

export default SimpleChatApp;
