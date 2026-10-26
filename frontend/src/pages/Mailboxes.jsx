import React, { useState } from 'react';
import { api } from '../api';
import { useApi, useNotification } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, EmptyState, Pagination, ConfirmDialog, Notification } from '../components';

export default function Mailboxes() {
  const [page, setPage] = useState(1);
  const [showImport, setShowImport] = useState(false);
  const [deleteId, setDeleteId] = useState(null);
  const { notification, notify } = useNotification();

  const { data, loading, error, reload } = useApi(
    () => api.mailboxes.list({ page }),
    [page]
  );

  return (
    <div>
      <Notification notification={notification} />
      <h1 className="page-title">Mailbox Manager</h1>
      <div className="card" style={{ background: 'var(--bg-secondary)', marginBottom: 16, fontSize: 13 }}>
        <strong>Microsoft Graph Authorization Required:</strong> Mailbox access requires explicit OAuth
        authorization from the mailbox owner and tenant administrator. Configure your Azure app registration
        in Settings before using live features. Mock data is shown until authorization is configured.
      </div>

      <div className="toolbar">
        <button className="btn btn-primary" onClick={() => setShowImport(true)}>Import Mailboxes</button>
      </div>

      {loading ? <Loading /> : error ? <ErrorMessage message={error} /> : (
        <>
          {data.items.length === 0 ? (
            <EmptyState icon="📧" text="No mailboxes imported yet" />
          ) : (
            <div className="card" style={{ padding: 0 }}>
              <table>
                <thead>
                  <tr><th>Email</th><th>Status</th><th>Scopes</th><th>Created</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {data.items.map(m => (
                    <tr key={m.id}>
                      <td>{m.email}</td>
                      <td><StatusBadge status={m.status} /></td>
                      <td>{m.scopes || '-'}</td>
                      <td>{new Date(m.created_at).toLocaleDateString()}</td>
                      <td style={{ display: 'flex', gap: 4 }}>
                        <button className="btn" style={{ padding: '4px 8px', fontSize: 11 }}
                          onClick={async () => {
                            try {
                              const r = await api.mailboxes.validate(m.id);
                              notify(r.is_mock ? 'Mock validation result' : 'Validated', r.valid ? 'success' : 'warning');
                            } catch (e) { notify(e.message, 'error'); }
                          }}>Validate</button>
                        <button className="btn" style={{ padding: '4px 8px', fontSize: 11 }}
                          onClick={() => setDeleteId(m.id)}>Delete</button>
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

      {showImport && <ImportMailboxDialog onClose={() => setShowImport(false)} onSuccess={() => { setShowImport(false); reload(); notify('Mailboxes imported', 'success'); }} />}
      {deleteId && <ConfirmDialog title="Delete Mailbox" message="This will permanently delete this mailbox record and its stored tokens." onConfirm={async () => { await api.mailboxes.delete(deleteId); setDeleteId(null); reload(); notify('Deleted', 'success'); }} onCancel={() => setDeleteId(null)} />}
    </div>
  );
}

function ImportMailboxDialog({ onClose, onSuccess }) {
  const [text, setText] = useState('');
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');

  return (
    <div className="confirm-dialog-overlay" onClick={onClose}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
        <h3 style={{ color: 'var(--text-primary)' }}>Import Mailboxes</h3>
        {error && <ErrorMessage message={error} />}
        <div className="form-group">
          <label className="form-label">Paste email addresses (one per line)</label>
          <textarea rows={6} value={text} onChange={e => setText(e.target.value)} />
        </div>
        {preview && (
          <div style={{ fontSize: 13, padding: 12, background: 'var(--bg-secondary)', borderRadius: 4, marginBottom: 12 }}>
            Valid: {preview.valid_count} | Duplicates: {preview.duplicate_count} | Invalid: {preview.invalid_count}
          </div>
        )}
        <div className="actions">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn" onClick={async () => {
            try { setPreview(await api.mailboxes.importPreview({ raw_text: text })); } catch (e) { setError(e.message); }
          }}>Preview</button>
          <button className="btn btn-primary" onClick={async () => {
            try { await api.mailboxes.importCommit({ raw_text: text }); onSuccess(); } catch (e) { setError(e.message); }
          }}>Import</button>
        </div>
      </div>
    </div>
  );
}
