/**
 * Comprehensive tests for Runs API
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { runsApi } from '@/api/runs';
import apiClient from '@/api/client';
import type { Run } from '@/types/domain';

jest.mock('@/api/client');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('runsApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('list', () => {
    it('should fetch runs list without filters', async () => {
      const mockRuns: Run[] = [
        {
          id: 'run-1',
          projectId: 'proj-1',
          status: 'succeeded',
          startedAt: '2024-01-01T00:00:00Z',
          completedAt: '2024-01-01T01:00:00Z',
          postsGenerated: 30,
        },
        {
          id: 'run-2',
          projectId: 'proj-1',
          status: 'running',
          startedAt: '2024-01-02T00:00:00Z',
          postsGenerated: 15,
        },
      ];

      mockedApiClient.get.mockResolvedValue({ data: mockRuns } as any);

      const result = await runsApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/api/runs/', { params: undefined });
      expect(result).toEqual(mockRuns);
    });

    it('should fetch runs list with projectId filter', async () => {
      const mockRuns: Run[] = [
        {
          id: 'run-1',
          projectId: 'proj-1',
          status: 'succeeded',
          startedAt: '2024-01-01T00:00:00Z',
          completedAt: '2024-01-01T01:00:00Z',
          postsGenerated: 30,
        },
      ];

      mockedApiClient.get.mockResolvedValue({ data: mockRuns } as any);

      const result = await runsApi.list({ projectId: 'proj-1' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/runs/', {
        params: { projectId: 'proj-1' },
      });
      expect(result).toEqual(mockRuns);
    });

    it('should handle empty runs list', async () => {
      mockedApiClient.get.mockResolvedValue({ data: [] } as any);

      const result = await runsApi.list();

      expect(result).toEqual([]);
    });

    it('should handle runs with different statuses', async () => {
      const mockRuns: Run[] = [
        {
          id: 'run-1',
          projectId: 'proj-1',
          status: 'succeeded',
          startedAt: '2024-01-01T00:00:00Z',
          completedAt: '2024-01-01T01:00:00Z',
          postsGenerated: 30,
        },
        {
          id: 'run-2',
          projectId: 'proj-1',
          status: 'failed',
          startedAt: '2024-01-01T02:00:00Z',
          completedAt: '2024-01-01T02:30:00Z',
          postsGenerated: 10,
          error: 'API timeout',
        },
        {
          id: 'run-3',
          projectId: 'proj-1',
          status: 'running',
          startedAt: '2024-01-01T03:00:00Z',
          postsGenerated: 5,
        },
      ];

      mockedApiClient.get.mockResolvedValue({ data: mockRuns } as any);

      const result = await runsApi.list({ projectId: 'proj-1' });

      expect(result).toHaveLength(3);
      expect(result[0].status).toBe('succeeded');
      expect(result[1].status).toBe('failed');
      expect(result[2].status).toBe('running');
    });
  });

  describe('get', () => {
    it('should fetch single run by id', async () => {
      const mockRun: Run = {
        id: 'run-1',
        projectId: 'proj-1',
        status: 'succeeded',
        startedAt: '2024-01-01T00:00:00Z',
        completedAt: '2024-01-01T01:00:00Z',
        postsGenerated: 30,
      };

      mockedApiClient.get.mockResolvedValue({ data: mockRun } as any);

      const result = await runsApi.get('run-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/runs/run-1');
      expect(result).toEqual(mockRun);
    });

    it('should fetch run with error details', async () => {
      const mockRun: Run = {
        id: 'run-2',
        projectId: 'proj-1',
        status: 'failed',
        startedAt: '2024-01-01T00:00:00Z',
        completedAt: '2024-01-01T00:30:00Z',
        postsGenerated: 12,
        error: 'Claude API rate limit exceeded',
      };

      mockedApiClient.get.mockResolvedValue({ data: mockRun } as any);

      const result = await runsApi.get('run-2');

      expect(result.status).toBe('failed');
      expect(result.error).toBe('Claude API rate limit exceeded');
    });

    it('should fetch running run without completedAt', async () => {
      const mockRun: Run = {
        id: 'run-3',
        projectId: 'proj-1',
        status: 'running',
        startedAt: '2024-01-01T00:00:00Z',
        postsGenerated: 15,
      };

      mockedApiClient.get.mockResolvedValue({ data: mockRun } as any);

      const result = await runsApi.get('run-3');

      expect(result.status).toBe('running');
      expect(result.completedAt).toBeUndefined();
    });

    it('should fetch run with metadata', async () => {
      const mockRun: Run = {
        id: 'run-4',
        projectId: 'proj-1',
        status: 'succeeded',
        startedAt: '2024-01-01T00:00:00Z',
        completedAt: '2024-01-01T01:00:00Z',
        postsGenerated: 30,
        durationSeconds: 3600,
        tokensUsed: 155000,
        estimatedCost: 0.465,
      };

      mockedApiClient.get.mockResolvedValue({ data: mockRun } as any);

      const result = await runsApi.get('run-4');

      expect(result.durationSeconds).toBe(3600);
      expect(result.tokensUsed).toBe(155000);
      expect(result.estimatedCost).toBe(0.465);
    });
  });
});
