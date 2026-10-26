import React, { useState } from 'react';
import { api } from '../api';
import { useApi, useNotification } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, EmptyState, Pagination, ConfirmDialog, Notification } from '../components';

export default function Proxies() {
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [deleteId, setDeleteId] = useState(null);
  const { notification, notify } = useNotification();

  const { data, loading, error, reload } = useApi(() => api.proxies.list({ page }), [page]);

  return (
    <div>
      <Notification notification={notification} />
      <h1 className="page-title">Proxy Diagnostics</h1>
      <div className="card" style={{ background: 'var(--bg-secondary)', fontSize: 13, marginBottom: 16 }}>
        Proxies are for connectivity diagnostics only. They are <strong>not</strong> used to evade
        bans, rate limits, geofencing, or account controls.
      </div>

      <div className="toolbar">
        <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add Proxy</button>
        <button className="btn" onClick={() => setShowImport(true)}>Import</button>
      </div>

      {loading ? <Loading /> : error ? <ErrorMessage message={error} /> : (
        <>
          {data.items.length === 0 ? (
            <EmptyState icon="🌐" text="No proxies added yet" />
          ) : (
            <div className="card" style={{ padding: 0 }}>
              <table>
                <thead>
                  <tr><th>Host</th><th>Port</th><th>Protocol</th><th>Status</th><th>Latency</th><th>Last Tested</th><th>Error</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {data.items.map(p => (
                    <tr key={p.id}>
                      <td>{p.host}</td>
                      <td>{p.port}</td>
                      <td>{p.protocol}</td>
                      <td><StatusBadge status={p.test_status} /></td>
                      <td>{p.last_latency_ms ? `${Math.round(p.last_latency_ms)}ms` : '-'}</td>
                      <td style={{ fontSize: 11 }}>{p.last_test_at ? new Date(p.last_test_at).toLocaleString() : '-'}</td>
                      <td style={{ fontSize: 11, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--danger)' }} title={p.last_error || ''}>{p.last_error || '-'}</td>
                      <td style={{ display: 'flex', gap: 4 }}>
                        <button className="btn" style={{ padding: '4px 8px', fontSize: 11 }}
                          onClick={async () => {
                            try {
                              const r = await api.proxies.test(p.id);
                              notify(`Test ${r.status}: ${r.latency_ms ? Math.round(r.latency_ms) + 'ms' : r.error || ''}`, r.status === 'passed' ? 'success' : 'error');
                              reload();
                            } catch (e) { notify(e.message, 'error'); }
                          }}>Test</button>
                        <button className="btn" style={{ padding: '4px 8px', fontSize: 11 }}
                          onClick={() => setDeleteId(p.id)}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Pagination page={data.page} totalPages={data.total_pages} onPageChange={setPage} />
        </>
      )}

      {showAdd && <AddProxyDialog onClose={() => setShowAdd(false)} onSuccess={() => { setShowAdd(false); reload(); notify('Proxy added', 'success'); }} />}
      {showImport && <ImportProxyDialog onClose={() => setShowImport(false)} onSuccess={() => { setShowImport(false); reload(); notify('Proxies imported', 'success'); }} />}
      {deleteId && <ConfirmDialog title="Delete Proxy" message="Delete this proxy?" onConfirm={async () => { await api.proxies.delete(deleteId); setDeleteId(null); reload(); }} onCancel={() => setDeleteId(null)} />}
    </div>
  );
}

function AddProxyDialog({ onClose, onSuccess }) {
  const [protocol, setProtocol] = useState('http');
  const [host, setHost] = useState('');
  const [port, setPort] = useState('');
  const [error, setError] = useState('');

  return (
    <div className="confirm-dialog-overlay" onClick={onClose}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()}>
        <h3 style={{ color: 'var(--text-primary)' }}>Add Proxy</h3>
        {error && <ErrorMessage message={error} />}
        <div className="form-group">
          <label className="form-label">Protocol</label>
          <select value={protocol} onChange={e => setProtocol(e.target.value)}>
            <option value="http">HTTP</option><option value="https">HTTPS</option>
            <option value="socks4">SOCKS4</option><option value="socks5">SOCKS5</option>
          </select>
        </div>
        <div className="form-group"><label className="form-label">Host</label><input value={host} onChange={e => setHost(e.target.value)} /></div>
        <div className="form-group"><label className="form-label">Port</label><input type="number" value={port} onChange={e => setPort(e.target.value)} /></div>
        <div className="actions">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={async () => {
            try { await api.proxies.create({ protocol, host, port: parseInt(port) }); onSuccess(); } catch (e) { setError(e.message); }
          }}>Add</button>
        </div>
      </div>
    </div>
  );
}

function ImportProxyDialog({ onClose, onSuccess }) {
  const [text, setText] = useState('');
  const [error, setError] = useState('');

  return (
    <div className="confirm-dialog-overlay" onClick={onClose}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
        <h3 style={{ color: 'var(--text-primary)' }}>Import Proxies</h3>
        {error && <ErrorMessage message={error} />}
        <div className="form-group">
          <label className="form-label">Paste proxies (host:port per line)</label>
          <textarea rows={6} value={text} onChange={e => setText(e.target.value)} placeholder="1.2.3.4:8080&#10;socks5://5.6.7.8:1080" />
        </div>
        <div className="actions">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={async () => {
            try { await api.proxies.import({ raw_text: text, default_protocol: 'http' }); onSuccess(); } catch (e) { setError(e.message); }
          }}>Import</button>
        </div>
      </div>
    </div>
  );
}
