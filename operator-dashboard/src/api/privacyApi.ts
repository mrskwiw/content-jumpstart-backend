/**
 * Privacy API Client - GDPR/CCPA Compliance
 */
import apiClient from './client';
import type { Client, Project, ResearchResult } from '@/types/domain';

export interface DeleteClientResponse {
  status: string;
  client_id: string;
  deleted_at: string;
  cascade: boolean;
  deleted_counts: {
    client: number;
    projects: number;
    posts: number;
    research_results: number;
  };
  recovery_period_days: number;
  message: string;
}

export interface AnonymizeClientResponse {
  status: string;
  client_id: string;
  anonymized_at: string;
}

export interface ExportClientDataResponse {
  export_metadata: {
    client_id: string;
    exported_at: string;
    format: string;
  };
  client: Client;
  projects: Project[];
  research_results: ResearchResult[];
}

/**
 * Soft delete a client (GDPR Article 17 / CCPA Section 1798.105)
 */
export async function deleteClient(
  clientId: string,
  cascade: boolean = true
): Promise<DeleteClientResponse> {
  const response = await apiClient.delete(`/api/clients/${clientId}/privacy/delete?cascade=${cascade}`);
  return response.data;
}

/**
 * Anonymize client PII while preserving analytics
 */
export async function anonymizeClient(
  clientId: string
): Promise<AnonymizeClientResponse> {
  const response = await apiClient.post(`/api/clients/${clientId}/privacy/anonymize`);
  return response.data;
}

/**
 * Export all client data (GDPR Article 15 / CCPA Right to Know)
 */
export async function exportClientData(
  clientId: string
): Promise<ExportClientDataResponse> {
  const response = await apiClient.get(`/api/clients/${clientId}/privacy/export`);
  return response.data;
}

/**
 * Restore a soft-deleted client (within 90-day recovery period)
 */
export async function restoreClient(
  clientId: string
): Promise<{ status: string; client_id: string }> {
  const response = await apiClient.post(`/api/clients/${clientId}/privacy/restore`);
  return response.data;
}

/**
 * Download exported client data as JSON file
 */
export function downloadClientData(data: ExportClientDataResponse, clientName: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${clientName}_data_export.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
