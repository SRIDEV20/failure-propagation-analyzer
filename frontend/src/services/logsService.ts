import { fetchLiveSystemState } from './healthService';
import type { LogRecord } from '../types/domain';

export async function fetchLogs(): Promise<LogRecord[]> {
  const liveState = await fetchLiveSystemState();
  return liveState?.logs ?? [];
}
