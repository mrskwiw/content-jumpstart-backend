import apiClient from './client';
import type { PostDraft } from '@/types/domain';
import type { PaginatedResponse, PaginationParams } from '@/types/pagination';

export interface PostFilters extends PaginationParams {
  projectId?: string;
  runId?: string;
  status?: string;
}

export const postsApi = {
  /**
   * List posts with pagination support (Week 3 optimization)
   *
   * The backend automatically uses hybrid pagination:
   * - Pages 1-5: Offset pagination (fast, provides total count)
   * - Pages 6+: Cursor pagination (O(1) performance for deep pages)
   *
   * @param filters - Filter and pagination parameters
   * @returns Paginated response with posts and metadata
   */
  async list(filters?: PostFilters): Promise<PaginatedResponse<PostDraft>> {
    const { data } = await apiClient.get<PaginatedResponse<PostDraft>>('/api/posts', { params: filters });
    return data;
  },

  /**
   * Legacy list method for backward compatibility
   * Returns just the items array without pagination metadata
   *
   * @deprecated Use list() which returns PaginatedResponse instead
   */
  async listLegacy(filters?: Omit<PostFilters, keyof PaginationParams>): Promise<PostDraft[]> {
    const response = await this.list(filters);
    return response.items;
  },
};
