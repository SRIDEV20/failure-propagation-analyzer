import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { Skeleton } from '../../components/ui/Skeleton';
import { useDashboard } from '../../context/DashboardContext';
import { GraphPreview } from './GraphPreview';
import { ImpactPreview } from './ImpactPreview';
import { KpiGrid } from './KpiGrid';
import { LiveAlertsPanel } from './LiveAlertsPanel';
import { RecentEvents } from './RecentEvents';
import { RootCausePanel } from './RootCausePanel';
import styles from './OverviewPage.module.css';

export function OverviewPage() {
  const { data, loading, error } = useDashboard();

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div>
          <Badge tone={data.connectionState === 'live' ? 'success' : 'info'}>
            {data.connectionState === 'live' ? 'Live backend connected' : 'Backend unavailable'}
          </Badge>
          <h1 className={styles.heading}>Monitor dependency cascades before they become incidents.</h1>
          <p className={styles.lead}>
            A dark, production-style observability surface for failure propagation, root cause analysis, alert triage,
            and blast-radius inspection.
          </p>
        </div>

        <Card className={styles.summaryCard}>
          <div className={styles.summaryTitle}>Current focus</div>
          <div className={styles.summaryValue}>
            {data.summary.failed > 0 ? 'Active failure propagation detected' : 'All monitored services are stable'}
          </div>
          <div className={styles.summaryNote}>Last sync {new Date(data.lastSyncedAt).toLocaleTimeString()}</div>
        </Card>
      </section>

      {error ? <Card className={styles.errorCard}>{error}</Card> : null}

      {loading ? <Skeleton height={140} /> : <KpiGrid summary={data.summary} />}

      <div className={styles.grid}>
        <Card className={styles.wideCard}>
          <SectionHeader title="Live Dependency Graph Preview" description="Compact topology snapshot driven by the current system state." />
          <GraphPreview />
        </Card>

        <Card className={styles.sideCard}>
          <SectionHeader title="Live Alerts" description="The most important active and recent alerts." />
          <LiveAlertsPanel alerts={data.alerts} />
        </Card>

        <Card className={styles.sideCard}>
          <SectionHeader title="Root Cause Analysis" description="Primary causes and propagation context." />
          <RootCausePanel services={data.services} />
        </Card>

        <Card className={styles.wideCard}>
          <SectionHeader title="Impact Ranking Preview" description="Services ranked by blast radius and operational importance." />
          <ImpactPreview impact={data.impact} />
        </Card>

        <Card className={styles.wideCard}>
          <SectionHeader title="Recent Events" description="A concise timeline of service activity and incident signals." />
          <RecentEvents logs={data.logs} />
        </Card>
      </div>
    </div>
  );
}
