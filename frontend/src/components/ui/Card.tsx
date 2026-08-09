import type { ReactNode } from 'react';
import styles from './Card.module.css';

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`${styles.card} ${className}`.trim()}>{children}</section>;
}
