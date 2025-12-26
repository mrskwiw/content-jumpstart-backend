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
  templates: string[]; // Legacy field for backward compatibility
  templateQuantities?: Record<number, number>; // New field: template_id -> quantity
  pricePerPost?: number; // Price per post ($40 base, $55 with research)
  researchPricePerPost?: number; // Research add-on price per post ($15)
  totalPrice?: number; // Total project price
  platforms: string[];
  tone?: string;
}

export interface UpdateProjectInput {
  name?: string;
  status?: ProjectStatus;
  templates?: string[]; // Legacy field
  templateQuantities?: Record<number, number>; // New field: template_id -> quantity
  pricePerPost?: number;
  researchPricePerPost?: number;
  totalPrice?: number;
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
    const { data } = await apiClient.get<PaginatedResponse<Project>>('/api/projects/', { params });
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
    // Convert camelCase to snake_case for backend compatibility
    const backendInput = {
      name: input.name,
      client_id: input.clientId,  // Convert clientId -> client_id
      templates: input.templates,
      template_quantities: input.templateQuantities ?
        Object.fromEntries(
          Object.entries(input.templateQuantities).map(([id, qty]) => [id.toString(), qty])
        ) : undefined,  // Convert to string keys for JSON
      price_per_post: input.pricePerPost,
      research_price_per_post: input.researchPricePerPost,
      total_price: input.totalPrice,
      platforms: input.platforms,
      tone: input.tone,
    };
    const { data } = await apiClient.post<Project>('/api/projects/', backendInput);
    return data;
  },

  async update(projectId: string, input: UpdateProjectInput) {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput: any = {};
    if (input.name !== undefined) backendInput.name = input.name;
    if (input.status !== undefined) backendInput.status = input.status;
    if (input.templates !== undefined) backendInput.templates = input.templates;
    if (input.templateQuantities !== undefined) {
      backendInput.template_quantities = Object.fromEntries(
        Object.entries(input.templateQuantities).map(([id, qty]) => [id.toString(), qty])
      );
    }
    if (input.pricePerPost !== undefined) backendInput.price_per_post = input.pricePerPost;
    if (input.researchPricePerPost !== undefined) backendInput.research_price_per_post = input.researchPricePerPost;
    if (input.totalPrice !== undefined) backendInput.total_price = input.totalPrice;
    if (input.platforms !== undefined) backendInput.platforms = input.platforms;
    if (input.tone !== undefined) backendInput.tone = input.tone;

    const { data } = await apiClient.patch<Project>(`/api/projects/${projectId}`, backendInput);
    return data;
  },
};
