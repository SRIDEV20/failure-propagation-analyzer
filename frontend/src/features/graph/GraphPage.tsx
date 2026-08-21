import { useEffect, useMemo, useState } from 'react';
import ReactFlow, { Background, Controls, MarkerType, MiniMap } from 'reactflow';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { SectionHeader } from '../../components/ui/SectionHeader';
import { useDashboard } from '../../context/DashboardContext';
import { statusColor } from '../../utils/analyzer';
import type { ServiceSnapshot } from '../../types/domain';
import styles from './GraphPage.module.css';

function labelTone(service: ServiceSnapshot) {
  if (service.finalHealth === 'failed') {
    return 'danger';
  }

  if (service.finalHealth === 'degraded') {
    return 'warning';
  }

  return 'success';
}

export function GraphPage() {
  const { data } = useDashboard();
  const [selectedService, setSelectedService] = useState<ServiceSnapshot | null>(data.services[0] ?? null);

  useEffect(() => {
    if (!selectedService || !data.services.some((service) => service.name === selectedService.name)) {
      setSelectedService(data.services[0] ?? null);
    }
  }, [data.services, selectedService]);

  const nodes = useMemo(
    () =>
      data.graph.nodes.map((node) => ({
        ...node,
        style: {
          width: 170,
          borderRadius: 18,
          border: `1px solid ${statusColor(node.data.status)}`,
          background:
            node.data.status === 'failed'
              ? 'rgba(255, 92, 124, 0.16)'
              : node.data.status === 'degraded'
                ? 'rgba(245, 158, 11, 0.14)'
                : 'rgba(57, 217, 138, 0.12)',
          color: '#fff',
          boxShadow: '0 12px 28px rgba(0, 0, 0, 0.25)',
        },
      })),
    [data.graph.nodes],
  );

  const edges = useMemo(
    () =>
      data.graph.edges.map((edge) => ({
        ...edge,
        animated: true,
        type: 'smoothstep' as const,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: 'rgba(148, 163, 184, 0.75)',
        },
        style: {
          stroke: edge.animated ? 'rgba(255, 92, 124, 0.76)' : 'rgba(148, 163, 184, 0.35)',
          strokeWidth: 1.6,
        },
      })),
    [data.graph.edges],
  );

  const onNodeClick = (_: unknown, node: { id: string }) => {
    setSelectedService(data.services.find((service) => service.name === node.id) ?? null);
  };

  return (
    <div className={styles.page}>
      <Card className={styles.graphCard}>
        <SectionHeader
          title="Service Dependency Graph"
          description="Use zoom, pan, and node selection to inspect propagation paths across the topology."
        />
        <div className={styles.flowWrap}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            onNodeClick={onNodeClick}
            className={styles.flow}
            minZoom={0.2}
            maxZoom={1.4}
          >
            <MiniMap zoomable pannable />
            <Controls />
            <Background gap={18} size={1} color="rgba(148, 163, 184, 0.16)" />
          </ReactFlow>
        </div>
      </Card>

      <div className={styles.sideRail}>
        <Card className={styles.sidebarCard}>
          <SectionHeader title="Node Details" description="Service-level health, dependencies, and impact signals." />
          {selectedService ? (
            <div className={styles.details}>
              <div className={styles.detailsHeader}>
                <div>
                  <div className={styles.serviceName}>{selectedService.name}</div>
                  <div className={styles.detailLine}>Local health: {selectedService.localHealth}</div>
                </div>
                <Badge tone={labelTone(selectedService)}>{selectedService.finalHealth}</Badge>
              </div>

              <div className={styles.metricsGrid}>
                <div>
                  <div className={styles.metricLabel}>Operational impact score</div>
                  <div className={styles.metricValue}>{selectedService.operationalImpactScore ?? selectedService.impactScore}</div>
                </div>
                <div>
                  <div className={styles.metricLabel}>Confidence</div>
                  <div className={styles.metricValue}>{selectedService.confidence}%</div>
                </div>
                <div>
                  <div className={styles.metricLabel}>Blast radius</div>
                  <div className={styles.metricValue}>{selectedService.blastRadius}</div>
                </div>
              </div>

              <div className={styles.section}>
                <div className={styles.sectionLabel}>Dependencies</div>
                <div className={styles.flowText}>{selectedService.dependencies.join(', ') || 'None'}</div>
              </div>

              <div className={styles.section}>
                <div className={styles.sectionLabel}>Dependents</div>
                <div className={styles.flowText}>{selectedService.dependents.join(', ') || 'None'}</div>
              </div>

              <div className={styles.section}>
                <div className={styles.sectionLabel}>Metrics</div>
                <div className={styles.flowText}>
                  Latency {selectedService.metrics.latency_ms ?? 'n/a'} ms, error rate {selectedService.metrics.error_rate ?? 'n/a'}, timeout{' '}
                  {String(selectedService.metrics.timeout ?? false)}
                </div>
              </div>
            </div>
          ) : null}
        </Card>

        <Card className={styles.sidebarCard}>
          <SectionHeader title="Legend" description="Color mapping follows service health and propagation state." />
          <div className={styles.legend}>
            <div className={styles.legendItem}><span className={styles.dotHealthy} />Healthy</div>
            <div className={styles.legendItem}><span className={styles.dotDegraded} />Degraded</div>
            <div className={styles.legendItem}><span className={styles.dotFailed} />Failed</div>
          </div>
        </Card>
      </div>
    </div>
  );
}
