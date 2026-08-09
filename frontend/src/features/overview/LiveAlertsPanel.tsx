import { Badge } from '../../components/ui/Badge';
import { EmptyState } from '../../components/ui/EmptyState';
import type { AlertRecord } from '../../types/domain';
import styles from './LiveAlertsPanel.module.css';

export function LiveAlertsPanel({ alerts }: { alerts: AlertRecord[] }) {
  if (alerts.length === 0) {
    return <EmptyState title="No live alerts" description="The alerting service has not returned any active alert records." />;
  }

  return (
    <div className={styles.list}>
      {alerts.slice(0, 4).map((alert) => (
        <div key={alert.id} className={styles.item}>
          <div className={styles.row}>
            <div className={styles.title}>{alert.title}</div>
            <Badge tone={alert.severity === 'critical' ? 'danger' : alert.severity === 'warning' ? 'warning' : 'info'}>
              {alert.severity}
            </Badge>
          </div>
          <div className={styles.meta}>{alert.summary}</div>
          <div className={styles.footer}>
            <span>{alert.timestamp}</span>
            <span>{alert.affectedServices.join(' • ')}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
