import { useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { Tabs } from '../../components/ui/Tabs';
import { useDashboard } from '../../context/DashboardContext';
import styles from './AlertsPage.module.css';

const severityOptions = [
  { value: 'all', label: 'All' },
  { value: 'critical', label: 'Critical' },
  { value: 'warning', label: 'Warning' },
  { value: 'info', label: 'Info' },
] as const;

type SeverityFilter = (typeof severityOptions)[number]['value'];

export function AlertsPage() {
  const { data } = useDashboard();
  const [filter, setFilter] = useState<SeverityFilter>('all');

  const alerts = data.alerts.filter((alert) => filter === 'all' || alert.severity === filter);

  return (
    <div className={styles.page}>
      <Card className={styles.card}>
        <SectionHeader
          title="Alerts"
          description="Filter incidents by severity, inspect active states, and scan the affected service set."
          action={<Tabs value={filter} options={[...severityOptions]} onChange={setFilter} />}
        />

        <div className={styles.table}>
          <div className={styles.head}>
            <div>Severity</div>
            <div>Alert</div>
            <div>Root Cause</div>
            <div>Affected Services</div>
            <div>Time</div>
            <div>Status</div>
          </div>

          {alerts.length === 0 ? (
            <EmptyState title="No alerts returned" description="There are no live alert records matching the current filters." />
          ) : (
            alerts.map((alert) => (
              <div key={alert.id} className={styles.row}>
                <div>
                  <Badge tone={alert.severity === 'critical' ? 'danger' : alert.severity === 'warning' ? 'warning' : 'info'}>{alert.severity}</Badge>
                </div>
                <div>
                  <div className={styles.alertTitle}>{alert.title}</div>
                  <div className={styles.alertSummary}>{alert.summary}</div>
                </div>
                <div>{alert.rootCause}</div>
                <div>{alert.affectedServices.join(', ')}</div>
                <div>{alert.timestamp}</div>
                <div>
                  <Badge tone={alert.status === 'active' ? 'danger' : 'success'}>{alert.status}</Badge>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
