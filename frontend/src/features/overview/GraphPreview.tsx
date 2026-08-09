import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import { EmptyState } from '../../components/ui/EmptyState';
import { useDashboard } from '../../context/DashboardContext';
import { statusColor } from '../../utils/analyzer';
import styles from './GraphPreview.module.css';

export function GraphPreview() {
  const { data } = useDashboard();

  if (data.graph.nodes.length === 0) {
    return <EmptyState title="No live topology data" description="The backend has not returned any dependency graph records yet." />;
  }

  const nodes = data.graph.nodes.slice(0, 9).map((node) => ({
    ...node,
    draggable: false,
    selectable: false,
    style: {
      borderRadius: 16,
      border: `1px solid ${statusColor(node.data.status)}`,
      background:
        node.data.status === 'failed'
          ? 'rgba(255, 92, 124, 0.16)'
          : node.data.status === 'degraded'
            ? 'rgba(245, 158, 11, 0.14)'
            : 'rgba(57, 217, 138, 0.12)',
      color: '#fff',
      width: 140,
      padding: 6,
      boxShadow: '0 10px 24px rgba(0, 0, 0, 0.22)',
    },
  }));
  const edges = data.graph.edges.slice(0, 12).map((edge) => ({
    ...edge,
    style: { stroke: 'rgba(148, 163, 184, 0.35)', strokeWidth: 1.4 },
  }));

  return (
    <div className={styles.preview}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        zoomOnScroll={false}
        panOnDrag={false}
        nodesDraggable={false}
        nodesConnectable={false}
        className={styles.flow}
      >
        <MiniMap zoomable pannable />
        <Controls showInteractive={false} />
        <Background gap={18} size={1} color="rgba(148, 163, 184, 0.14)" />
      </ReactFlow>
    </div>
  );
}
