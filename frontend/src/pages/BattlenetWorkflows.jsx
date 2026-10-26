import React, { useState } from 'react';
import { api } from '../api';
import { useApi, useNotification } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, EmptyState, Pagination, ConfirmDialog, Notification } from '../components';

const STATUS_COLORS = {
  created: '#888',
  running: '#2196f3',
  paused_manual: '#ff9800',
  completed: '#4caf50',
  failed: '#f44336',
  cancelled: '#9e9e9e',
};

function StepTimeline({ steps }) {
  if (!steps || steps.length === 0) return null;
  return (
    <div style={{ marginTop: 12 }}>
      {steps.map((s, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 0',
          borderBottom: '1px solid var(--border-color)',
        }}>
          <div style={{
            width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
            background: STATUS_COLORS[s.status] || '#888',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: 12, fontWeight: 600,
          }}>{i + 1}</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: 14 }}>{s.step}</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>{s.description}</div>
            <div style={{ fontSize: 13, marginTop: 4 }}>{s.message}</div>
            {s.data?.url && (
              <div style={{ fontSize: 12, marginTop: 4 }}>
                <a href={s.data.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-color)' }}>
                  Open link
                </a>
              </div>
            )}
            {s.data?.verification_link && (
              <div style={{ fontSize: 12, marginTop: 4, padding: '4px 8px', background: 'var(--surface-color)', borderRadius: 4 }}>
                Verification link found — open manually to complete
              </div>
            )}
            {s.data?.verification_code && (
              <div style={{ fontSize: 12, marginTop: 4, padding: '4px 8px', background: 'var(--surface-color)', borderRadius: 4 }}>
                Code: <strong>{s.data.verification_code}</strong>
              </div>
            )}
            {s.data?.phone_number && (
              <div style={{ fontSize: 12, marginTop: 4 }}>Phone: {s.data.phone_number}</div>
            )}
            {s.data?.is_mock && (
              <span style={{ fontSize: 11, color: '#ff9800', fontWeight: 600 }}>MOCK</span>
            )}
            {s.screenshot && (
              <div style={{ fontSize: 12, marginTop: 4, color: 'var(--text-secondary)' }}>
                Screenshot: {s.screenshot.split('/').pop()}
              </div>
            )}
          </div>
          <StatusBadge status={s.status} />
        </div>
      ))}
    </div>
  );
}

export default function BattlenetWorkflows() {
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [accountId, setAccountId] = useState('');
  const [selectedWf, setSelectedWf] = useState(null);
  const [cancelId, setCancelId] = useState(null);
  const { notification, notify } = useNotification();

  const { data, loading, error, reload } = useApi(
    () => api.workflows.list({ platform: 'battlenet', page }),
    [page]
  );

  const handleCreate = async () => {
    if (!accountId) return notify('Account ID required', 'error');
    try {
      await api.workflows.create({ platform: 'battlenet', account_id: parseInt(accountId) });
      notify('Battle.net workflow created', 'success');
      setShowCreate(false);
      setAccountId('');
      reload();
    } catch (e) {
      notify(e.message, 'error');
    }
  };

  const handleCancel = async () => {
    try {
      await api.workflows.cancel(cancelId);
      notify('Workflow cancelled', 'success');
      setCancelId(null);
      reload();
    } catch (e) {
      notify(e.message, 'error');
    }
  };

  const loadDetail = async (id) => {
    try {
      const wf = await api.workflows.get(id);
      setSelectedWf(wf);
    } catch (e) {
      notify(e.message, 'error');
    }
  };

  return (
    <div>
      <Notification notification={notification} />
      <h1 className="page-title">Battle.net Workflows</h1>

      <div style={{ padding: '12px 16px', marginBottom: 16, background: 'var(--surface-color)', borderRadius: 8, border: '1px solid var(--border-color)' }}>
        <strong>How it works:</strong> Battle.net account creation requires manual steps because no authorized API exists.
        The workflow navigates to the registration page, detects CAPTCHAs and anti-bot measures, then pauses for manual completion.
        Email verification uses Microsoft Graph (when configured). Phone verification rents an SMS number and pauses for code entry.
      </div>

      <div className="toolbar">
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>Start Workflow</button>
        <button className="btn" onClick={reload}>Refresh</button>
      </div>

      {loading && <Loading />}
      {error && <ErrorMessage message={error} />}

      {showCreate && (
        <div className="dialog-overlay" onClick={() => setShowCreate(false)}>
          <div className="dialog" onClick={e => e.stopPropagation()}>
            <h3>Start Battle.net Workflow</h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Create or select an account first, then enter its ID to start the workflow.
            </p>
            <div className="form-group">
              <label>Account ID</label>
              <input type="number" value={accountId} onChange={e => setAccountId(e.target.value)} placeholder="Enter account ID" />
            </div>
            <div className="dialog-actions">
              <button className="btn" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleCreate}>Start</button>
            </div>
          </div>
        </div>
      )}

      {selectedWf && (
        <div className="dialog-overlay" onClick={() => setSelectedWf(null)}>
          <div className="dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: 640 }}>
            <h3>Workflow #{selectedWf.id}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13, marginBottom: 12 }}>
              <div>Status: <StatusBadge status={selectedWf.status} /></div>
              <div>Account: #{selectedWf.account_id}</div>
              <div>Step: {selectedWf.current_step_index + 1} / {selectedWf.total_steps}</div>
              <div>Job: #{selectedWf.job_id || 'N/A'}</div>
            </div>
            {selectedWf.error_message && (
              <div style={{ color: '#f44336', fontSize: 13, marginBottom: 8 }}>{selectedWf.error_message}</div>
            )}
            <StepTimeline steps={selectedWf.step_results} />
            <div className="dialog-actions" style={{ marginTop: 16 }}>
              <button className="btn" onClick={() => setSelectedWf(null)}>Close</button>
              {!['completed', 'failed', 'cancelled'].includes(selectedWf.status) && (
                <button className="btn btn-danger" onClick={() => { setSelectedWf(null); setCancelId(selectedWf.id); }}>Cancel Workflow</button>
              )}
            </div>
          </div>
        </div>
      )}

      {data && data.items?.length === 0 && <EmptyState message="No Battle.net workflows yet" />}
      {data && data.items?.length > 0 && (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Account</th>
                <th>Status</th>
                <th>Step</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map(wf => (
                <tr key={wf.id}>
                  <td>{wf.id}</td>
                  <td>#{wf.account_id}</td>
                  <td><StatusBadge status={wf.status} /></td>
                  <td>{wf.current_step_index + 1} / {wf.total_steps}</td>
                  <td>{new Date(wf.created_at).toLocaleString()}</td>
                  <td>
                    <button className="btn btn-sm" onClick={() => loadDetail(wf.id)}>Details</button>
                    {!['completed', 'failed', 'cancelled'].includes(wf.status) && (
                      <button className="btn btn-sm btn-danger" onClick={() => setCancelId(wf.id)} style={{ marginLeft: 4 }}>Cancel</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} totalPages={data.total_pages} onPageChange={setPage} />
        </>
      )}

      <ConfirmDialog
        open={cancelId !== null}
        title="Cancel Workflow"
        message="This will cancel the workflow and any associated job. Continue?"
        onConfirm={handleCancel}
        onCancel={() => setCancelId(null)}
      />
    </div>
  );
}
