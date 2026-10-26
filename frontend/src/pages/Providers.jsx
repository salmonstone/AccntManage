import React from 'react';
import { api } from '../api';
import { useApi, useNotification } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, Notification } from '../components';

export default function Providers() {
  const { notification, notify } = useNotification();

  return (
    <div>
      <Notification notification={notification} />
      <h1 className="page-title">Provider Settings</h1>

      <ProviderCard type="sms" title="SMS Provider" notify={notify}
        description="Mock SMS adapter active. Live SMS is for authorized test environments only." />
      <ProviderCard type="captcha" title="CAPTCHA Provider" notify={notify}
        description="Live CAPTCHA solving is disabled by policy. Only mock results are available." />
      <ProviderCard type="msgraph" title="Microsoft Graph" notify={notify}
        description="Configure Azure app registration for authorized mailbox access. Requires tenant admin consent." />
    </div>
  );
}

function ProviderCard({ type, title, description, notify }) {
  const { data, loading, reload } = useApi(() => api.providers.health(type), [type]);

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div>
          <div className="card-title">{title}</div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>{description}</p>
        </div>
        {data && <StatusBadge status={data.status} />}
      </div>
      {data && (
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>
          {data.message}
          {data.is_mock && <span className="badge badge-mock" style={{ marginLeft: 8 }}>MOCK — No live integration active</span>}
          {data.status === 'disabled' && <span className="badge badge-muted" style={{ marginLeft: 8 }}>DISABLED BY POLICY</span>}
        </div>
      )}
      <button className="btn" onClick={async () => {
        try { await reload(); notify('Health check complete', 'info'); } catch (e) { notify(e.message, 'error'); }
      }}>Check Health</button>
    </div>
  );
}
