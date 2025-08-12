import React, { useState } from 'react';
import { api } from '../util/api';

interface Props {
  onConfigured?: (data:any)=>void;
}

export const CredentialsPanel: React.FC<Props> = ({ onConfigured }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [baseUrl, setBaseUrl] = useState('https://api.example.com');
  const [environment, setEnvironment] = useState('DEV');
  const [sessionId, setSessionId] = useState('default');
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string|null>(null);

  const submit = async (e:React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setError(null); setResult(null);
    try {
      const resp = await api.configure({ username, password, base_url: baseUrl, environment, session_id: sessionId });
      setResult(resp);
      onConfigured && onConfigured(resp);
    } catch (err:any) {
      setError(err.message);
    } finally { setSaving(false); }
  };

  return (
    <div style={{border:'1px solid #ddd', borderRadius:4, padding:'0.75rem', marginTop:'1rem'}}>
      <h3 style={{margin:'0 0 .5rem'}}>Credentials</h3>
      <form onSubmit={submit} style={{display:'flex', flexDirection:'column', gap:'0.5rem'}}>
        <input placeholder='Username' value={username} onChange={e=>setUsername(e.target.value)} required />
        <input placeholder='Password' type='password' value={password} onChange={e=>setPassword(e.target.value)} required />
        <input placeholder='Base API URL' value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} />
        <div style={{display:'flex', gap:'.5rem'}}>
          <input placeholder='Environment' value={environment} onChange={e=>setEnvironment(e.target.value)} style={{flex:1}} />
          <input placeholder='Session ID' value={sessionId} onChange={e=>setSessionId(e.target.value)} style={{flex:1}} />
        </div>
        <button type='submit' disabled={saving}>{saving? 'Saving...' : 'Save & Apply'}</button>
      </form>
      {error && <div style={{color:'red', marginTop:'.5rem'}}>Error: {error}</div>}
      {result && <pre style={{background:'#f7f7f7', padding:'.5rem', marginTop:'.5rem', maxHeight:150, overflow:'auto'}}>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
};

export default CredentialsPanel;
