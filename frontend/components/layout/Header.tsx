'use client';

import { Menu } from 'lucide-react';
import type { BackendInfo } from '@/hooks/useBackendStatus';

const STATUS_CONFIG = {
  connected: { symbol: '●', label: 'Connected', cls: 'conn-ok' },
  degraded: { symbol: '●', label: 'Degraded', cls: 'conn-warn' },
  unavailable: { symbol: '○', label: 'Backend unavailable', cls: 'conn-err' },
  loading: { symbol: '◌', label: 'Connecting…', cls: 'conn-load' },
} as const;

function ApexMark() {
  return <svg className="brand-mark" viewBox="0 0 32 32" role="img" aria-label="Apex logo">
    <defs>
      <linearGradient id="apex-mark-gradient" x1="4" y1="4" x2="28" y2="28">
        <stop offset="0" stopColor="#69c7b8" />
        <stop offset="1" stopColor="#167568" />
      </linearGradient>
    </defs>
    <rect x="1" y="1" width="30" height="30" rx="10" fill="url(#apex-mark-gradient)" />
    <path d="M8 11h16M12 11v10c0 3 2 5 4 5s4-2 4-5V11" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
    <circle cx="24" cy="22" r="2" fill="#fff" />
  </svg>;
}

export function Header({ onMenu, backend }: { onMenu: () => void; backend: BackendInfo }) {
  const cfg = STATUS_CONFIG[backend.status];
  return <header>
    <button onClick={onMenu} aria-label="Toggle navigation"><Menu size={20} /></button>
    <div className="header-brand"><ApexMark /><strong>Apex</strong></div>
    <span className={'connection ' + cfg.cls} title={cfg.label} aria-label={'Backend status: ' + cfg.label}>{cfg.symbol} {cfg.label}</span>
  </header>;
}
