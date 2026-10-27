import React, { useState } from 'react';

export function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;
  return (
    <div className="pagination">
      <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Prev</button>
      <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
        Page {page} of {totalPages}
      </span>
      <button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</button>
    </div>
  );
}

export function ConfirmDialog({ open, title, message, onConfirm, onCancel }) {
  if (!open) return null;
  return (
    <div className="confirm-dialog-overlay" onClick={onCancel}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()}>
        <h3>{title}</h3>
        <p>{message}</p>
        <div className="actions">
          <button className="btn" onClick={onCancel}>Cancel</button>
          <button className="btn btn-danger" onClick={onConfirm}>Confirm</button>
        </div>
      </div>
    </div>
  );
}

export function Notification({ notification }) {
  if (!notification) return null;
  return (
    <div className={`notification notification-${notification.type}`}>
      {notification.message}
    </div>
  );
}

export function StatusBadge({ status }) {
  const colorMap = {
    draft: 'muted', pending: 'warning', queued: 'warning',
    running: 'info', completed: 'success', verified: 'success',
    authorized: 'success', passed: 'success',
    failed: 'danger', error: 'danger', cancelled: 'danger',
    timeout: 'danger', timed_out: 'danger',
    unverified: 'warning', suspended: 'danger',
    mocked: 'mock', mock_only: 'mock', simulated: 'mock',
    local_record_only: 'muted',
    manual_required: 'warning', unsupported: 'muted',
    registration_confirmed: 'success',
    email_unverified: 'warning',
    verified_live: 'success',
    untested: 'muted', testing: 'info',
    pending_email_verification: 'warning',
    pending_phone_verification: 'warning',
    token_expired: 'warning', revoked: 'muted',
    unconfigured: 'muted', configured: 'info',
    configured_not_tested: 'warning', live_tested: 'success',
    disabled: 'muted', unavailable: 'danger',
    connected: 'success', interrupted: 'warning',
    created: 'muted', paused_manual: 'warning',
  };
  const labelMap = {
    local_record_only: 'Local Record Only',
    manual_required: 'Manual Required',
    mock_only: 'Mock Only',
    verified_live: 'Verified (Live)',
    email_unverified: 'Email Unverified',
    registration_confirmed: 'Registration Confirmed',
    pending_email_verification: 'Pending Email',
    pending_phone_verification: 'Pending Phone',
    token_expired: 'Token Expired',
    timed_out: 'Timed Out',
    configured_not_tested: 'Configured (Untested)',
    live_tested: 'Live Tested',
    paused_manual: 'Paused (Manual)',
  };
  const cls = colorMap[status] || 'muted';
  const label = labelMap[status] || status;
  return <span className={`badge badge-${cls}`}>{label}</span>;
}

export function EmptyState({ icon = '📋', text, message }) {
  const label = text || message || 'No data yet';
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <div className="empty-state-text">{label}</div>
    </div>
  );
}

export function Loading() {
  return <div className="loading">Loading...</div>;
}

export function ErrorMessage({ message }) {
  if (!message) return null;
  return <div className="error-msg">{message}</div>;
}

export function maskEmail(email) {
  if (!email || !email.includes('@')) return email || '';
  const [local, domain] = email.split('@');
  const visible = Math.min(3, local.length);
  return local.slice(0, visible) + '****@' + domain;
}
