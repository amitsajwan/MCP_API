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
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(()=>{ if(logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [messages]);

  const push = (role: ChatEntry['role'], content: string) => {
    setMessages(m => [...m, { id: Math.random().toString(36).slice(2), role, content, ts: new Date().toISOString() }]);
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
        <label><input type='checkbox' checked={assistantMode} onChange={e=>setAssistantMode(e.target.checked)} /> Assistant Mode</label>
        {assistantMode && (
          <label>Max Tools <input type='number' min={1} max={5} value={maxTools} onChange={e=>setMaxTools(Math.max(1, Math.min(5, parseInt(e.target.value)||1)))} /></label>
        )}
        <button onClick={()=>window.location.reload()} disabled={loading}>Reset</button>
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
