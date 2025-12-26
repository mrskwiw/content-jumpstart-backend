import apiClient from './client';
import type { Run } from '@/types/domain';

export interface RunFilters {
  projectId?: string;
}

export const runsApi = {
  async list(filters?: RunFilters) {
    const { data } = await apiClient.get<Run[]>('/api/runs/', { params: filters });
    return data;
  },

  async get(runId: string) {
    const { data } = await apiClient.get<Run>(`/api/runs/${runId}`);
    return data;
  },
};
