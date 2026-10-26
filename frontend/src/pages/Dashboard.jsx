import React from 'react';
import { api } from '../api';
import { useApi } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, EmptyState } from '../components';

const MOCK_STATUSES = new Set(['mocked', 'simulated', 'local_record_only']);
const LIVE_STATUSES = new Set(['verified_live', 'registration_confirmed']);

export default function Dashboard() {
  const { data: metrics, loading, error } = useApi(() => api.dashboard.metrics());
  const { data: activity } = useApi(() => api.dashboard.activity(10));
  const { data: health } = useApi(() => api.health());

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;

  const mockCount = metrics.mock_accounts ?? Object.entries(metrics.accounts_by_status)
    .filter(([s]) => MOCK_STATUSES.has(s)).reduce((sum, [, c]) => sum + c, 0);
  const liveCount = metrics.live_accounts ?? Object.entries(metrics.accounts_by_status)
    .filter(([s]) => LIVE_STATUSES.has(s)).reduce((sum, [, c]) => sum + c, 0);

  return (
    <div>
      <h1 className="page-title">Overview</h1>
      {health?.mock_mode && (
        <div style={{ padding: '10px 16px', marginBottom: 16, background: '#fff3e0', border: '1px solid #ffe0b2', borderRadius: 8, fontSize: 13, color: '#e65100' }}>
          All providers are running in <strong>mock mode</strong>. No live third-party integrations are active. Results labelled "simulated" or "mocked" are deterministic test data, not real external state.
        </div>
      )}
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

      {(mockCount > 0 || liveCount > 0) && (
        <div className="card">
          <div className="card-title">Mock vs Live Accounts</div>
          <div style={{ display: 'flex', gap: 24, fontSize: 14 }}>
            <span>Live (verified): <strong style={{ color: 'var(--success)' }}>{liveCount}</strong></span>
            <span>Mock / Simulated: <strong style={{ color: '#ff9800' }}>{mockCount}</strong></span>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
            "Live" counts only accounts confirmed through a real, authorized external workflow. "Mock / Simulated" counts local records, simulated runs, and mock results.
          </p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
        <div className="card">
          <div className="card-title">Job Status Breakdown</div>
          <DonutChart data={metrics.job_status_breakdown} />
        </div>
        <div className="card">
          <div className="card-title">7-Day Activity</div>
          <BarChart data={metrics.activity_timeline} />
        </div>
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

const DONUT_COLORS = ['#c9a96e', '#8b7355', '#6b8e7b', '#d4583a', '#7a8b99', '#b8860b', '#5f7a8a'];

function DonutChart({ data }) {
  const entries = Object.entries(data || {});
  const total = entries.reduce((s, [, v]) => s + v, 0);
  if (total === 0) return <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No jobs yet</p>;

  const r = 70, cx = 100, cy = 100, stroke = 28;
  const circumference = 2 * Math.PI * r;
  let offset = 0;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
      <svg width={200} height={200} viewBox="0 0 200 200">
        {entries.map(([status, count], i) => {
          const pct = count / total;
          const dash = pct * circumference;
          const seg = (
            <circle
              key={status}
              cx={cx} cy={cy} r={r}
              fill="none"
              stroke={DONUT_COLORS[i % DONUT_COLORS.length]}
              strokeWidth={stroke}
              strokeDasharray={`${dash} ${circumference - dash}`}
              strokeDashoffset={-offset}
              transform={`rotate(-90 ${cx} ${cy})`}
            />
          );
          offset += dash;
          return seg;
        })}
        <text x={cx} y={cy - 6} textAnchor="middle" style={{ fontSize: 22, fontWeight: 700, fill: 'var(--text-primary)' }}>{total}</text>
        <text x={cx} y={cy + 14} textAnchor="middle" style={{ fontSize: 11, fill: 'var(--text-muted)' }}>total jobs</text>
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {entries.map(([status, count], i) => (
          <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <span style={{ width: 12, height: 12, borderRadius: 3, background: DONUT_COLORS[i % DONUT_COLORS.length], flexShrink: 0 }} />
            <span style={{ color: 'var(--text-secondary)' }}>{status}</span>
            <strong>{count}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function BarChart({ data }) {
  const items = data || [];
  if (items.length === 0) return <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No activity data</p>;

  const maxCount = Math.max(...items.map(d => d.count), 1);
  const barH = 160;

  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: barH + 30 }}>
      {items.map(d => {
        const h = (d.count / maxCount) * barH;
        const label = d.date.slice(5);
        return (
          <div key={d.date} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>{d.count}</span>
            <div style={{ width: '100%', maxWidth: 40, height: h || 2, background: 'var(--accent, #c9a96e)', borderRadius: '4px 4px 0 0', transition: 'height 0.3s' }} />
            <span style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>{label}</span>
          </div>
        );
      })}
    </div>
  );
}
