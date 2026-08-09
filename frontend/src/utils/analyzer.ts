import type { ServiceHealth } from '../types/domain';

const statusColors: Record<ServiceHealth, string> = {
  healthy: '#39d98a',
  degraded: '#f59e0b',
  failed: '#ff5c7c',
  unknown: '#94a3b8',
};

export function statusColor(status: ServiceHealth) {
  return statusColors[status];
}
