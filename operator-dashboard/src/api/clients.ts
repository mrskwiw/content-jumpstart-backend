import apiClient from './client';
import type { Client } from '@/types/domain';

export interface CreateClientInput {
  name: string;
  email?: string;
}

export interface UpdateClientInput {
  name?: string;
  email?: string;
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
    const { data } = await apiClient.post<Client>('/api/clients/', input);
    return data;
  },

  async update(clientId: string, input: UpdateClientInput) {
    const { data } = await apiClient.patch<Client>(`/api/clients/${clientId}`, input);
    return data;
  },
};
