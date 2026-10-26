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

export function ConfirmDialog({ title, message, onConfirm, onCancel }) {
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
  const map = {
    draft: 'muted', pending: 'warning', queued: 'warning',
    running: 'info', completed: 'success', verified: 'success',
    authorized: 'success', passed: 'success',
    failed: 'danger', error: 'danger', cancelled: 'danger',
    timeout: 'danger', timed_out: 'danger',
    unverified: 'warning', suspended: 'danger',
    mocked: 'mock', mock_only: 'mock',
    manual_required: 'warning', unsupported: 'muted',
    untested: 'muted', testing: 'info',
    pending_email_verification: 'warning',
    pending_phone_verification: 'warning',
    token_expired: 'warning', revoked: 'muted',
    unconfigured: 'muted', configured: 'info',
    connected: 'success', interrupted: 'warning',
  };
  const cls = map[status] || 'muted';
  return <span className={`badge badge-${cls}`}>{status}</span>;
}

export function EmptyState({ icon = '📋', text = 'No data yet' }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <div className="empty-state-text">{text}</div>
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
