import React, { useState } from 'react';
import { api } from '../util/api';

export const ChatPanel: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<{role:string; content:any}[]>([]);
  const [sending, setSending] = useState(false);

  const send = async () => {
    if (!input.trim()) return;
    const text = input.trim();
    setInput('');
    setMessages(m => [...m, { role:'user', content:text }]);
    setSending(true);
    try {
      const resp = await api.sendChat(text);
      setMessages(m => [...m, { role:'assistant', content: JSON.stringify(resp) }]);
    } catch (e:any){
      setMessages(m => [...m, { role:'assistant', content: 'Error: '+ e.message }]);
    } finally { setSending(false); }
  };

  return (
    <div style={{display:'flex', flexDirection:'column', height:'100%'}}>
      <div style={{flex:1, overflow:'auto', padding:'0.5rem', border:'1px solid #ddd', borderRadius:4, marginBottom:'0.5rem', background:'#fafafa'}}>
        {messages.map((m,i)=>(
          <div key={i} style={{marginBottom:'0.35rem'}}>
            <strong style={{color: m.role==='user' ? '#333':'#0a6'}}> {m.role}: </strong>
            <span style={{whiteSpace:'pre-wrap', fontFamily:'monospace', fontSize:'0.75rem'}}>{m.content}</span>
          </div>
        ))}
      </div>
      <div style={{display:'flex', gap:'0.5rem'}}>
        <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter') send(); }} placeholder="Ask something..." style={{flex:1, padding:'0.5rem'}} />
        <button onClick={send} disabled={sending} style={{padding:'0.5rem 1rem'}}>{sending? '...' : 'Send'}</button>
      </div>
    </div>
  );
};
