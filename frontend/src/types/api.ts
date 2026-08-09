import type { AlertRecord, DashboardSnapshot, GraphView, ImpactRecord, LogRecord, MetricsSnapshot, OverviewSummary, ServiceHealth, ServiceSnapshot } from './domain';

export interface BackendServiceState {
  local_state?: string;
  final_state?: string;
  metrics?: MetricsSnapshot;
  last_updated?: number;
}

export interface BackendSystemState extends DashboardSnapshot {
  localState?: Record<string, string>;
  finalState?: Record<string, string>;
  rootFailures?: string[];
  error?: string;
}

export interface BackendMetricsPayload {
  service_name: string;
  metrics: MetricsSnapshot;
}

export interface HealthStatusPayload {
  service: string;
  localState: ServiceHealth;
  finalState: ServiceHealth;
}

export type { AlertRecord, GraphView, ImpactRecord, LogRecord, OverviewSummary, ServiceSnapshot };
