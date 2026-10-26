import React from 'react';
import { api } from '../api';
import { useApi, useNotification } from '../hooks';
import { Loading, ErrorMessage, StatusBadge, Notification } from '../components';

const CAPTCHA_LABELS = {
  capsolver: 'CapSolver',
  anticaptcha: 'AntiCaptcha',
  twocaptcha: '2Captcha',
  ezcaptcha: 'EzCaptcha',
};

export default function Providers() {
  const { notification, notify } = useNotification();
  const { data: profiles, loading: profilesLoading, reload: reloadProfiles } = useApi(
    () => api.providers.captchaProfiles(), []
  );

  return (
    <div>
      <Notification notification={notification} />
      <h1 className="page-title">Provider Settings</h1>

      <ProviderCard type="sms" title="SMS Provider" notify={notify}
        description="Mock SMS adapter active. Live SMS is for authorized test environments only." />

      <div className="card">
        <div className="card-title">CAPTCHA Providers</div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Live CAPTCHA solving is disabled by policy. Only mock results are available.
          Four provider profiles can be configured — only one is active at a time.
        </p>
        {profilesLoading && <Loading />}
        {profiles && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
            {profiles.map(p => (
              <div key={p.provider} style={{
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: 14,
                background: p.is_active ? 'var(--bg-secondary)' : 'transparent',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <strong>{CAPTCHA_LABELS[p.provider] || p.provider}</strong>
                  <StatusBadge status={p.status} />
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {p.is_active && <span className="badge badge-info" style={{ marginRight: 6 }}>ACTIVE</span>}
                  {p.has_key
                    ? <span className="badge badge-success">KEY SET</span>
                    : <span className="badge badge-muted">NO KEY</span>}
                  {p.is_mock && <span className="badge badge-mock" style={{ marginLeft: 6 }}>MOCK</span>}
                  {p.status === 'disabled' && <span className="badge badge-muted" style={{ marginLeft: 6 }}>DISABLED BY POLICY</span>}
                </div>
              </div>
            ))}
          </div>
        )}
        <button className="btn" style={{ marginTop: 12 }} onClick={async () => {
          try { await reloadProfiles(); notify('CAPTCHA profiles refreshed', 'info'); } catch (e) { notify(e.message, 'error'); }
        }}>Refresh Profiles</button>
      </div>

      <ProviderCard type="captcha" title="CAPTCHA Provider (Aggregate)" notify={notify}
        description="Aggregate health check for the active CAPTCHA provider profile." />

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
