export type ServiceHealth = 'healthy' | 'degraded' | 'failed' | 'unknown';
export type AlertSeverity = 'critical' | 'warning' | 'info';
export type AlertState = 'active' | 'resolved';
export type LogLevel = 'ERROR' | 'WARN' | 'INFO' | 'DEBUG';

export interface MetricsSnapshot {
  latency_ms?: number | null;
  error_rate?: number | null;
  timeout?: boolean;
}

export interface ServiceSnapshot {
  name: string;
  localHealth: ServiceHealth;
  finalHealth: ServiceHealth;
  metrics: MetricsSnapshot;
  dependencies: string[];
  dependents: string[];
  rootCause: boolean;
  severity: AlertSeverity;
  confidence: number;
  baseImpactScore: number;
  operationalImpactScore: number;
  impactScore: number;
  blastRadius: number;
  propagated: boolean;
}

export interface AlertRecord {
  id: string;
  title: string;
  severity: AlertSeverity;
  status: AlertState;
  timestamp: string;
  affectedServices: string[];
  rootCause: string;
  confidence: number;
  summary: string;
}

export interface LogRecord {
  id: string;
  timestamp: string;
  service: string;
  level: LogLevel;
  message: string;
  details: string;
}

export interface ImpactRecord {
  service: string;
  baseImpactScore: number;
  operationalImpactScore: number;
  impactScore: number;
  blastRadius: number;
  severity: AlertSeverity;
  status: ServiceHealth;
  trend: number[];
  incidents: number;
}

export interface OverviewSummary {
  totalServices: number;
  healthy: number;
  degraded: number;
  failed: number;
  criticalAlerts: number;
  activeAlerts: number;
}

export interface GraphNodeData {
  label: string;
  status: ServiceHealth;
  metrics: MetricsSnapshot;
  rootCause: boolean;
  confidence: number;
  impactScore: number;
}

export interface GraphView {
  nodes: Array<{ id: string; data: GraphNodeData; position: { x: number; y: number } }>;
  edges: Array<{ id: string; source: string; target: string; animated?: boolean }>;
}

export interface DashboardSnapshot {
  summary: OverviewSummary;
  services: ServiceSnapshot[];
  alerts: AlertRecord[];
  logs: LogRecord[];
  impact: ImpactRecord[];
  graph: GraphView;
  lastSyncedAt: string;
  connectionState: 'live' | 'offline';
  liveLatencyMs?: number;
}
