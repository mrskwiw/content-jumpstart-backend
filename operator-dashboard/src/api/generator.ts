import apiClient from './client';
import type { ExportInput, GenerateAllInput, RegenerateInput, Run } from '@/types/domain';
import type { Deliverable } from '@/types/domain';

export const generatorApi = {
  async generateAll(input: GenerateAllInput) {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput = {
      project_id: input.projectId,
      client_id: input.clientId,
      is_batch: input.isBatch ?? true,
    };
    const { data } = await apiClient.post<Run>('/api/generator/generate-all', backendInput);
    return data;
  },

  async regenerate(input: RegenerateInput) {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput = {
      project_id: input.projectId,
      post_ids: input.postIds,
      reason: input.reason,
    };
    const { data } = await apiClient.post<Run>('/api/generator/regenerate', backendInput);
    return data;
  },

  async exportPackage(input: ExportInput) {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput = {
      project_id: input.projectId,
      client_id: input.clientId,
      format: input.format,
    };
    const { data } = await apiClient.post<Deliverable>('/api/generator/export', backendInput);
    return data;
  },
};
