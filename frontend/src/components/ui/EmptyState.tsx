import styles from './EmptyState.module.css';

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className={styles.empty}>
      <div className={styles.title}>{title}</div>
      <div className={styles.description}>{description}</div>
    </div>
  );
}
