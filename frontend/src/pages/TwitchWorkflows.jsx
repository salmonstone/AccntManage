import React, { useState, useCallback } from 'react';
import { api } from '../api';
import { useApi, useNotification, useWebSocket } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, EmptyState, Pagination, ConfirmDialog, Notification } from '../components';

export default function TwitchWorkflows() {
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [accountId, setAccountId] = useState('');
  const [selectedWf, setSelectedWf] = useState(null);
  const [cancelId, setCancelId] = useState(null);
  const { notification, notify } = useNotification();

  const { data, loading, error, reload } = useApi(
    () => api.workflows.list({ platform: 'twitch', page }),
    [page]
  );

  const onWsMessage = useCallback((msg) => {
    if (msg.type === 'workflow_update' || msg.type === 'workflow_completed' || msg.type === 'workflow_failed') {
      reload();
    }
  }, [reload]);
  useWebSocket(onWsMessage
  );

  const handleCreate = async () => {
    if (!accountId) return notify('Account ID required', 'error');
    try {
      await api.workflows.create({ platform: 'twitch', account_id: parseInt(accountId) });
      notify('Twitch workflow created', 'success');
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
      <h1 className="page-title">Twitch Workflows</h1>

      <div style={{ padding: '12px 16px', marginBottom: 16, background: 'var(--surface-color)', borderRadius: 8, border: '1px solid var(--border-color)' }}>
        <strong>Policy note:</strong> Twitch accounts are <strong>intentionally left unverified</strong> per client specification.
        The workflow navigates to the signup page and pauses for manual registration. No email verification step is performed — this is by design, not an error.
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
            <h3>Start Twitch Workflow</h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Create or select an account first, then enter its ID.
              Email verification will be skipped per client policy.
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
          <div className="dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: 600 }}>
            <h3>Workflow #{selectedWf.id}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13, marginBottom: 12 }}>
              <div>Status: <StatusBadge status={selectedWf.status} /></div>
              <div>Account: #{selectedWf.account_id}</div>
              <div>Step: {selectedWf.current_step_index + 1} / {selectedWf.total_steps}</div>
              <div>Job: #{selectedWf.job_id || 'N/A'}</div>
            </div>
            {selectedWf.step_results?.map((s, i) => (
              <div key={i} style={{
                padding: '8px 0', borderBottom: '1px solid var(--border-color)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{s.step}</div>
                  <div style={{ fontSize: 13, marginTop: 2 }}>{s.message}</div>
                  {s.data?.no_email_verification && (
                    <span style={{ fontSize: 11, color: '#ff9800', fontWeight: 600 }}>NO VERIFICATION (BY POLICY)</span>
                  )}
                </div>
                <StatusBadge status={s.status} />
              </div>
            ))}
            <div className="dialog-actions" style={{ marginTop: 16 }}>
              <button className="btn" onClick={() => setSelectedWf(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {data && data.items?.length === 0 && <EmptyState message="No Twitch workflows yet" />}
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
                  <td>
                    <StatusBadge status={wf.status} />
                    {wf.is_mock && <span className="badge badge-mock" style={{ marginLeft: 4, fontSize: 10 }}>SIMULATED</span>}
                  </td>
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
        message="Cancel this Twitch workflow?"
        onConfirm={handleCancel}
        onCancel={() => setCancelId(null)}
      />
    </div>
  );
}
