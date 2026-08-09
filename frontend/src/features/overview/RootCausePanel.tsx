import { Badge } from '../../components/ui/Badge';
import { EmptyState } from '../../components/ui/EmptyState';
import type { ServiceSnapshot } from '../../types/domain';
import styles from './RootCausePanel.module.css';

export function RootCausePanel({ services }: { services: ServiceSnapshot[] }) {
  const roots = services.filter((service) => service.rootCause || service.finalHealth !== 'healthy').slice(0, 3);

  if (roots.length === 0) {
    return <EmptyState title="No root causes detected" description="The backend currently reports a fully healthy topology." />;
  }

  return (
    <div className={styles.list}>
      {roots.map((service) => (
        <div key={service.name} className={styles.item}>
          <div className={styles.row}>
            <div>
              <div className={styles.title}>{service.name}</div>
              <div className={styles.description}>{service.rootCause ? 'Primary root cause' : 'Propagation target'}</div>
            </div>
            <Badge tone={service.finalHealth === 'failed' ? 'danger' : 'warning'}>{service.finalHealth}</Badge>
          </div>
          <div className={styles.details}>
            Dependencies: {service.dependencies.length} • Impact score: {service.impactScore} • Confidence: {service.confidence}%
          </div>
        </div>
      ))}
    </div>
  );
}
