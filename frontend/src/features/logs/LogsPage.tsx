import { useMemo, useState } from 'react';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { SearchInput } from '../../components/ui/SearchInput';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { Tabs } from '../../components/ui/Tabs';
import { useDashboard } from '../../context/DashboardContext';
import styles from './LogsPage.module.css';

const levelOptions = [
  { value: 'all', label: 'All' },
  { value: 'ERROR', label: 'Error' },
  { value: 'WARN', label: 'Warn' },
  { value: 'INFO', label: 'Info' },
] as const;

const pageSize = 6;

type LevelFilter = (typeof levelOptions)[number]['value'];

export function LogsPage() {
  const { data } = useDashboard();
  const [query, setQuery] = useState('');
  const [serviceFilter, setServiceFilter] = useState('all');
  const [levelFilter, setLevelFilter] = useState<LevelFilter>('all');
  const [page, setPage] = useState(0);

  const services = useMemo(() => ['all', ...new Set(data.logs.map((log) => log.service))], [data.logs]);

  const filtered = data.logs.filter((log) => {
    const matchesQuery = [log.service, log.message, log.details, log.timestamp].join(' ').toLowerCase().includes(query.toLowerCase());
    const matchesService = serviceFilter === 'all' || log.service === serviceFilter;
    const matchesLevel = levelFilter === 'all' || log.level === levelFilter;
    return matchesQuery && matchesService && matchesLevel;
  });

  const visibleLogs = filtered.slice(page * pageSize, page * pageSize + pageSize);
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));

  return (
    <div className={styles.page}>
      <Card className={styles.card}>
        <SectionHeader
          title="Logs"
          description="Search by message, service, or timestamp. Filter by service, severity, and page through recent events."
        />

        <div className={styles.controls}>
          <SearchInput value={query} onChange={setQuery} placeholder="Search logs" />
          <Tabs value={levelFilter} options={[...levelOptions]} onChange={setLevelFilter} />
          <select className={styles.select} value={serviceFilter} onChange={(event) => setServiceFilter(event.target.value)}>
            {services.map((service) => (
              <option key={service} value={service}>
                {service}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.table}>
          <div className={styles.head}>
            <div>Timestamp</div>
            <div>Service</div>
            <div>Level</div>
            <div>Message</div>
            <div>Details</div>
          </div>

          {visibleLogs.length === 0 ? (
            <EmptyState title="No log events" description="The logging source returned no entries for the current filters." />
          ) : (
            visibleLogs.map((log) => (
              <div key={log.id} className={styles.row}>
                <div>{log.timestamp}</div>
                <div>{log.service}</div>
                <div className={`${styles.level} ${styles[log.level.toLowerCase()]}`}>{log.level}</div>
                <div>{log.message}</div>
                <div>{log.details}</div>
              </div>
            ))
          )}
        </div>

        <div className={styles.pagination}>
          <button type="button" onClick={() => setPage((current) => Math.max(0, current - 1))} disabled={page === 0}>
            Previous
          </button>
          <div>
            Page {page + 1} of {totalPages}
          </div>
          <button type="button" onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))} disabled={page + 1 >= totalPages}>
            Next
          </button>
        </div>
      </Card>
    </div>
  );
}
