import styles from './Badge.module.css';

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: string;
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info';
}) {
  return <span className={`${styles.badge} ${styles[tone]}`}>{children}</span>;
}
