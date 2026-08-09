import { fetchLiveSystemState } from './healthService';
import type { AlertRecord } from '../types/domain';

export async function fetchAlerts(): Promise<AlertRecord[]> {
  const liveState = await fetchLiveSystemState();
  return liveState?.alerts ?? [];
}
