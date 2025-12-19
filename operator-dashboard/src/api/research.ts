import apiClient from './client';

export interface ResearchTool {
  name: string;
  label: string;
  price?: number;
  status?: 'available' | 'coming_soon';
  description?: string;
  category?: string;
}

export interface RunResearchInput {
  projectId: string;
  clientId: string;
  tool: string;
  params?: Record<string, unknown>;
}

export interface ResearchRunResult {
  tool: string;
  outputs: Record<string, string>;
  metadata?: Record<string, unknown>;
}

export const researchApi = {
  async listTools() {
    const { data } = await apiClient.get<ResearchTool[]>('/api/research/tools');
    return data;
  },

  async run(input: RunResearchInput) {
    const { data } = await apiClient.post<ResearchRunResult>('/api/research/run', input);
    return data;
  },
};
