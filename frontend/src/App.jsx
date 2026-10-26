import React, { useState } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import Mailboxes from './pages/Mailboxes';
import Proxies from './pages/Proxies';
import Jobs from './pages/Jobs';
import Providers from './pages/Providers';
import Settings from './pages/Settings';
import Backups from './pages/Backups';
import Diagnostics from './pages/Diagnostics';
import BattlenetWorkflows from './pages/BattlenetWorkflows';
import TwitchWorkflows from './pages/TwitchWorkflows';

const NAV = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/accounts', label: 'Accounts', icon: '👤' },
  { path: '/battlenet', label: 'Battle.net', icon: '🎮' },
  { path: '/twitch', label: 'Twitch', icon: '📺' },
  { path: '/mailboxes', label: 'Mailboxes', icon: '📧' },
  { path: '/proxies', label: 'Proxies', icon: '🌐' },
  { path: '/jobs', label: 'Jobs', icon: '⚙️' },
  { path: '/providers', label: 'Providers', icon: '🔌' },
  { path: '/settings', label: 'Settings', icon: '⚡' },
  { path: '/backups', label: 'Backups', icon: '💾' },
  { path: '/diagnostics', label: 'Diagnostics', icon: '🔍' },
];

export default function App() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="app-layout">
      <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            {!collapsed && <span>AccntMgmt</span>}
            <button className="sidebar-toggle" onClick={() => setCollapsed(!collapsed)}>
              {collapsed ? '→' : '←'}
            </button>
          </div>
        </div>
        <nav className="sidebar-nav">
          {NAV.map(n => (
            <NavLink key={n.path} to={n.path} end={n.path === '/'}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
              <span className="sidebar-icon">{n.icon}</span>
              {!collapsed && <span className="sidebar-label">{n.label}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          {!collapsed && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Mock Mode Active</span>}
        </div>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/battlenet" element={<BattlenetWorkflows />} />
          <Route path="/twitch" element={<TwitchWorkflows />} />
          <Route path="/mailboxes" element={<Mailboxes />} />
          <Route path="/proxies" element={<Proxies />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/providers" element={<Providers />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/backups" element={<Backups />} />
          <Route path="/diagnostics" element={<Diagnostics />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}
