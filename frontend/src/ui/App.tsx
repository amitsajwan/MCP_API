import React, { useEffect, useState } from 'react';
import { ToolList } from './ToolList';
import ToolExecutor from './ToolExecutor';
import { ChatPanel } from './ChatPanel';
import WebSocketChat from './WebSocketChat';
import CredentialsPanel from './CredentialsPanel';
import { StatusBar } from './StatusBar';
import { QuickActions } from './QuickActions';
import { api } from '../util/api';

export const App: React.FC = () => {
  const [tools, setTools] = useState<string[]>([]);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTools = async () => {
    setLoading(true);
    try {
      const data = await api.getTools();
      setTools(data);
      setError(null);
    } catch (e:any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTools(); }, []);

  const [chatMode, setChatMode] = useState<'http'|'ws'>('http');

  return (
    <div style={{display:'flex', flexDirection:'column', minHeight:'100vh', fontFamily:'system-ui, sans-serif'}}>
      <header style={{padding:'0.75rem 1rem', borderBottom:'1px solid #ddd', display:'flex', justifyContent:'space-between'}}>
        <h1 style={{margin:0, fontSize:'1.25rem'}}>MCP Console</h1>
        <button onClick={loadTools} disabled={loading} style={{padding:'0.4rem 0.9rem'}}>{loading ? 'Loading…' : 'Reload Tools'}</button>
      </header>
      <StatusBar />
      <main style={{flex:1, display:'grid', gridTemplateColumns:'280px 1fr 300px', gap:'1rem', padding:'1rem'}}>
        <aside>
          <h2 style={{fontSize:'1rem'}}>Tools ({tools.length})</h2>
          {error && <div style={{color:'red'}}>{error}</div>}
          <div onClick={(e)=>{
            // delegate click: find data-tool attribute if added later
          }}>
            <ToolList tools={tools} />
          </div>
          <div style={{marginTop:'0.75rem'}}>
            <label style={{display:'block', fontSize:'0.75rem', fontWeight:600, textTransform:'uppercase', letterSpacing:'.05em'}}>Select Tool</label>
            <select value={selectedTool || ''} onChange={e=>setSelectedTool(e.target.value || null)} style={{width:'100%', padding:'0.35rem'}}>
              <option value=''>-- choose --</option>
              {tools.map(t=> <option key={t} value={t}>{t}</option>)}
            </select>
            <ToolExecutor toolName={selectedTool} />
          </div>
        </aside>
        <section style={{display:'flex', flexDirection:'column', gap:'1rem'}}>
          <div style={{display:'flex', gap:'.5rem'}}>
            <button onClick={()=>setChatMode('http')} disabled={chatMode==='http'}>HTTP Chat</button>
            <button onClick={()=>setChatMode('ws')} disabled={chatMode==='ws'}>WebSocket Chat</button>
          </div>
            {chatMode==='http' ? <ChatPanel /> : <WebSocketChat />}
        </section>
        <aside style={{display:'flex', flexDirection:'column'}}>
          <QuickActions />
          <CredentialsPanel />
        </aside>
      </main>
      <footer style={{padding:'0.5rem 1rem', fontSize:'0.75rem', color:'#666', borderTop:'1px solid #eee'}}>OpenAPI MCP Demo</footer>
    </div>
  );
};
