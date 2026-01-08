import apiClient from './client';
import type { Client, Platform } from '@/types/domain';

export interface CreateClientInput {
  name: string;
  email?: string;
  businessDescription?: string;
  idealCustomer?: string;
  mainProblemSolved?: string;
  tonePreference?: string;
  platforms?: Platform[];
  customerPainPoints?: string[];
  customerQuestions?: string[];
}

export interface UpdateClientInput {
  name?: string;
  email?: string;
  businessDescription?: string;
  idealCustomer?: string;
  mainProblemSolved?: string;
  tonePreference?: string;
  platforms?: Platform[];
  customerPainPoints?: string[];
  customerQuestions?: string[];
}

export const clientsApi = {
  async list() {
    const { data } = await apiClient.get<Client[]>('/api/clients/');
    return data;
  },

  async get(clientId: string) {
    const { data } = await apiClient.get<Client>(`/api/clients/${clientId}`);
    return data;
  },

  async create(input: CreateClientInput) {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput = {
      name: input.name,
      email: input.email,
      business_description: input.businessDescription,
      ideal_customer: input.idealCustomer,
      main_problem_solved: input.mainProblemSolved,
      tone_preference: input.tonePreference,
      platforms: input.platforms,
      customer_pain_points: input.customerPainPoints,
      customer_questions: input.customerQuestions,
    };
    const { data } = await apiClient.post<Client>('/api/clients/', backendInput);
    return data;
  },

  async update(clientId: string, input: UpdateClientInput) {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput: Record<string, string | number | string[] | Platform[] | undefined> = {};
    if (input.name !== undefined) backendInput.name = input.name;
    if (input.email !== undefined) backendInput.email = input.email;
    if (input.businessDescription !== undefined) backendInput.business_description = input.businessDescription;
    if (input.idealCustomer !== undefined) backendInput.ideal_customer = input.idealCustomer;
    if (input.mainProblemSolved !== undefined) backendInput.main_problem_solved = input.mainProblemSolved;
    if (input.tonePreference !== undefined) backendInput.tone_preference = input.tonePreference;
    if (input.platforms !== undefined) backendInput.platforms = input.platforms;
    if (input.customerPainPoints !== undefined) backendInput.customer_pain_points = input.customerPainPoints;
    if (input.customerQuestions !== undefined) backendInput.customer_questions = input.customerQuestions;

    const { data } = await apiClient.patch<Client>(`/api/clients/${clientId}`, backendInput);
    return data;
  },

  async exportProfile(clientId: string): Promise<{ blob: Blob; filename: string }> {
    const response = await apiClient.get(`/api/clients/${clientId}/export-profile`, {
      responseType: 'blob',
    });

    // Extract filename from Content-Disposition header if available
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'client_profile.md';

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
