import React, { useEffect, useState } from 'react';
import { fetchJSON, postJSON } from '../util/api';

interface ToolParam {
  name: string;
  type?: string;
  description?: string;
  required?: boolean;
  location?: string;
}
interface ToolMeta {
  name: string;
  description: string;
  parameters: ToolParam[];
}
interface Props {
  toolName: string | null;
  onRun?: (result: any) => void;
}

export const ToolExecutor: React.FC<Props> = ({ toolName, onRun }) => {
  const [meta, setMeta] = useState<ToolMeta | null>(null);
  const [form, setForm] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    if (!toolName) { setMeta(null); setResult(null); return; }
    setLoading(true);
    setError(null);
    fetchJSON(`/tool_meta/${toolName}`)
      .then(m => { setMeta(m); const defaults: Record<string, any> = {}; (m.parameters||[]).forEach((p:ToolParam)=>defaults[p.name]=''); setForm(defaults); })
      .catch(e => setError(String(e)))
      .finally(()=>setLoading(false));
  }, [toolName]);

  const run = () => {
    if (!toolName) return;
    setLoading(true);
    postJSON('/run_tool', { tool_name: toolName, arguments: form })
      .then(r => { setResult(r); onRun && onRun(r); })
      .catch(e => setError(String(e)))
      .finally(()=>setLoading(false));
  };

  if (!toolName) return <div style={{padding:'0.5rem', fontStyle:'italic'}}>Select a tool.</div>;
  if (loading && !meta) return <div>Loading tool metadata...</div>;
  if (error) return <div style={{color:'red'}}>Error: {error}</div>;
  if (!meta) return null;

  return (
    <div style={{border:'1px solid #ddd', borderRadius:4, padding:'0.75rem', marginTop:'0.5rem'}}>
      <h3 style={{marginTop:0}}>{meta.name}</h3>
      <p style={{marginTop:0, fontSize:'0.9rem'}}>{meta.description}</p>
      {(meta.parameters && meta.parameters.length>0) ? (
        <form onSubmit={(e)=>{e.preventDefault(); run();}}>
          {meta.parameters.map(p => (
            <div key={p.name} style={{marginBottom:'0.5rem'}}>
              <label style={{display:'block', fontWeight:600}}>{p.name}{p.required && <span style={{color:'red'}}> *</span>}</label>
              <input
                type='text'
                value={form[p.name] ?? ''}
                onChange={e=>setForm(f=>({...f, [p.name]: e.target.value}))}
                placeholder={p.description || p.type || ''}
                style={{width:'100%', padding:'0.4rem', boxSizing:'border-box'}}
              />
            </div>
          ))}
          <button type='submit' disabled={loading} style={{padding:'0.5rem 1rem'}}>Run</button>
        </form>
      ) : (
        <div style={{fontStyle:'italic'}}>No parameters.</div>
      )}
      {loading && <div>Running...</div>}
      {result && (
        <details style={{marginTop:'0.75rem'}} open>
          <summary style={{cursor:'pointer'}}>Result</summary>
          <pre style={{maxHeight:200, overflow:'auto', background:'#f7f7f7', padding:'0.5rem'}}>{JSON.stringify(result, null, 2)}</pre>
        </details>
      )}
    </div>
  );
};

export default ToolExecutor;
