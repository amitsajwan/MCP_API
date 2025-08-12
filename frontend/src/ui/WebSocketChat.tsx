import React, { useEffect, useRef, useState } from 'react';
import { api } from '../util/api';

interface Message { role:'user'|'assistant'; content:string; ts?:string }

export const WebSocketChat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [connected, setConnected] = useState(false);
  const [sessionId] = useState('default');
  const wsRef = useRef<WebSocket|null>(null);

  useEffect(()=>{
    const url = api.ws(sessionId);
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = ev => {
      try {
        const data = JSON.parse(ev.data);
        const content = typeof data.response === 'string' ? data.response : JSON.stringify(data.response);
        setMessages(m=>[...m, { role:'assistant', content, ts:data.timestamp }]);
      } catch {
        setMessages(m=>[...m, { role:'assistant', content: ev.data }]);
      }
    };
    return () => ws.close();
  }, [sessionId]);

  const send = () => {
    if(!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    const text = input.trim();
    setMessages(m=>[...m, { role:'user', content:text }]);
    wsRef.current.send(JSON.stringify({ message: text }));
    setInput('');
  };

  return (
    <div style={{display:'flex', flexDirection:'column', height:'100%'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'.25rem'}}>
        <strong>WebSocket Chat</strong>
        <span style={{fontSize:'.65rem', color: connected? '#090':'#a00'}}>{connected? 'connected':'disconnected'}</span>
      </div>
      <div style={{flex:1, overflow:'auto', padding:'0.5rem', border:'1px solid #ddd', borderRadius:4, background:'#fdfdfd'}}>
        {messages.map((m,i)=>(
          <div key={i} style={{marginBottom:'.4rem'}}>
            <span style={{fontWeight:600, color:m.role==='user'? '#333':'#0a6'}}>{m.role}: </span>
            <span style={{whiteSpace:'pre-wrap', fontFamily:'monospace', fontSize:'.75rem'}}>{m.content}</span>
          </div>
        ))}
      </div>
      <div style={{display:'flex', gap:'.5rem', marginTop:'.5rem'}}>
        <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter') send(); }} placeholder='Type message...' style={{flex:1, padding:'.45rem'}} />
        <button onClick={send} disabled={!connected || !input.trim()} style={{padding:'.5rem 1rem'}}>Send</button>
      </div>
    </div>
  );
};

export default WebSocketChat;
