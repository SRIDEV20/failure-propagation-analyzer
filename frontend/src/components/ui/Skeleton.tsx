import styles from './Skeleton.module.css';

export function Skeleton({ height = 120 }: { height?: number }) {
  return <div className={styles.skeleton} style={{ height }} />;
}
