import React from 'react';

export const ToolList: React.FC<{ tools: string[]; onSelect?: (t:string)=>void }> = ({ tools, onSelect }) => {
  if (!tools.length) return <div style={{fontSize:'0.85rem', color:'#777'}}>No tools.</div>;
  return (
    <ul style={{listStyle:'none', padding:0, margin:0, maxHeight:'60vh', overflow:'auto'}}>
      {tools.map(t => (
        <li key={t} style={{padding:'4px 6px', borderBottom:'1px solid #eee', cursor:'pointer'}} onClick={()=>onSelect && onSelect(t)}>
          <code style={{fontSize:'0.75rem'}}>{t}</code>
        </li>
      ))}
    </ul>
  );
};
