import React, { useState, useCallback } from 'react';
import { api } from '../api';
import { useApi, useNotification } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, EmptyState, Pagination, ConfirmDialog, Notification, maskEmail } from '../components';

export default function Accounts() {
  const [platform, setPlatform] = useState('');
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [showImport, setShowImport] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [deleteId, setDeleteId] = useState(null);
  const { notification, notify } = useNotification();

  const params = {};
  if (platform) params.platform = platform;
  if (status) params.status = status;
  if (search) params.search = search;
  params.page = page;

  const { data, loading, error, reload } = useApi(
    () => api.accounts.list(params),
    [platform, status, search, page]
  );

  const handleDelete = async () => {
    try {
      await api.accounts.delete(deleteId);
      notify('Account deleted', 'success');
      setDeleteId(null);
      reload();
    } catch (e) {
      notify(e.message, 'error');
    }
  };

  return (
    <div>
      <Notification notification={notification} />
      <h1 className="page-title">Account Management</h1>

      <div className="toolbar">
        <select value={platform} onChange={e => { setPlatform(e.target.value); setPage(1); }} style={{ width: 160 }}>
          <option value="">All Platforms</option>
          <option value="battlenet">Battle.net</option>
          <option value="twitch">Twitch</option>
        </select>
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(1); }} style={{ width: 200 }}>
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="local_record_only">Local Record Only</option>
          <option value="simulated">Simulated</option>
          <option value="mocked">Mocked</option>
          <option value="manual_required">Manual Required</option>
          <option value="unsupported">Unsupported</option>
          <option value="registration_confirmed">Registration Confirmed</option>
          <option value="pending_email_verification">Pending Email</option>
          <option value="email_unverified">Email Unverified</option>
          <option value="pending_phone_verification">Pending Phone</option>
          <option value="verified_live">Verified (Live)</option>
          <option value="verified">Verified</option>
          <option value="unverified">Unverified</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
          <option value="suspended">Suspended</option>
        </select>
        <input
          placeholder="Search email or name..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          style={{ width: 220 }}
        />
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ Add Account</button>
        <button className="btn" onClick={() => setShowImport(true)}>Import</button>
        <button className="btn" onClick={async () => {
          const csv = await api.accounts.exportCsv(platform || undefined);
          const blob = new Blob([csv], { type: 'text/csv' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url; a.download = 'accounts.csv'; a.click();
          URL.revokeObjectURL(url);
        }}>Export CSV</button>
      </div>

      {loading ? <Loading /> : error ? <ErrorMessage message={error} /> : (
        <>
          {data.items.length === 0 ? (
            <EmptyState icon="👤" text="No accounts found" />
          ) : (
            <div className="card" style={{ padding: 0 }}>
              <table>
                <thead>
                  <tr>
                    <th>Email</th><th>Platform</th><th>Status</th>
                    <th>Name</th><th>Created</th><th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map(a => (
                    <tr key={a.id}>
                      <td title={a.email}>{maskEmail(a.email)}</td>
                      <td><StatusBadge status={a.platform} /></td>
                      <td><StatusBadge status={a.status} /></td>
                      <td>{a.display_name || '-'}</td>
                      <td>{new Date(a.created_at).toLocaleDateString()}</td>
                      <td>
                        <button className="btn" style={{ padding: '4px 8px', fontSize: 11 }}
                          onClick={() => setDeleteId(a.id)}>Delete</button>
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

      {showCreate && <CreateAccountDialog onClose={() => setShowCreate(false)} onSuccess={() => { setShowCreate(false); reload(); notify('Account created', 'success'); }} />}
      {showImport && <ImportDialog onClose={() => setShowImport(false)} onSuccess={() => { setShowImport(false); reload(); notify('Import complete', 'success'); }} />}
      {deleteId && <ConfirmDialog title="Delete Account" message="This will permanently delete this account record." onConfirm={handleDelete} onCancel={() => setDeleteId(null)} />}
    </div>
  );
}

function CreateAccountDialog({ onClose, onSuccess }) {
  const [platform, setPlatform] = useState('battlenet');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const submit = async () => {
    try {
      await api.accounts.create({ platform, email, display_name: name || undefined });
      onSuccess();
    } catch (e) { setError(e.message); }
  };

  return (
    <div className="confirm-dialog-overlay" onClick={onClose}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: 480 }}>
        <h3 style={{ color: 'var(--text-primary)' }}>Add Account</h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
          This creates a local database record only. It does not register an account on the platform.
        </p>
        {error && <ErrorMessage message={error} />}
        <div className="form-group">
          <label className="form-label">Platform</label>
          <select value={platform} onChange={e => setPlatform(e.target.value)}>
            <option value="battlenet">Battle.net</option>
            <option value="twitch">Twitch</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Email</label>
          <input value={email} onChange={e => setEmail(e.target.value)} placeholder="user@example.com" />
        </div>
        <div className="form-group">
          <label className="form-label">Display Name (optional)</label>
          <input value={name} onChange={e => setName(e.target.value)} />
        </div>
        <div className="actions">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={submit}>Create</button>
        </div>
      </div>
    </div>
  );
}

function ImportDialog({ onClose, onSuccess }) {
  const [platform, setPlatform] = useState('battlenet');
  const [text, setText] = useState('');
  const [autoWorkflow, setAutoWorkflow] = useState(false);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');

  const doPreview = async () => {
    try {
      const r = await api.accounts.importPreview({ platform, raw_text: text });
      setPreview(r);
    } catch (e) { setError(e.message); }
  };

  const doImport = async () => {
    try {
      await api.accounts.importCommit({ platform, raw_text: text, auto_workflow: autoWorkflow });
      onSuccess();
    } catch (e) { setError(e.message); }
  };

  return (
    <div className="confirm-dialog-overlay" onClick={onClose}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: 560 }}>
        <h3 style={{ color: 'var(--text-primary)' }}>Import Accounts</h3>
        {error && <ErrorMessage message={error} />}
        <div className="form-group">
          <label className="form-label">Platform</label>
          <select value={platform} onChange={e => setPlatform(e.target.value)}>
            <option value="battlenet">Battle.net</option>
            <option value="twitch">Twitch</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Paste emails (one per line)</label>
          <textarea rows={8} value={text} onChange={e => setText(e.target.value)} placeholder="user1@example.com&#10;user2@example.com" />
        </div>
        <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" id="auto-workflow" checked={autoWorkflow} onChange={e => setAutoWorkflow(e.target.checked)} style={{ width: 'auto' }} />
          <label htmlFor="auto-workflow" style={{ margin: 0, fontSize: 13, cursor: 'pointer' }}>Auto-start workflows after import</label>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {platform === 'twitch' ? '(create only, no verification)' : '(registration + email + phone verify)'}
          </span>
        </div>
        {preview && (
          <div style={{ fontSize: 13, marginBottom: 16, padding: 12, background: 'var(--bg-secondary)', borderRadius: 4 }}>
            <div>Parsed: {preview.total_parsed}</div>
            <div>Valid (new): {preview.valid_count}</div>
            <div>Duplicates: {preview.duplicate_count}</div>
            <div>Invalid: {preview.invalid_count}</div>
          </div>
        )}
        <div className="actions">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn" onClick={doPreview}>Preview</button>
          <button className="btn btn-primary" onClick={doImport} disabled={!text.trim()}>Import</button>
        </div>
      </div>
    </div>
  );
}
