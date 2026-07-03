/**
 * Tests for posts API module
 */
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { postsApi } from '../posts';
import apiClient from '../client';
import type { PaginatedResponse } from '@/types/pagination';
import type { PostDraft } from '@/types/domain';

// Mock the API client
jest.mock('../client');

const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('Posts API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('list', () => {
    it('should fetch paginated posts', async () => {
      const mockResponse: PaginatedResponse<PostDraft> = {
        items: [],
        metadata: {
          page_size: 10,
          has_next: false,
          has_prev: false,
          strategy: 'offset' as const,
        },
      };

      mockedApiClient.get.mockResolvedValue({ data: mockResponse } as any);

      const result = await postsApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/api/posts/', { params: {} });
      expect(result).toEqual(mockResponse);
    });

    it('should convert camelCase to snake_case in filters', async () => {
      mockedApiClient.get.mockResolvedValue({ data: { items: [], metadata: { page_size: 10, has_next: false, has_prev: false, strategy: 'offset' as const } } } as any);

      await postsApi.list({ projectId: 'proj-1', runId: 'run-1' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/posts/', {
        params: { project_id: 'proj-1', run_id: 'run-1' },
      });
    });
  });

  describe('get', () => {
    it('should fetch single post', async () => {
      const mockPost = { id: 'post-1', content: 'Test' };
      mockedApiClient.get.mockResolvedValue({ data: mockPost } as any);

      const result = await postsApi.get('post-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/posts/post-1');
      expect(result).toEqual(mockPost);
    });
  });

  describe('update', () => {
    it('should update post content', async () => {
      const mockPost = { id: 'post-1', content: 'Updated' };
      mockedApiClient.patch.mockResolvedValue({ data: mockPost } as any);

      await postsApi.update('post-1', { content: 'Updated' });

      expect(apiClient.patch).toHaveBeenCalledWith('/api/posts/post-1', { content: 'Updated' });
    });
  });
});
