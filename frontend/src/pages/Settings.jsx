import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { useApi, useNotification } from '../hooks';
import { Loading, ErrorMessage, Notification } from '../components';

export default function Settings() {
  const { data, loading, error, reload } = useApi(() => api.settings.get());
  const [form, setForm] = useState({});
  const { notification, notify } = useNotification();

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = async () => {
    try {
      await api.settings.update(form);
      notify('Settings saved', 'success');
      reload();
    } catch (e) { notify(e.message, 'error'); }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div>
      <Notification notification={notification} />
      <h1 className="page-title">Settings</h1>
      <div className="card">
        <div className="form-group">
          <label className="form-label">Max Workers</label>
          <input type="number" value={form.max_worker_count || ''} onChange={e => setForm({...form, max_worker_count: parseInt(e.target.value) || 1})} />
        </div>
        <div className="form-group">
          <label className="form-label">Max Queue Size</label>
          <input type="number" value={form.max_queue_size || ''} onChange={e => setForm({...form, max_queue_size: parseInt(e.target.value) || 10})} />
        </div>
        <div className="form-group">
          <label className="form-label">Job Timeout (seconds)</label>
          <input type="number" value={form.job_timeout_seconds || ''} onChange={e => setForm({...form, job_timeout_seconds: parseInt(e.target.value) || 30})} />
        </div>
        <div className="form-group">
          <label className="form-label">Max Retries</label>
          <input type="number" value={form.max_retries || ''} onChange={e => setForm({...form, max_retries: parseInt(e.target.value) || 0})} />
        </div>
        <div className="form-group">
          <label className="form-label">Import Max Rows</label>
          <input type="number" value={form.import_max_rows || ''} onChange={e => setForm({...form, import_max_rows: parseInt(e.target.value) || 100})} />
        </div>
        <div className="form-group">
          <label className="form-label">Backup Retention (days)</label>
          <input type="number" value={form.backup_retention_days || ''} onChange={e => setForm({...form, backup_retention_days: parseInt(e.target.value) || 1})} />
        </div>
        <div className="form-group">
          <label className="form-label">Theme</label>
          <select value={form.theme || 'light'} onChange={e => {
            setForm({...form, theme: e.target.value});
            document.documentElement.setAttribute('data-theme', e.target.value);
          }}>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>
        <button className="btn btn-primary" onClick={save}>Save Settings</button>
      </div>
    </div>
  );
}
