import apiClient from './client';
import type { ExportInput, GenerateAllInput, RegenerateInput, Run } from '@/types/domain';
import type { Deliverable } from '@/types/domain';

export const generatorApi = {
  async generateAll(input: GenerateAllInput) {
    const { data } = await apiClient.post<Run>('/api/generator/generate-all', input);
    return data;
  },

  async regenerate(input: RegenerateInput) {
    const { data } = await apiClient.post<Run>('/api/generator/regenerate', input);
    return data;
  },

  async exportPackage(input: ExportInput) {
    const { data } = await apiClient.post<Deliverable>('/api/generator/export', input);
    return data;
  },
};
