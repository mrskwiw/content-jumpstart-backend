import apiClient from './client';
import type { Project, ProjectStatus } from '@/types/domain';
import type { PaginatedResponse, PaginationParams } from '@/types/pagination';

export interface ProjectFilters extends PaginationParams {
  clientId?: string;
  status?: ProjectStatus;
  search?: string;
}

export interface CreateProjectInput {
  clientId: string;
  name: string;
  templates: string[];
  platforms: string[];
  tone?: string;
}

export interface UpdateProjectInput {
  name?: string;
  status?: ProjectStatus;
  templates?: string[];
  platforms?: string[];
  tone?: string;
}

export const projectsApi = {
  /**
   * List projects with pagination support (Week 3 optimization)
   *
   * The backend automatically uses hybrid pagination:
   * - Pages 1-5: Offset pagination (fast, provides total count)
   * - Pages 6+: Cursor pagination (O(1) performance for deep pages)
   *
   * @param params - Filter and pagination parameters
   * @returns Paginated response with projects and metadata
   */
  async list(params?: ProjectFilters): Promise<PaginatedResponse<Project>> {
    const { data } = await apiClient.get<PaginatedResponse<Project>>('/api/projects', { params });
    return data;
  },

  /**
   * Legacy list method for backward compatibility
   * Returns just the items array without pagination metadata
   *
   * @deprecated Use list() which returns PaginatedResponse instead
   */
  async listLegacy(params?: Omit<ProjectFilters, keyof PaginationParams>): Promise<Project[]> {
    const response = await this.list(params);
    return response.items;
  },

  async get(projectId: string) {
    const { data } = await apiClient.get<Project>(`/api/projects/${projectId}`);
    return data;
  },

  async create(input: CreateProjectInput) {
    const { data } = await apiClient.post<Project>('/api/projects', input);
    return data;
  },

  async update(projectId: string, input: UpdateProjectInput) {
    const { data } = await apiClient.patch<Project>(`/api/projects/${projectId}`, input);
    return data;
  },
};
