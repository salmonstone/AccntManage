import React from 'react';
import { api } from '../api';
import { useApi } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, EmptyState } from '../components';

export default function Dashboard() {
  const { data: metrics, loading, error } = useApi(() => api.dashboard.metrics());
  const { data: activity } = useApi(() => api.dashboard.activity(10));

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div>
      <h1 className="page-title">Overview</h1>
      <div className="metrics-grid">
        <MetricCard value={metrics.total_battlenet_accounts} label="Battle.net Accounts" />
        <MetricCard value={metrics.total_twitch_accounts} label="Twitch Accounts" />
        <MetricCard value={metrics.total_mailboxes} label="Mailboxes" />
        <MetricCard value={metrics.total_proxies} label="Proxies" />
        <MetricCard value={metrics.active_jobs} label="Active Jobs" />
        <MetricCard value={metrics.completed_jobs_24h} label="Completed (24h)" />
        <MetricCard value={metrics.failed_jobs_24h} label="Failed (24h)" />
        <MetricCard value={metrics.mailboxes_authorized} label="Authorized Mailboxes" />
      </div>

      <div className="card">
        <div className="card-title">Account Status Distribution</div>
        {Object.keys(metrics.accounts_by_status).length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No accounts yet</p>
        ) : (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {Object.entries(metrics.accounts_by_status).map(([status, count]) => (
              <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <StatusBadge status={status} />
                <span style={{ fontSize: 14, fontWeight: 600 }}>{count}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-title">Proxy Health</div>
        <div style={{ display: 'flex', gap: 24, fontSize: 14 }}>
          <span>Passed: <strong style={{ color: 'var(--success)' }}>{metrics.proxies_passed}</strong></span>
          <span>Failed: <strong style={{ color: 'var(--danger)' }}>{metrics.proxies_failed}</strong></span>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Recent Activity</div>
        {!activity || activity.length === 0 ? (
          <EmptyState icon="📝" text="No recent activity" />
        ) : (
          <table>
            <thead>
              <tr><th>Action</th><th>Entity</th><th>Details</th><th>Time</th></tr>
            </thead>
            <tbody>
              {activity.map(a => (
                <tr key={a.id}>
                  <td><StatusBadge status={a.action} /></td>
                  <td>{a.entity_type || '-'}</td>
                  <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.details || '-'}</td>
                  <td>{new Date(a.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function MetricCard({ value, label }) {
  return (
    <div className="metric-card">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
