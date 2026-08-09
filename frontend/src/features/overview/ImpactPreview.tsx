import type { ImpactRecord } from '../../types/domain';
import { EmptyState } from '../../components/ui/EmptyState';
import styles from './ImpactPreview.module.css';

export function ImpactPreview({ impact }: { impact: ImpactRecord[] }) {
  if (impact.length === 0) {
    return <EmptyState title="No impact data" description="The backend has not returned any live impact records yet." />;
  }

  return (
    <div className={styles.list}>
      {impact.slice(0, 5).map((item) => (
        <div key={item.service} className={styles.item}>
          <div className={styles.row}>
            <div>
              <div className={styles.title}>{item.service}</div>
              <div className={styles.meta}>Blast radius {item.blastRadius} • {item.severity}</div>
            </div>
            <div className={styles.score}>{item.impactScore}</div>
          </div>
          <div className={styles.barTrack}>
            <div className={styles.bar} style={{ width: `${Math.min(100, item.impactScore * 6)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
