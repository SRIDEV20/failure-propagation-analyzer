import type { ImpactRecord } from '../../types/domain';
import { EmptyState } from '../../components/ui/EmptyState';
import styles from './ImpactPreview.module.css';

export function ImpactPreview({ impact }: { impact: ImpactRecord[] }) {
  if (impact.length === 0) {
    return <EmptyState title="No impact data" description="The backend has not returned any live impact records yet." />;
  }

  const visibleImpact = impact.slice(0, 5);
  const maxImpact = Math.max(...visibleImpact.map((item) => item.operationalImpactScore ?? item.impactScore), 1);

  return (
    <div className={styles.list}>
      {visibleImpact.map((item) => (
        <div key={item.service} className={styles.item}>
          <div className={styles.row}>
            <div>
              <div className={styles.title}>{item.service}</div>
              <div className={styles.meta}>Blast radius {item.blastRadius} • {item.severity}</div>
            </div>
            <div className={styles.score}>{item.operationalImpactScore ?? item.impactScore}</div>
          </div>
          <div className={styles.barTrack}>
            <div className={styles.bar} style={{ width: `${Math.min(100, ((item.operationalImpactScore ?? item.impactScore) / maxImpact) * 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
