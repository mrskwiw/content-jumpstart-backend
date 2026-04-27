import apiClient from './client';

export interface AuditUser {
  id: string;
  name: string;
  email: string;
  role: string;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  user: AuditUser;
  action: string;
  actionType: 'create' | 'read' | 'update' | 'delete' | 'export' | 'system' | 'security';
  resource: string;
  resourceType: 'project' | 'deliverable' | 'user' | 'settings' | 'template' | 'client' | 'post' | 'brief';
  details: string;
  ipAddress: string;
  status: 'success' | 'failed' | 'warning';
  metadata?: Record<string, unknown>;
}

export interface ComplianceStats {
  totalEvents: number;
  todayEvents: number;
  failedActions: number;
  securityEvents: number;
  avgEventsPerDay: number;
  retentionDays: number;
}

export interface AuditFilters {
  skip?: number;
  limit?: number;
  action_type?: string;
  resource_type?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
}

export const auditApi = {
  async list(filters?: AuditFilters): Promise<AuditEntry[]> {
    const { data } = await apiClient.get<AuditEntry[]>('/api/audit/', { params: filters });
    return data;
  },

  async stats(): Promise<ComplianceStats> {
    const { data } = await apiClient.get<ComplianceStats>('/api/audit/stats');
    return data;
  },

  exportUrl(format: 'csv' | 'json', filters?: AuditFilters): string {
    const params = new URLSearchParams();
    if (filters?.action_type && filters.action_type !== 'all') params.set('action_type', filters.action_type);
    if (filters?.resource_type && filters.resource_type !== 'all') params.set('resource_type', filters.resource_type);
    if (filters?.status && filters.status !== 'all') params.set('status', filters.status);
    if (filters?.date_from) params.set('date_from', filters.date_from);
    if (filters?.date_to) params.set('date_to', filters.date_to);
    const qs = params.toString();
    return `/api/audit/export.${format}${qs ? `?${qs}` : ''}`;
  },
};
