import React, { useState } from 'react';
import { api } from '../api';
import { useApi, useNotification } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, EmptyState, Pagination, Notification } from '../components';

export default function Jobs() {
  const [page, setPage] = useState(1);
  const { notification, notify } = useNotification();
  const { data, loading, error, reload } = useApi(() => api.jobs.list({ page }), [page]);

  return (
    <div>
      <Notification notification={notification} />
      <h1 className="page-title">Job Queue</h1>
      <div className="toolbar">
        <button className="btn" onClick={reload}>Refresh</button>
      </div>

      {loading ? <Loading /> : error ? <ErrorMessage message={error} /> : (
        <>
          {data.items.length === 0 ? (
            <EmptyState icon="⚙️" text="No jobs in queue" />
          ) : (
            <div className="card" style={{ padding: 0 }}>
              <table>
                <thead>
                  <tr><th>ID</th><th>Type</th><th>Status</th><th>Progress</th><th>Items</th><th>Created</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {data.items.map(j => (
                    <tr key={j.id}>
                      <td>{j.id}</td>
                      <td>{j.job_type}</td>
                      <td><StatusBadge status={j.status} /></td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ width: 80, height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ width: `${j.progress}%`, height: '100%', background: 'var(--accent-bronze)', borderRadius: 3 }} />
                          </div>
                          <span style={{ fontSize: 11 }}>{Math.round(j.progress)}%</span>
                        </div>
                      </td>
                      <td>{j.completed_items}/{j.total_items} ({j.failed_items} failed)</td>
                      <td>{new Date(j.created_at).toLocaleString()}</td>
                      <td>
                        {!['completed', 'failed', 'cancelled', 'timed_out'].includes(j.status) && (
                          <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: 11 }}
                            onClick={async () => {
                              try { await api.jobs.cancel(j.id); reload(); notify('Job cancelled', 'success'); }
                              catch (e) { notify(e.message, 'error'); }
                            }}>Cancel</button>
                        )}
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
    </div>
  );
}
