/**
 * Tests for clients API module
 */
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { clientsApi } from '../clients';
import apiClient from '../client';
import type { Client } from '@/types/domain';

// Mock the API client
jest.mock('../client');

const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('Clients API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('list', () => {
    it('should fetch all clients', async () => {
      const mockClients: Client[] = [
        {
          id: 'client-1',
          name: 'Test Client',
          businessDescription: 'Test description',
          createdAt: '2026-01-01T00:00:00Z',
        },
      ];

      mockedApiClient.get.mockResolvedValue({ data: mockClients } as any);

      const result = await clientsApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/api/clients/', { params: { archived: false } });
      expect(result).toEqual(mockClients);
    });
  });

  describe('get', () => {
    it('should fetch a single client by ID', async () => {
      const mockClient: Client = {
        id: 'client-1',
        name: 'Test Client',
        businessDescription: 'Test description',
        createdAt: '2026-01-01T00:00:00Z',
      };

      mockedApiClient.get.mockResolvedValue({ data: mockClient } as any);

      const result = await clientsApi.get('client-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/clients/client-1');
      expect(result).toEqual(mockClient);
    });
  });

  describe('create', () => {
    it('should create a client with only required fields', async () => {
      const input = {
        name: 'New Client',
      };

      const mockResponse: Client = {
        id: 'client-new',
        name: 'New Client',
        createdAt: '2026-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockResponse } as any);

      const result = await clientsApi.create(input);

      expect(apiClient.post).toHaveBeenCalledWith('/api/clients/', {
        name: 'New Client',
      });

      expect(result).toEqual(mockResponse);
    });

    it('should convert camelCase to snake_case for backend', async () => {
      const input = {
        name: 'Test Client',
        businessDescription: 'Test business',
        idealCustomer: 'B2B',
        mainProblemSolved: 'Problem',
        tonePreference: 'professional',
        customerPainPoints: ['Pain 1'],
        customerQuestions: ['Question 1'],
      };

      mockedApiClient.post.mockResolvedValue({
        data: { id: 'client-x', name: 'Test Client', createdAt: '2026-01-01T00:00:00Z' } as any,
      } as any);

      await clientsApi.create(input);

      expect(apiClient.post).toHaveBeenCalledWith('/api/clients/', {
        name: 'Test Client',
        business_description: 'Test business',
        ideal_customer: 'B2B',
        main_problem_solved: 'Problem',
        tone_preference: 'professional',
        customer_pain_points: ['Pain 1'],
        customer_questions: ['Question 1'],
      });
    });
  });

  describe('update', () => {
    it('should update client with camelCase to snake_case conversion', async () => {
      const input = {
        name: 'Updated',
        businessDescription: 'Updated desc',
      };

      mockedApiClient.patch.mockResolvedValue({
        data: { id: 'client-1', name: 'Updated', createdAt: '2026-01-01T00:00:00Z' } as any,
      } as any);

      await clientsApi.update('client-1', input);

      expect(apiClient.patch).toHaveBeenCalledWith('/api/clients/client-1', {
        name: 'Updated',
        business_description: 'Updated desc',
      });
    });
  });

  describe('exportProfile', () => {
    it('should export client profile and extract filename', async () => {
      const mockBlob = new Blob(['content']);
      mockedApiClient.get.mockResolvedValue({
        data: mockBlob,
        headers: { 'content-disposition': 'attachment; filename="profile.md"' },
      } as any);

      const result = await clientsApi.exportProfile('client-1');

      expect(result.blob).toBe(mockBlob);
      expect(result.filename).toBe('profile.md');
    });
  });
});
