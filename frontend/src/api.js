const BASE = '/api/v1';

async function request(path, options = {}) {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || err.error || 'Request failed');
  }
  if (resp.headers.get('content-type')?.includes('text/csv')) {
    return resp.text();
  }
  return resp.json();
}

export const api = {
  dashboard: {
    metrics: () => request('/dashboard/metrics'),
    activity: (limit = 20) => request(`/dashboard/activity?limit=${limit}`),
  },
  accounts: {
    list: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/accounts?${q}`);
    },
    get: (id) => request(`/accounts/${id}`),
    create: (data) => request('/accounts', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data) => request(`/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id) => request(`/accounts/${id}?confirm=true`, { method: 'DELETE' }),
    bulkDelete: (ids) => request('/accounts/bulk-delete?confirm=true', { method: 'POST', body: JSON.stringify(ids) }),
    history: (id) => request(`/accounts/${id}/history`),
    importPreview: (data) => request('/accounts/import/preview', { method: 'POST', body: JSON.stringify(data) }),
    importCommit: (data) => request('/accounts/import/commit', { method: 'POST', body: JSON.stringify(data) }),
    exportCsv: (platform) => request(`/accounts/export/csv${platform ? `?platform=${platform}` : ''}`),
  },
  mailboxes: {
    list: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/mailboxes?${q}`);
    },
    get: (id) => request(`/mailboxes/${id}`),
    importPreview: (data) => request('/mailboxes/import/preview', { method: 'POST', body: JSON.stringify(data) }),
    importCommit: (data) => request('/mailboxes/import/commit', { method: 'POST', body: JSON.stringify(data) }),
    validate: (id) => request(`/mailboxes/${id}/validate`, { method: 'POST' }),
    search: (data) => request('/mailboxes/search', { method: 'POST', body: JSON.stringify(data) }),
    revoke: (id) => request(`/mailboxes/${id}/revoke`, { method: 'POST' }),
    delete: (id) => request(`/mailboxes/${id}?confirm=true`, { method: 'DELETE' }),
  },
  proxies: {
    list: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/proxies?${q}`);
    },
    create: (data) => request('/proxies', { method: 'POST', body: JSON.stringify(data) }),
    test: (id) => request(`/proxies/${id}/test`, { method: 'POST' }),
    delete: (id) => request(`/proxies/${id}?confirm=true`, { method: 'DELETE' }),
    import: (data) => request('/proxies/import', { method: 'POST', body: JSON.stringify(data) }),
  },
  jobs: {
    list: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/jobs?${q}`);
    },
    get: (id) => request(`/jobs/${id}`),
    create: (data) => request('/jobs', { method: 'POST', body: JSON.stringify(data) }),
    cancel: (id) => request(`/jobs/${id}/cancel`, { method: 'POST' }),
  },
  providers: {
    list: () => request('/providers'),
    get: (type) => request(`/providers/${type}`),
    update: (type, data) => request(`/providers/${type}`, { method: 'PUT', body: JSON.stringify(data) }),
    health: (type) => request(`/providers/${type}/health`, { method: 'POST' }),
  },
  settings: {
    get: () => request('/settings'),
    update: (data) => request('/settings', { method: 'PATCH', body: JSON.stringify(data) }),
  },
  backups: {
    list: () => request('/backups'),
    create: () => request('/backups', { method: 'POST' }),
    delete: (name) => request(`/backups/${name}?confirm=true`, { method: 'DELETE' }),
  },
  workflows: {
    list: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/workflows?${q}`);
    },
    get: (id) => request(`/workflows/${id}`),
    create: (data) => request('/workflows', { method: 'POST', body: JSON.stringify(data) }),
    cancel: (id) => request(`/workflows/${id}/cancel`, { method: 'POST' }),
  },
  health: () => request('/health'),
  diagnostics: {
    logs: (tail = 100) => fetch(`${BASE}/diagnostics/logs?tail=${tail}`).then(r => r.text()),
  },
};
