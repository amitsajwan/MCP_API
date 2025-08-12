import React, { useEffect, useState } from 'react';
import { api } from '../util/api';

export const StatusBar: React.FC = () => {
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try { setStatus(await api.getStatus()); setError(null);} catch(e:any){ setError(e.message);} }

  useEffect(()=>{ load(); const id=setInterval(load, 5000); return ()=>clearInterval(id); },[]);

  if (error) return <div style={{padding:'0.4rem 1rem', background:'#fee', color:'#900'}}>Status error: {error}</div>;
  if (!status) return <div style={{padding:'0.4rem 1rem', background:'#f5f5f5'}}>Loading status…</div>;

  return (
    <div style={{padding:'0.35rem 1rem', fontSize:'0.8rem', background: status.mcp_server_connected ? '#0a61' : '#666', color:'#fff', display:'flex', gap:'1rem'}}>
      <span>Server: {status.mcp_server_connected ? 'Connected' : 'Disconnected'}</span>
      <span>Tools: {status.available_tools}</span>
      <span>{new Date(status.server_timestamp || Date.now()).toLocaleTimeString()}</span>
    </div>
  );
};
