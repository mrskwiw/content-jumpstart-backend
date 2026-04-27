import apiClient from './client';
import { ProjectSchema, type Project, type ProjectStatus } from '@/types/domain';
import { createPaginatedResponseSchema, type PaginatedResponse, type PaginationParams } from '@/types/pagination';

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
  numPosts?: number; // Total post count
  // pricePerPost removed - credits only
  // researchPricePerPost removed: Tools use credits (Bug #51)
  totalPrice?: number; // Total project price
  postsCost?: number; // Post generation cost (num_posts * price_per_post)
  researchAddonCost?: number; // Per-post topic research cost
  toolsCost?: number; // Research tool cost after bundle discount
  discountAmount?: number; // Bundle discount savings
  selectedTools?: string[]; // List of selected research tool IDs
  platforms: string[];
  targetPlatform?: string;
  tone?: string;
}

export interface UpdateProjectInput {
  name?: string;
  status?: ProjectStatus;
  templates?: string[]; // Legacy field
  templateQuantities?: Record<number, number>; // New field: template_id -> quantity
  // pricePerPost removed - credits only
  // researchPricePerPost removed: Tools use credits (Bug #51)
  totalPrice?: number;
  postsCost?: number;
  researchAddonCost?: number;
  toolsCost?: number;
  discountAmount?: number;
  selectedTools?: string[];
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
    const { data } = await apiClient.get('/api/projects/', { params });
    const schema = createPaginatedResponseSchema(ProjectSchema);
    return schema.parse(data);
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

  async get(projectId: string): Promise<Project> {
    const { data } = await apiClient.get(`/api/projects/${projectId}`);
    return ProjectSchema.parse(data);
  },

  async create(input: CreateProjectInput): Promise<Project> {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput = {
      name: input.name,
      client_id: input.clientId,  // Convert clientId -> client_id
      templates: input.templates,
      template_quantities: input.templateQuantities ?
        Object.fromEntries(
          Object.entries(input.templateQuantities).map(([id, qty]) => [id.toString(), qty])
        ) : undefined,  // Convert to string keys for JSON
      num_posts: input.numPosts,
      // price_per_post removed
      // research_price_per_post removed (Bug #51)
      total_price: input.totalPrice,
      posts_cost: input.postsCost,
      research_addon_cost: input.researchAddonCost,
      tools_cost: input.toolsCost,
      discount_amount: input.discountAmount,
      selected_tools: input.selectedTools,
      platforms: input.platforms,
      target_platform: input.targetPlatform,
      tone: input.tone,
    };
    const { data } = await apiClient.post('/api/projects/', backendInput);
    return ProjectSchema.parse(data);
  },

  async update(projectId: string, input: UpdateProjectInput): Promise<Project> {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput: Record<string, string | number | string[] | Record<string, number> | undefined> = {};
    if (input.name !== undefined) backendInput.name = input.name;
    if (input.status !== undefined) backendInput.status = input.status;
    if (input.templates !== undefined) backendInput.templates = input.templates;
    if (input.templateQuantities !== undefined) {
      backendInput.template_quantities = Object.fromEntries(
        Object.entries(input.templateQuantities).map(([id, qty]) => [id.toString(), qty])
      );
    }
    if (input.totalPrice !== undefined) backendInput.total_price = input.totalPrice;
    if (input.postsCost !== undefined) backendInput.posts_cost = input.postsCost;
    if (input.researchAddonCost !== undefined) backendInput.research_addon_cost = input.researchAddonCost;
    if (input.toolsCost !== undefined) backendInput.tools_cost = input.toolsCost;
    if (input.discountAmount !== undefined) backendInput.discount_amount = input.discountAmount;
    if (input.selectedTools !== undefined) backendInput.selected_tools = input.selectedTools;
    if (input.platforms !== undefined) backendInput.platforms = input.platforms;
    if (input.tone !== undefined) backendInput.tone = input.tone;

    const { data } = await apiClient.patch(`/api/projects/${projectId}`, backendInput);
    return ProjectSchema.parse(data);
  },
};
