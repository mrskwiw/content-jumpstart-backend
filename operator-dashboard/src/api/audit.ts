import apiClient from './client';
import type { AuditEntry } from '@/types/domain';

export interface AuditFilters {
  targetType?: string;
  targetId?: string;
  limit?: number;
}

export const auditApi = {
  async list(filters?: AuditFilters) {
    const { data } = await apiClient.get<AuditEntry[]>('/api/audit', { params: filters });
    return data;
  },
};
