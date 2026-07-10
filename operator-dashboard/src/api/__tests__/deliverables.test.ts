/**
 * Comprehensive tests for Deliverables API
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import type { AxiosResponse } from 'axios';
import { deliverablesApi } from '../deliverables';
import apiClient from '../client';
import type { Deliverable } from '@/types/domain';

jest.mock('../client');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('deliverablesApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('list', () => {
    it('should fetch deliverables list without filters', async () => {
      const mockDeliverables: Deliverable[] = [
        {
          id: 'del-1',
          projectId: 'proj-1',
          clientId: 'client-1',
          format: 'txt',
          path: 'deliverable.txt',
          status: 'draft',
          createdAt: '2024-01-01T00:00:00Z',
        },
      ];

      mockedApiClient.get.mockResolvedValue({ data: mockDeliverables } as unknown as AxiosResponse);

      const result = await deliverablesApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/', { params: {} });
      expect(result).toEqual(mockDeliverables);
    });

    it('should fetch deliverables list with clientId filter', async () => {
      const mockDeliverables: Deliverable[] = [];
      mockedApiClient.get.mockResolvedValue({ data: mockDeliverables } as unknown as AxiosResponse);

      await deliverablesApi.list({ clientId: 'client-1' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/', {
        params: { client_id: 'client-1' },
      });
    });

    it('should fetch deliverables list with multiple filters', async () => {
      const mockDeliverables: Deliverable[] = [];
      mockedApiClient.get.mockResolvedValue({ data: mockDeliverables } as unknown as AxiosResponse);

      await deliverablesApi.list({
        clientId: 'client-1',
        projectId: 'proj-1',
        status: 'ready',
      });

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/', {
        params: {
          client_id: 'client-1',
          project_id: 'proj-1',
          status: 'ready',
        },
      });
    });
  });

  describe('create', () => {
    it('should create deliverable with camelCase to snake_case conversion', async () => {
      const mockDeliverable: Deliverable = {
        id: 'del-1',
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'txt',
        path: 'output.txt',
        status: 'draft',
        createdAt: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockDeliverable } as unknown as AxiosResponse);

      const input = {
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'txt' as const,
        path: 'output.txt',
        runId: 'run-1',
      };

      const result = await deliverablesApi.create(input);

      expect(apiClient.post).toHaveBeenCalledWith('/api/deliverables/', {
        project_id: 'proj-1',
        client_id: 'client-1',
        format: 'txt',
        path: 'output.txt',
        run_id: 'run-1',
      });
      expect(result).toEqual(mockDeliverable);
    });

    it('should reject unsafe paths with .. navigation', async () => {
      const input = {
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'txt' as const,
        path: '../../../etc/passwd',
      };

      await expect(deliverablesApi.create(input)).rejects.toThrow(
        'Deliverable path must be relative and safe.'
      );

      expect(apiClient.post).not.toHaveBeenCalled();
    });

    it('should reject absolute paths', async () => {
      const input = {
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'txt' as const,
        path: '/etc/passwd',
      };

      await expect(deliverablesApi.create(input)).rejects.toThrow(
        'Deliverable path must be relative and safe.'
      );

      expect(apiClient.post).not.toHaveBeenCalled();
    });

    it('should accept safe relative paths', async () => {
      const mockDeliverable: Deliverable = {
        id: 'del-1',
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'txt',
        path: 'subfolder/output.txt',
        status: 'draft',
        createdAt: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockDeliverable } as unknown as AxiosResponse);

      const input = {
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'txt' as const,
        path: 'subfolder/output.txt',
      };

      await deliverablesApi.create(input);

      expect(apiClient.post).toHaveBeenCalled();
    });
  });

  describe('download', () => {
    it('should download deliverable with filename from Content-Disposition header', async () => {
      const mockBlob = new Blob(['content'], { type: 'text/plain' });
      mockedApiClient.get.mockResolvedValue({
        data: mockBlob,
        headers: {
          'content-disposition': 'attachment; filename="deliverable.txt"',
        },
      } as unknown as AxiosResponse);

      const result = await deliverablesApi.download('del-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/del-1/download', {
        responseType: 'blob',
      });
      expect(result.blob).toBe(mockBlob);
      expect(result.filename).toBe('deliverable.txt');
    });

    it('should use default filename when Content-Disposition is missing', async () => {
      const mockBlob = new Blob(['content'], { type: 'text/plain' });
      mockedApiClient.get.mockResolvedValue({
        data: mockBlob,
        headers: {},
      } as unknown as AxiosResponse);

      const result = await deliverablesApi.download('del-1');

      expect(result.filename).toBe('deliverable');
    });

    it('should handle filename extraction correctly', async () => {
      const mockBlob = new Blob(['content'], { type: 'text/plain' });
      mockedApiClient.get.mockResolvedValue({
        data: mockBlob,
        headers: {
          'content-disposition': 'attachment; filename="report-2024.docx"',
        },
      } as unknown as AxiosResponse);

      const result = await deliverablesApi.download('del-1');

      expect(result.filename).toBe('report-2024.docx');
    });
  });

  describe('markDelivered', () => {
    it('should mark deliverable as delivered with all fields', async () => {
      const mockDeliverable: Deliverable = {
        id: 'del-1',
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'txt',
        path: 'output.txt',
        status: 'delivered',
        createdAt: '2024-01-01T00:00:00Z',
        deliveredAt: '2024-01-02T00:00:00Z',
        proofUrl: 'https://example.com/proof',
        proofNotes: 'Sent via email',
      };

      mockedApiClient.patch.mockResolvedValue({ data: mockDeliverable } as unknown as AxiosResponse);

      const input = {
        deliveredAt: '2024-01-02T00:00:00Z',
        proofUrl: 'https://example.com/proof',
        proofNotes: 'Sent via email',
      };

      const result = await deliverablesApi.markDelivered('del-1', input);

      expect(apiClient.patch).toHaveBeenCalledWith('/api/deliverables/del-1/mark-delivered', {
        delivered_at: '2024-01-02T00:00:00Z',
        proof_url: 'https://example.com/proof',
        proof_notes: 'Sent via email',
      });
      expect(result).toEqual(mockDeliverable);
    });
  });
});
