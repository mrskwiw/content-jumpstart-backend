import apiClient from './client';
import type { Deliverable, DeliverableDetails, DeliverableStatus, MarkDeliveredInput } from '@/types/domain';
import { isSafeRelativePath } from '@/utils/guards';
import { DeliverableDetailsSchema } from '@/types/domain';

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
    const { data } = await apiClient.get<Deliverable[]>('/api/deliverables/', { params: filters });
    return data;
  },

  async get(deliverableId: string) {
    const { data } = await apiClient.get<Deliverable>(`/api/deliverables/${deliverableId}`);
    return data;
  },

  async getDetails(deliverableId: string): Promise<DeliverableDetails> {
    const { data } = await apiClient.get(`/api/deliverables/${deliverableId}/details`);
    return DeliverableDetailsSchema.parse(data);
  },

  async create(input: CreateDeliverableInput) {
    if (!isSafeRelativePath(input.path)) {
      throw new Error('Deliverable path must be relative and safe.');
    }
    // Convert camelCase to snake_case for backend compatibility
    const backendInput = {
      project_id: input.projectId,
      client_id: input.clientId,
      format: input.format,
      path: input.path,
      run_id: input.runId,
    };
    const { data } = await apiClient.post<Deliverable>('/api/deliverables/', backendInput);
    return data;
  },

  async markDelivered(deliverableId: string, input: MarkDeliveredInput) {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput = {
      delivered_at: input.deliveredAt,
      proof_url: input.proofUrl,
      proof_notes: input.proofNotes,
    };
    const { data } = await apiClient.post<Deliverable>(
      `/api/deliverables/${deliverableId}/deliver`,
      backendInput
    );
    return data;
  },

  async download(deliverableId: string): Promise<{ blob: Blob; filename: string }> {
    const response = await apiClient.get(`/api/deliverables/${deliverableId}/download`, {
      responseType: 'blob',
    });

    // Extract filename from Content-Disposition header if available
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'download';

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/"/g, '');
      }
    }

    return {
      blob: response.data,
      filename,
    };
  },
};
