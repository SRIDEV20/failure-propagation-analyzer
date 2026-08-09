import { apiClient } from './apiClient';
import type { BackendSystemState } from '../types/api';

export async function fetchLiveSystemState(): Promise<BackendSystemState | null> {
  const response = await apiClient.get<BackendSystemState>('/state');
  return response.data;
}
