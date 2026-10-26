import React, { useState } from 'react';
import { api } from '../api';
import { useApi } from '../hooks';
import { Loading, ErrorMessage } from '../components';

export default function Diagnostics() {
  const { data: health, loading, error } = useApi(() => api.health());
  const [logs, setLogs] = useState('');
  const [logLines, setLogLines] = useState(100);

  const loadLogs = async () => {
    try {
      const text = await api.diagnostics.logs(logLines);
      setLogs(text);
    } catch (e) {
      setLogs('Failed to load logs: ' + e.message);
    }
  };

  return (
    <div>
      <h1 className="page-title">Diagnostics & Logs</h1>

      <div className="card">
        <div className="card-title">System Health</div>
        {loading ? <Loading /> : error ? <ErrorMessage message={error} /> : (
          <div style={{ fontSize: 13 }}>
            <div>Status: <strong style={{ color: health.status === 'healthy' ? 'var(--success)' : 'var(--danger)' }}>{health.status}</strong></div>
            <div>Database: {health.database}</div>
            <div>Python: {health.python_version}</div>
            <div>Platform: {health.platform}</div>
            <div>Timestamp: {health.timestamp}</div>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-title">Application Logs</div>
        <div className="toolbar">
          <select value={logLines} onChange={e => setLogLines(Number(e.target.value))} style={{ width: 100 }}>
            <option value={50}>50 lines</option>
            <option value={100}>100 lines</option>
            <option value={250}>250 lines</option>
            <option value={500}>500 lines</option>
          </select>
          <button className="btn" onClick={loadLogs}>Load Logs</button>
        </div>
        {logs && (
          <pre style={{
            background: '#1a1a1a', color: '#e0e0e0', padding: 16, borderRadius: 4,
            fontSize: 11, maxHeight: 500, overflow: 'auto', whiteSpace: 'pre-wrap',
          }}>{logs}</pre>
        )}
      </div>
    </div>
  );
}
