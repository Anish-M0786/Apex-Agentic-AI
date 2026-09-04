'use client';
import { MessageSquarePlus, Search, Settings, X, Moon, Sun, Monitor } from 'lucide-react';
import type { BackendInfo } from '@/hooks/useBackendStatus';
import { useTheme } from '@/hooks/useTheme';

export function Sidebar({ open, onClose, onNew, backend }: { open: boolean; onClose: () => void; onNew?: () => void; backend: BackendInfo }) {
  const { theme, setTheme } = useTheme();
  
  const cycleTheme = () => {
    if (theme === 'system') setTheme('light');
    else if (theme === 'light') setTheme('dark');
    else setTheme('system');
  };

  const statusLabel = backend.status === 'connected' ? 'Connected' : backend.status === 'degraded' ? 'Degraded' : backend.status === 'loading' ? 'Connecting…' : 'Unavailable';
  return <aside className={'sidebar ' + (open ? 'open' : '')}>
    <div className="side-brand"><span>TX</span><strong>Apex</strong><button onClick={onClose} aria-label="Close navigation"><X size={17} /></button></div>
    <button className="new-chat" onClick={onNew}><MessageSquarePlus size={17} /> New workspace</button>
    <button className="side-link"><Search size={17} /> Search conversations</button>
    <p>RECENT WORK</p><div className="empty-recent">Your conversations will appear here.</div>
    <div className={'runtime-status ' + (backend.status === 'connected' ? 'conn-ok' : 'conn-err')}><span aria-hidden="true">●</span> {statusLabel}</div>
    <button className="side-link settings"><Settings size={17} /> Settings</button>
    <button className="side-link" onClick={cycleTheme}>
      {theme === 'system' ? <Monitor size={17} /> : theme === 'light' ? <Sun size={17} /> : <Moon size={17} />}
      Theme: {theme.charAt(0).toUpperCase() + theme.slice(1)}
    </button>
  </aside>;
}