/**
 * Comprehensive tests for Deliverables API
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { deliverablesApi } from '@/api/deliverables';
import apiClient from '@/api/client';
import type { Deliverable, DeliverableDetails } from '@/types/domain';

jest.mock('@/api/client');
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
          status: 'pending',
          createdAt: '2024-01-01T00:00:00Z',
        },
      ];

      mockedApiClient.get.mockResolvedValue({ data: mockDeliverables } as any);

      const result = await deliverablesApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/', { params: undefined });
      expect(result).toEqual(mockDeliverables);
    });

    it('should fetch deliverables list with clientId filter', async () => {
      const mockDeliverables: Deliverable[] = [];
      mockedApiClient.get.mockResolvedValue({ data: mockDeliverables } as any);

      await deliverablesApi.list({ clientId: 'client-1' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/', {
        params: { clientId: 'client-1' },
      });
    });

    it('should fetch deliverables list with projectId filter', async () => {
      const mockDeliverables: Deliverable[] = [];
      mockedApiClient.get.mockResolvedValue({ data: mockDeliverables } as any);

      await deliverablesApi.list({ projectId: 'proj-1' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/', {
        params: { projectId: 'proj-1' },
      });
    });

    it('should fetch deliverables list with status filter', async () => {
      const mockDeliverables: Deliverable[] = [];
      mockedApiClient.get.mockResolvedValue({ data: mockDeliverables } as any);

      await deliverablesApi.list({ status: 'delivered' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/', {
        params: { status: 'delivered' },
      });
    });

    it('should fetch deliverables list with multiple filters', async () => {
      const mockDeliverables: Deliverable[] = [];
      mockedApiClient.get.mockResolvedValue({ data: mockDeliverables } as any);

      await deliverablesApi.list({
        clientId: 'client-1',
        projectId: 'proj-1',
        status: 'pending',
      });

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/', {
        params: {
          clientId: 'client-1',
          projectId: 'proj-1',
          status: 'pending',
        },
      });
    });
  });

  describe('get', () => {
    it('should fetch single deliverable by id', async () => {
      const mockDeliverable: Deliverable = {
        id: 'del-1',
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'md',
        path: 'deliverable.md',
        status: 'delivered',
        createdAt: '2024-01-01T00:00:00Z',
        deliveredAt: '2024-01-02T00:00:00Z',
      };

      mockedApiClient.get.mockResolvedValue({ data: mockDeliverable } as any);

      const result = await deliverablesApi.get('del-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/del-1');
      expect(result).toEqual(mockDeliverable);
    });
  });

  describe('getDetails', () => {
    it('should fetch deliverable details and parse with schema', async () => {
      const mockDetails: DeliverableDetails = {
        id: 'del-1',
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'docx',
        path: 'deliverable.docx',
        status: 'delivered',
        createdAt: '2024-01-01T00:00:00Z',
        deliveredAt: '2024-01-02T00:00:00Z',
        proofUrl: 'https://example.com/proof',
        proofNotes: 'Delivered via email',
        runId: 'run-1',
      };

      mockedApiClient.get.mockResolvedValue({ data: mockDetails } as any);

      const result = await deliverablesApi.getDetails('del-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/del-1/details');
      expect(result).toEqual(mockDetails);
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
        status: 'pending',
        createdAt: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockDeliverable } as any);

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

    it('should create deliverable without runId', async () => {
      const mockDeliverable: Deliverable = {
        id: 'del-1',
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'md',
        path: 'output.md',
        status: 'pending',
        createdAt: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockDeliverable } as any);

      const input = {
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'md' as const,
        path: 'output.md',
      };

      await deliverablesApi.create(input);

      expect(apiClient.post).toHaveBeenCalledWith('/api/deliverables/', {
        project_id: 'proj-1',
        client_id: 'client-1',
        format: 'md',
        path: 'output.md',
        run_id: undefined,
      });
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
        status: 'pending',
        createdAt: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockDeliverable } as any);

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

      mockedApiClient.patch.mockResolvedValue({ data: mockDeliverable } as any);

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

    it('should mark deliverable as delivered with minimal fields', async () => {
      const mockDeliverable: Deliverable = {
        id: 'del-1',
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'txt',
        path: 'output.txt',
        status: 'delivered',
        createdAt: '2024-01-01T00:00:00Z',
        deliveredAt: '2024-01-02T00:00:00Z',
      };

      mockedApiClient.patch.mockResolvedValue({ data: mockDeliverable } as any);

      const input = {
        deliveredAt: '2024-01-02T00:00:00Z',
      };

      await deliverablesApi.markDelivered('del-1', input);

      expect(apiClient.patch).toHaveBeenCalledWith('/api/deliverables/del-1/mark-delivered', {
        delivered_at: '2024-01-02T00:00:00Z',
        proof_url: undefined,
        proof_notes: undefined,
      });
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
      } as any);

      const result = await deliverablesApi.download('del-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/deliverables/del-1/download', {
        responseType: 'blob',
      });
      expect(result.blob).toBe(mockBlob);
      expect(result.filename).toBe('deliverable.txt');
    });

    it('should download deliverable with filename without quotes', async () => {
      const mockBlob = new Blob(['content'], { type: 'text/plain' });
      mockedApiClient.get.mockResolvedValue({
        data: mockBlob,
        headers: {
          'content-disposition': 'attachment; filename=deliverable.txt',
        },
      } as any);

      const result = await deliverablesApi.download('del-1');

      expect(result.filename).toBe('deliverable.txt');
    });

    it('should use default filename when Content-Disposition is missing', async () => {
      const mockBlob = new Blob(['content'], { type: 'text/plain' });
      mockedApiClient.get.mockResolvedValue({
        data: mockBlob,
        headers: {},
      } as any);

      const result = await deliverablesApi.download('del-1');

      expect(result.filename).toBe('download');
    });

    it('should use default filename when Content-Disposition has no filename', async () => {
      const mockBlob = new Blob(['content'], { type: 'text/plain' });
      mockedApiClient.get.mockResolvedValue({
        data: mockBlob,
        headers: {
          'content-disposition': 'attachment',
        },
      } as any);

      const result = await deliverablesApi.download('del-1');

      expect(result.filename).toBe('download');
    });

    it('should handle filename with complex Content-Disposition format', async () => {
      const mockBlob = new Blob(['content'], { type: 'text/plain' });
      mockedApiClient.get.mockResolvedValue({
        data: mockBlob,
        headers: {
          'content-disposition': 'attachment; filename="my-file-2024.docx"; size=1024',
        },
      } as any);

      const result = await deliverablesApi.download('del-1');

      expect(result.filename).toBe('my-file-2024.docx');
    });
  });
});
