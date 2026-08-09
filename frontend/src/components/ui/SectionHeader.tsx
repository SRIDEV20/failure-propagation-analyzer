import type { ReactNode } from 'react';
import styles from './SectionHeader.module.css';

export function SectionHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className={styles.header}>
      <div>
        <div className={styles.title}>{title}</div>
        {description ? <div className={styles.description}>{description}</div> : null}
      </div>
      {action ? <div>{action}</div> : null}
    </div>
  );
}
