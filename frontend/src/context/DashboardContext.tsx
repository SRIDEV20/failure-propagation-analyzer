import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { DashboardSnapshot } from '../types/domain';
import { fetchLiveSystemState } from '../services/healthService';

interface DashboardContextValue {
  data: DashboardSnapshot;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

function createEmptyDashboardSnapshot(): DashboardSnapshot {
  return {
    summary: {
      totalServices: 0,
      healthy: 0,
      degraded: 0,
      failed: 0,
      criticalAlerts: 0,
      activeAlerts: 0,
    },
    services: [],
    alerts: [],
    logs: [],
    impact: [],
    graph: { nodes: [], edges: [] },
    lastSyncedAt: new Date(0).toISOString(),
    connectionState: 'offline',
    liveLatencyMs: undefined,
  };
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DashboardSnapshot>(() => createEmptyDashboardSnapshot());

  const refresh = async () => {
    setLoading(true);
    setError(null);

    try {
      const liveState = await fetchLiveSystemState();
      if (liveState?.error) {
        setError(liveState.error);
        setData((current) => ({ ...current, connectionState: 'offline' }));
      } else if (liveState) {
        setData(liveState);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Failed to load dashboard');
      setData((current) => ({ ...current, connectionState: 'offline' }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => {
      void refresh();
    }, 15000);

    return () => window.clearInterval(interval);
  }, []);

  const value = useMemo(() => ({ data, loading, error, refresh }), [data, loading, error]);

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard() {
  const context = useContext(DashboardContext);

  if (!context) {
    throw new Error('useDashboard must be used inside DashboardProvider');
  }

  return context;
}
