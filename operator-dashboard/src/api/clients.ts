import apiClient from './client';
import { ClientSchema, type Client, type Platform } from '@/types/domain';
import { z } from 'zod';

export interface CreateClientInput {
  name: string;
  email?: string;
  industry?: string;
  businessDescription?: string;
  idealCustomer?: string;
  mainProblemSolved?: string;
  tonePreference?: string;
  platforms?: Platform[];
  customerPainPoints?: string[];
  customerQuestions?: string[];
  keywords?: string[];
  competitors?: string[];
  location?: string;
  founderName?: string;
  brandPersonality?: string[];
  toneToAvoid?: string;
  dataUsage?: string;
  stories?: string[];
  misconceptions?: string[];
  measurableResults?: string;
  postingFrequency?: string;
  mainCta?: string;
  keyPhrases?: string[];
}

export interface UpdateClientInput {
  name?: string;
  email?: string;
  industry?: string;
  businessDescription?: string;
  idealCustomer?: string;
  mainProblemSolved?: string;
  tonePreference?: string;
  platforms?: Platform[];
  customerPainPoints?: string[];
  customerQuestions?: string[];
  keywords?: string[];
  competitors?: string[];
  location?: string;
  founderName?: string;
  brandPersonality?: string[];
  toneToAvoid?: string;
  dataUsage?: string;
  stories?: string[];
  misconceptions?: string[];
  measurableResults?: string;
  postingFrequency?: string;
  mainCta?: string;
  keyPhrases?: string[];
}

export interface SendEmailInput {
  email_type: 'general' | 'deliverable' | 'feedback_request' | 'invoice_reminder' | 'revision_confirmation';
  subject: string;
  content: string;
}

export interface SendEmailResponse {
  success: boolean;
  status: 'sent' | 'logged' | 'failed';
  detail: string;
  communication_id: number;
}

export const clientsApi = {
  async list(archived = false): Promise<Client[]> {
    const { data } = await apiClient.get('/api/clients/', { params: { archived } });
    return z.array(ClientSchema).parse(data);
  },

  async get(clientId: string): Promise<Client> {
    const { data } = await apiClient.get(`/api/clients/${clientId}`);
    return ClientSchema.parse(data);
  },

  async create(input: CreateClientInput): Promise<Client> {
    // Convert camelCase to snake_case for backend compatibility
    // Exclude undefined values to prevent validation errors
    const backendInput: Record<string, string | string[] | Platform[] | undefined> = {
      name: input.name,
    };

    if (input.email !== undefined) backendInput.email = input.email;
    if (input.industry !== undefined) backendInput.industry = input.industry;
    if (input.businessDescription !== undefined) backendInput.business_description = input.businessDescription;
    if (input.idealCustomer !== undefined) backendInput.ideal_customer = input.idealCustomer;
    if (input.mainProblemSolved !== undefined) backendInput.main_problem_solved = input.mainProblemSolved;
    if (input.tonePreference !== undefined) backendInput.tone_preference = input.tonePreference;
    if (input.platforms !== undefined) backendInput.platforms = input.platforms;
    if (input.customerPainPoints !== undefined) backendInput.customer_pain_points = input.customerPainPoints;
    if (input.customerQuestions !== undefined) backendInput.customer_questions = input.customerQuestions;
    // FIX (Bug #45): Add missing fields that were collected but not sent to backend
    if (input.keywords !== undefined) backendInput.keywords = input.keywords;
    if (input.competitors !== undefined) backendInput.competitors = input.competitors;
    if (input.location !== undefined) backendInput.location = input.location;
    if (input.founderName !== undefined) backendInput.founder_name = input.founderName;
    if (input.brandPersonality !== undefined) backendInput.brand_personality = input.brandPersonality;
    if (input.toneToAvoid !== undefined) backendInput.tone_to_avoid = input.toneToAvoid;
    if (input.dataUsage !== undefined) backendInput.data_usage = input.dataUsage;
    if (input.stories !== undefined) backendInput.stories = input.stories;
    if (input.misconceptions !== undefined) backendInput.misconceptions = input.misconceptions;
    if (input.measurableResults !== undefined) backendInput.measurable_results = input.measurableResults;
    if (input.postingFrequency !== undefined) backendInput.posting_frequency = input.postingFrequency;
    if (input.mainCta !== undefined) backendInput.main_cta = input.mainCta;
    if (input.keyPhrases !== undefined) backendInput.key_phrases = input.keyPhrases;

    const { data } = await apiClient.post('/api/clients/', backendInput);
    return ClientSchema.parse(data);
  },

  async update(clientId: string, input: UpdateClientInput): Promise<Client> {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput: Record<string, string | number | string[] | Platform[] | undefined> = {};
    if (input.name !== undefined) backendInput.name = input.name;
    if (input.email !== undefined) backendInput.email = input.email;
    if (input.industry !== undefined) backendInput.industry = input.industry;
    if (input.businessDescription !== undefined) backendInput.business_description = input.businessDescription;
    if (input.idealCustomer !== undefined) backendInput.ideal_customer = input.idealCustomer;
    if (input.mainProblemSolved !== undefined) backendInput.main_problem_solved = input.mainProblemSolved;
    if (input.tonePreference !== undefined) backendInput.tone_preference = input.tonePreference;
    if (input.platforms !== undefined) backendInput.platforms = input.platforms;
    if (input.customerPainPoints !== undefined) backendInput.customer_pain_points = input.customerPainPoints;
    if (input.customerQuestions !== undefined) backendInput.customer_questions = input.customerQuestions;
    // FIX (Bug #45): Add missing fields that were collected but not sent to backend
    if (input.keywords !== undefined) backendInput.keywords = input.keywords;
    if (input.competitors !== undefined) backendInput.competitors = input.competitors;
    if (input.location !== undefined) backendInput.location = input.location;
    if (input.founderName !== undefined) backendInput.founder_name = input.founderName;
    if (input.brandPersonality !== undefined) backendInput.brand_personality = input.brandPersonality;
    if (input.toneToAvoid !== undefined) backendInput.tone_to_avoid = input.toneToAvoid;
    if (input.dataUsage !== undefined) backendInput.data_usage = input.dataUsage;
    if (input.stories !== undefined) backendInput.stories = input.stories;
    if (input.misconceptions !== undefined) backendInput.misconceptions = input.misconceptions;
    if (input.measurableResults !== undefined) backendInput.measurable_results = input.measurableResults;
    if (input.postingFrequency !== undefined) backendInput.posting_frequency = input.postingFrequency;
    if (input.mainCta !== undefined) backendInput.main_cta = input.mainCta;
    if (input.keyPhrases !== undefined) backendInput.key_phrases = input.keyPhrases;

    const { data } = await apiClient.patch(`/api/clients/${clientId}`, backendInput);
    return ClientSchema.parse(data);
  },


  async delete(clientId: string): Promise<void> {
    await apiClient.delete(`/api/clients/${clientId}`);
  },

  async permanentDelete(clientId: string): Promise<void> {
    await apiClient.delete(`/api/clients/${clientId}?force=true`);
  },

  async archive(clientId: string): Promise<void> {
    await apiClient.post(`/api/clients/${clientId}/archive`);
  },

  async unarchive(clientId: string): Promise<void> {
    await apiClient.post(`/api/clients/${clientId}/unarchive`);
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

  async sendEmail(clientId: string, input: SendEmailInput): Promise<SendEmailResponse> {
    const { data } = await apiClient.post(`/api/clients/${clientId}/send-email`, input);
    return data as SendEmailResponse;
  },
};
