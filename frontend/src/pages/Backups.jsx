import React, { useState } from 'react';
import { api } from '../api';
import { useApi, useNotification } from '../hooks';
import { Loading, ErrorMessage, EmptyState, ConfirmDialog, Notification } from '../components';

export default function Backups() {
  const { data, loading, error, reload } = useApi(() => api.backups.list());
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [restoreTarget, setRestoreTarget] = useState(null);
  const { notification, notify } = useNotification();

  return (
    <div>
      <Notification notification={notification} />
      <h1 className="page-title">Database & Backups</h1>
      <div className="toolbar">
        <button className="btn btn-primary" onClick={async () => {
          try { const r = await api.backups.create(); notify(r.message, 'success'); reload(); }
          catch (e) { notify(e.message, 'error'); }
        }}>Create Backup</button>
      </div>

      {loading ? <Loading /> : error ? <ErrorMessage message={error} /> : (
        <>
          {(!data || data.length === 0) ? (
            <EmptyState icon="💾" text="No backups yet" />
          ) : (
            <div className="card" style={{ padding: 0 }}>
              <table>
                <thead><tr><th>Name</th><th>Size</th><th>Created</th><th>Actions</th></tr></thead>
                <tbody>
                  {data.map(b => (
                    <tr key={b.name}>
                      <td>{b.name}</td>
                      <td>{(b.size_bytes / 1024).toFixed(1)} KB</td>
                      <td>{new Date(b.created_at).toLocaleString()}</td>
                      <td style={{ display: 'flex', gap: 4 }}>
                        <button className="btn" style={{ padding: '4px 8px', fontSize: 11 }}
                          onClick={() => setRestoreTarget(b.name)}>Restore</button>
                        <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: 11 }}
                          onClick={() => setDeleteTarget(b.name)}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      {restoreTarget && (
        <ConfirmDialog
          title="Restore Backup"
          message={`This will overwrite the current database with "${restoreTarget}". The server must be restarted after restoring.`}
          onConfirm={async () => {
            try { await api.backups.restore(restoreTarget); notify('Backup restored — restart the server to apply', 'success'); }
            catch (e) { notify(e.message, 'error'); }
            setRestoreTarget(null);
          }}
          onCancel={() => setRestoreTarget(null)}
        />
      )}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete Backup"
          message={`Permanently delete backup "${deleteTarget}"?`}
          onConfirm={async () => {
            try { await api.backups.delete(deleteTarget); notify('Backup deleted', 'success'); reload(); }
            catch (e) { notify(e.message, 'error'); }
            setDeleteTarget(null);
          }}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
