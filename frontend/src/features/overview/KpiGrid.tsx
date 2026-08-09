import { Card } from '../../components/ui/Card';
import type { OverviewSummary } from '../../types/domain';
import styles from './KpiGrid.module.css';

const metrics = [
  { key: 'totalServices', label: 'Total services', tone: 'neutral' },
  { key: 'healthy', label: 'Healthy', tone: 'success' },
  { key: 'degraded', label: 'Degraded', tone: 'warning' },
  { key: 'failed', label: 'Failed', tone: 'danger' },
  { key: 'criticalAlerts', label: 'Critical alerts', tone: 'danger' },
] as const;

export function KpiGrid({ summary }: { summary: OverviewSummary }) {
  return (
    <div className={styles.grid}>
      {metrics.map((metric) => (
        <Card key={metric.key} className={styles.card}>
          <div className={styles.label}>{metric.label}</div>
          <div className={`${styles.value} ${styles[metric.tone]}`}>{summary[metric.key]}</div>
        </Card>
      ))}
    </div>
  );
}
