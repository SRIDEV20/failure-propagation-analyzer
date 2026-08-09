import { useLocation } from 'react-router-dom';
import { useDashboard } from '../../context/DashboardContext';
import styles from './TopBar.module.css';

const titleMap: Record<string, string> = {
  '/': 'Overview',
  '/graph': 'Graph',
  '/alerts': 'Alerts',
  '/impact': 'Impact Analysis',
  '/logs': 'Logs',
};

export function TopBar() {
  const location = useLocation();
  const { data, loading, refresh } = useDashboard();

  return (
    <header className={styles.topbar}>
      <div>
        <div className={styles.title}>{titleMap[location.pathname] ?? 'Failure Propagation Analyzer'}</div>
        <div className={styles.subtitle}>
          {loading ? 'Syncing live signals...' : `Last sync ${new Date(data.lastSyncedAt).toLocaleTimeString()}`}
        </div>
      </div>

      <div className={styles.actions}>
        <div className={`${styles.statusPill} ${data.connectionState === 'live' ? styles.live : styles.mock}`}>
          {data.connectionState === 'live' ? 'Live' : 'Offline'}
        </div>
        <button className={styles.refreshButton} onClick={() => void refresh()} type="button">
          Refresh
        </button>
      </div>
    </header>
  );
}
