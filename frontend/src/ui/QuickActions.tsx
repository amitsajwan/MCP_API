import React, { useEffect, useState } from 'react';
import { api } from '../util/api';

export const QuickActions: React.FC = () => {
  const [actions, setActions] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const data = await api.getQuickActions();
      // unify shape -> array of objects with name & description
      let norm: any[] = [];
      if (Array.isArray(data)) {
        if (data.length && typeof data[0] === 'string') {
          norm = data.map(d => ({ name: d, description: d }));
        } else {
          norm = data.map((d:any)=>({ name: d.name || d, description: d.description || d.name || String(d)}));
        }
      } else if (data.tools) {
        norm = data.tools.map((t:any)=>({ name:t.name, description:t.description || t.name }));
      }
      setActions(norm);
      setError(null);
    } catch (e:any) {
      setError(e.message);
    }
  };

  useEffect(()=>{ load(); },[]);

  const execute = async (name:string) => {
    try { await api.runTool(name); } catch(e){ /* ignore for now */ }
  };

  return (
    <div>
      <h2 style={{fontSize:'1rem'}}>Quick Actions</h2>
      {error && <div style={{color:'red'}}>{error}</div>}
      <div style={{display:'flex', flexDirection:'column', gap:'0.35rem'}}>
        {actions.map(a => (
          <button key={a.name} style={{textAlign:'left', fontSize:'0.7rem', padding:'0.35rem 0.5rem', border:'1px solid #ddd', background:'#fff', cursor:'pointer'}} onClick={()=>execute(a.name)}>
            {a.description}
          </button>
        ))}
      </div>
    </div>
  );
};
