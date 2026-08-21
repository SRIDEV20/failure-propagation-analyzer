import { EmptyState } from '../../components/ui/EmptyState';
import type { LogRecord } from '../../types/domain';
import styles from './RecentEvents.module.css';
import { formatTimestamp } from '../../utils/formatters';

export function RecentEvents({ logs }: { logs: LogRecord[] }) {
  if (logs.length === 0) {
    return <EmptyState title="No recent events" description="The logging source has not returned any live events yet." />;
  }

  return (
    <div className={styles.list}>
      {logs.slice(0, 6).map((log) => (
        <div key={log.id} className={styles.item}>
          <div className={styles.time}>{formatTimestamp(log.timestamp)}</div>
          <div className={styles.message}>
            <strong>{log.service}</strong> {log.message}
          </div>
          <div className={styles.details}>{log.details}</div>
        </div>
      ))}
    </div>
  );
}
