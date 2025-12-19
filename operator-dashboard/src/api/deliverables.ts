import apiClient from './client';
import type { Deliverable, DeliverableStatus, MarkDeliveredInput } from '@/types/domain';
import { isSafeRelativePath } from '@/utils/guards';

export interface DeliverableFilters {
  clientId?: string;
  projectId?: string;
  status?: DeliverableStatus;
}

export interface CreateDeliverableInput {
  projectId: string;
  clientId: string;
  format: 'txt' | 'docx';
  path: string;
  runId?: string;
}

export const deliverablesApi = {
  async list(filters?: DeliverableFilters) {
    const { data } = await apiClient.get<Deliverable[]>('/api/deliverables', { params: filters });
    return data;
  },

  async get(deliverableId: string) {
    const { data } = await apiClient.get<Deliverable>(`/api/deliverables/${deliverableId}`);
    return data;
  },

  async create(input: CreateDeliverableInput) {
    if (!isSafeRelativePath(input.path)) {
      throw new Error('Deliverable path must be relative and safe.');
    }
    const { data } = await apiClient.post<Deliverable>('/api/deliverables', input);
    return data;
  },

  async markDelivered(deliverableId: string, input: MarkDeliveredInput) {
    const { data } = await apiClient.post<Deliverable>(
      `/api/deliverables/${deliverableId}/deliver`,
      input
    );
    return data;
  },
};
