import { fetchLiveSystemState } from './healthService';
import type { ImpactRecord } from '../types/domain';

export async function fetchImpact(): Promise<ImpactRecord[]> {
  const liveState = await fetchLiveSystemState();
  return liveState?.impact ?? [];
}
