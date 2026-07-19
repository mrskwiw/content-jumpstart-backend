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
  const response = await apiClient.delete(`/api/privacy/clients/${clientId}?cascade=${cascade}`);
  return response.data;
}

/**
 * Anonymize client PII while preserving analytics
 */
export async function anonymizeClient(
  clientId: string
): Promise<AnonymizeClientResponse> {
  const response = await apiClient.post(`/api/privacy/clients/${clientId}/anonymize`);
  return response.data;
}

/**
 * Export all client data (GDPR Article 15 / CCPA Right to Know)
 */
export async function exportClientData(
  clientId: string
): Promise<ExportClientDataResponse> {
  const response = await apiClient.get(`/api/privacy/clients/${clientId}/export`);
  return response.data;
}

/**
 * Restore a soft-deleted client (within 90-day recovery period)
 */
export async function restoreClient(
  clientId: string
): Promise<{ status: string; client_id: string }> {
  const response = await apiClient.post(`/api/privacy/clients/${clientId}/restore`);
  return response.data;
}

/**
 * Export the entire instance database as a single JSON bundle (superuser only).
 * GDPR/CCPA data portability — intended for a customer migrating elsewhere.
 */
export async function exportInstanceData(): Promise<unknown> {
  const response = await apiClient.get('/api/privacy/instance/export');
  return response.data;
}

/**
 * Trigger a browser download of an arbitrary JSON payload.
 */
export function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename.endsWith('.json') ? filename : `${filename}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Download exported client data as JSON file
 */
export function downloadClientData(data: ExportClientDataResponse, clientName: string) {
  downloadJson(data, `${clientName}_data_export`);
}
