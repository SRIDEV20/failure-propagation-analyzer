import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { useDashboard } from '../../context/DashboardContext';
import styles from './ImpactPage.module.css';

const chartColors = ['#ff5c7c', '#f59e0b', '#38bdf8', '#39d98a', '#8b5cf6', '#4f8cff'];

export function ImpactPage() {
  const { data } = useDashboard();
  const topServices = data.impact.slice(0, 6);
  const trendServices = topServices.filter((item) => item.trend.length > 0).slice(0, 3);

  const healthDistribution = [
    { name: 'Healthy', value: data.summary.healthy, color: '#39d98a' },
    { name: 'Degraded', value: data.summary.degraded, color: '#f59e0b' },
    { name: 'Failed', value: data.summary.failed, color: '#ff5c7c' },
  ].filter((item) => item.value > 0);

  const trendLength = Math.max(...trendServices.map((item) => item.trend.length), 0);
  const trendData = Array.from({ length: trendLength }, (_, index) => {
    const point: Record<string, string | number> = { label: `T-${trendLength - index - 1}` };
    trendServices.forEach((service) => {
      point[service.service] = service.trend[index] ?? 0;
    });
    return point;
  });

  if (data.impact.length === 0) {
    return (
      <div className={styles.page}>
        <Card className={styles.chartCard}>
          <EmptyState title="No impact data" description="The backend has not returned any live impact metrics yet." />
        </Card>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.grid}>
        <Card className={styles.chartCard}>
          <SectionHeader title="Operational Impact Scores" description="Services ranked by operational importance and blast radius." />
          <div className={styles.chartBox}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topServices} margin={{ top: 10, right: 14, left: 0, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.12)" />
                <XAxis dataKey="service" stroke="#94a3b8" tickLine={false} axisLine={false} />
                <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#0d1728', border: '1px solid rgba(148, 163, 184, 0.2)' }} />
                <Bar dataKey="impactScore" radius={[10, 10, 0, 0]}>
                  {topServices.map((entry, index) => (
                    <Cell key={entry.service} fill={chartColors[index % chartColors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className={styles.chartCard}>
          <SectionHeader title="Propagation Trends" description="Historical propagation points returned by the backend." />
          <div className={styles.chartBox}>
            {trendServices.length === 0 ? (
              <EmptyState title="No historical trend data" description="The live impact response does not currently contain trend points for the monitored services." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 10, right: 14, left: 0, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.12)" />
                  <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: '#0d1728', border: '1px solid rgba(148, 163, 184, 0.2)' }} />
                  {trendServices.map((service, index) => (
                    <Line
                      key={service.service}
                      type="monotone"
                      dataKey={service.service}
                      name={service.service}
                      stroke={chartColors[index % chartColors.length]}
                      strokeWidth={3}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card className={styles.chartCard}>
          <SectionHeader title="Health Distribution" description="Current operational mix across monitored services." />
          <div className={styles.chartBoxSmall}>
            {healthDistribution.length === 0 ? (
              <EmptyState title="No health data" description="The backend has not reported service health counts yet." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={healthDistribution} dataKey="value" nameKey="name" innerRadius={80} outerRadius={120} paddingAngle={4}>
                    {healthDistribution.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#0d1728', border: '1px solid rgba(148, 163, 184, 0.2)' }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card className={styles.chartCard}>
          <SectionHeader title="Propagation Statistics" description="Incidents, blast radius, and rank weighting." />
          <div className={styles.statsList}>
            {data.impact.slice(0, 5).map((item) => (
              <div key={item.service} className={styles.statRow}>
                <div>
                  <div className={styles.statTitle}>{item.service}</div>
                  <div className={styles.statMeta}>Blast radius {item.blastRadius} • {item.incidents} incidents</div>
                </div>
                <div className={styles.statValue}>{item.operationalImpactScore ?? item.impactScore}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
