'use client';

import { useState } from 'react';
import { useBackendStatus } from '@/hooks/useBackendStatus';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  const backend = useBackendStatus();

  return (
    <div className="shell">
      <Sidebar
        open={open}
        onClose={() => setOpen(false)}
        onNew={() => { location.href = '/'; }}
        backend={backend}
      />
      <div className="workspace">
        <Header onMenu={() => setOpen(v => !v)} backend={backend} />
        {children}
      </div>
    </div>
  );
}