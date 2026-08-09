import { fetchLiveSystemState } from './healthService';
import type { GraphView } from '../types/domain';

export async function fetchGraphView(): Promise<GraphView> {
  const liveState = await fetchLiveSystemState();
  return liveState?.graph ?? { nodes: [], edges: [] };
}
