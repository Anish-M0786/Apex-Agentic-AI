'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';

export type BackendStatus = 'loading' | 'connected' | 'degraded' | 'unavailable';

export interface BackendInfo {
  status: BackendStatus;
  model: string;
  provider: string;
  modelAvailable: boolean;
}

const POLL_INTERVAL_MS = 30_000;

async function fetchRuntimeHealth(): Promise<BackendInfo> {
  // /api/runtime/health gives richer info (provider, model_available, metrics)
  const data = await apiFetch<{
    provider: string;
    available: boolean;
    configured_model: string;
    model_available: boolean;
  }>('/api/runtime/health');

  return {
    status: data.available ? 'connected' : 'unavailable',
    model: data.configured_model || 'Unknown',
    provider: data.provider || 'Local AI',
    modelAvailable: data.model_available,
  };
}

export function useBackendStatus(): BackendInfo {
  const [info, setInfo] = useState<BackendInfo>({
    status: 'loading',
    model: '',
    provider: 'Local AI',
    modelAvailable: false,
  });

  const check = useCallback(async () => {
    try {
      const result = await fetchRuntimeHealth();
      setInfo(result);
    } catch {
      setInfo(prev => ({ ...prev, status: 'unavailable' }));
    }
  }, []);

  useEffect(() => {
    check();
    const id = window.setInterval(check, POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [check]);

  return info;
}
