/**
 * Tests for projects API module
 */
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { projectsApi } from '../projects';
import apiClient from '../client';
import type { Project } from '@/types/domain';
import type { PaginatedResponse } from '@/types/pagination';

// Mock the API client
jest.mock('../client');

const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('Projects API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('list', () => {
    it('should fetch paginated projects', async () => {
      const mockResponse: PaginatedResponse<Project> = {
        items: [
          {
            id: 'proj-1',
            clientId: 'client-1',
            name: 'Project 1',
            status: 'draft',
            numPosts: 30,
            platforms: ['linkedin' as const],
            templates: ['1', '2'],
            pricePerPost: 40,
            totalPrice: 1200,
            tone: 'professional',
            createdAt: '2024-01-01T00:00:00Z',
            updatedAt: '2024-01-01T00:00:00Z',
          },
        ],
        metadata: {
          page_size: 10,
          has_next: false,
          has_prev: false,
          strategy: 'offset' as const,
        },
      };

      mockedApiClient.get.mockResolvedValue({ data: mockResponse } as any);

      const result = await projectsApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/api/projects/', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('should pass filter parameters', async () => {
      const mockResponse: PaginatedResponse<Project> = {
        items: [],
        metadata: {
          page_size: 10,
          has_next: false,
          has_prev: false,
          strategy: 'offset' as const,
        },
      };

      mockedApiClient.get.mockResolvedValue({ data: mockResponse } as any);

      await projectsApi.list({ clientId: 'client-1', status: 'draft', page: 2 });

      expect(apiClient.get).toHaveBeenCalledWith('/api/projects/', {
        params: { clientId: 'client-1', status: 'draft', page: 2 },
      });
    });
  });

  describe('get', () => {
    it('should fetch single project by ID', async () => {
      const mockProject: Project = {
        id: 'proj-1',
        clientId: 'client-1',
        name: 'Test Project',
        status: 'draft',
        numPosts: 30,
        platforms: ['linkedin'],
        templates: ['1'],
        pricePerPost: 40,
        totalPrice: 1200,
        tone: 'professional',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.get.mockResolvedValue({ data: mockProject } as any);

      const result = await projectsApi.get('proj-1');

      expect(apiClient.get).toHaveBeenCalledWith('/api/projects/proj-1');
      expect(result).toEqual(mockProject);
    });
  });

  describe('create', () => {
    it('should create project with camelCase to snake_case conversion', async () => {
      const input = {
        clientId: 'client-1',
        name: 'New Project',
        templates: ['1', '2'],
        platforms: ['linkedin'],
        numPosts: 30,
        pricePerPost: 40,
        totalPrice: 1200,
      };

      const mockResponse: Project = {
        id: 'proj-new',
        clientId: input.clientId,
        name: input.name,
        templates: input.templates,
        platforms: ['linkedin' as const],
        numPosts: input.numPosts,
        pricePerPost: input.pricePerPost,
        totalPrice: input.totalPrice,
        status: 'draft',
        tone: 'professional',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockResponse } as any);

      const result = await projectsApi.create(input);

      expect(apiClient.post).toHaveBeenCalledWith('/api/projects/', {
        client_id: 'client-1',
        name: 'New Project',
        templates: ['1', '2'],
        template_quantities: undefined,
        num_posts: 30,
        total_price: 1200,
        posts_cost: undefined,
        research_addon_cost: undefined,
        tools_cost: undefined,
        discount_amount: undefined,
        selected_tools: undefined,
        platforms: ['linkedin'],
        tone: undefined,
      });

      expect(result).toEqual(mockResponse);
    });
  });

  describe('update', () => {
    it('should update project with snake_case conversion', async () => {
      const input = {
        name: 'Updated Project',
        status: 'ready' as const,
      };

      const mockResponse: Project = {
        id: 'proj-1',
        clientId: 'client-1',
        name: 'Updated Project',
        status: 'ready',
        numPosts: 30,
        platforms: ['linkedin'],
        templates: ['1'],
        pricePerPost: 40,
        totalPrice: 1200,
        tone: 'professional',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-02T00:00:00Z',
      };

      mockedApiClient.patch.mockResolvedValue({ data: mockResponse } as any);

      const result = await projectsApi.update('proj-1', input);

      expect(apiClient.patch).toHaveBeenCalledWith('/api/projects/proj-1', {
        name: 'Updated Project',
        status: 'ready',
        templates: undefined,
        template_quantities: undefined,
        price_per_post: undefined,
        research_price_per_post: undefined,
        total_price: undefined,
        posts_cost: undefined,
        research_addon_cost: undefined,
        tools_cost: undefined,
        discount_amount: undefined,
        selected_tools: undefined,
        platforms: undefined,
        tone: undefined,
      });

      expect(result).toEqual(mockResponse);
    });
  });
});
