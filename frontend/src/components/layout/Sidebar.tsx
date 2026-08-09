import { NavLink } from 'react-router-dom';
import styles from './Sidebar.module.css';

const items = [
  { to: '/', label: 'Overview' },
  { to: '/graph', label: 'Graph' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/impact', label: 'Impact' },
  { to: '/logs', label: 'Logs' },
];

export function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brandBlock}>
        <div className={styles.logoMark}>FPA</div>
        <div>
          <div className={styles.brandTitle}>Failure Propagation Analyzer</div>
          <div className={styles.brandSubtitle}>Real-time observability</div>
        </div>
      </div>

      <nav className={styles.nav}>
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
            end={item.to === '/'}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className={styles.footerCard}>
        <div className={styles.footerLabel}>Streaming ready</div>
        <div className={styles.footerValue}>Backend API + derived analytics</div>
        <div className={styles.footerNote}>Built for live dependency mapping and incident response.</div>
      </div>
    </aside>
  );
}
