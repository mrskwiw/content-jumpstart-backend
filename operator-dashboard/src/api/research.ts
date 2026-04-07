import apiClient from './client';
import { ResearchResultSchema, type ResearchResult } from '../types/domain';
import { z } from 'zod';

// Zod schemas for runtime validation
const ResearchToolSchema = z.object({
  name: z.string(),
  label: z.string(),
  credits: z.number().optional(),
  status: z.enum(['available', 'coming_soon', 'experimental']).optional(),
  description: z.string().optional(),
  category: z.string().optional(),
  required_integrations: z.array(z.string()).optional(),
});

export interface ResearchTool {
  name: string;
  label: string;
  credits?: number;  // Credit cost (not dollars)
  status?: 'available' | 'coming_soon' | 'experimental';
  description?: string;
  category?: string;
  required_integrations?: string[];
}

export interface RunResearchInput {
  projectId: string;
  clientId: string;
  tool: string;
  params?: Record<string, unknown>;
}

const ResearchRunResultSchema = z.object({
  tool: z.string(),
  outputs: z.record(z.string(), z.string()),
  metadata: z.record(z.string(), z.unknown()).optional(),
});

const ResearchResultHistorySchema = z.object({
  id: z.string(),
  toolName: z.string(),
  toolLabel: z.string().optional(),
  createdAt: z.string(),
  status: z.string(),
  durationSeconds: z.number().optional(),
});

const ResearchHistoryResponseSchema = z.object({
  results: z.array(ResearchResultHistorySchema),
  total: z.number(),
  clientId: z.string(),
});

const ResearchResultListResponseSchema = z.object({
  results: z.array(ResearchResultSchema),
  total: z.number(),
  clientId: z.string().nullish(),
  projectId: z.string().nullish(),
});

export interface ResearchRunResult {
  tool: string;
  outputs: Record<string, string>;
  metadata?: Record<string, unknown>;
}

export interface ResearchResultHistory {
  id: string;
  toolName: string;
  toolLabel?: string;
  createdAt: string;  // ISO 8601
  status: string;
  durationSeconds?: number;
}

export interface ResearchHistoryResponse {
  results: ResearchResultHistory[];
  total: number;
  clientId: string;
}

export interface ResearchResultListResponse {
  results: ResearchResult[];
  total: number;
  clientId?: string | null;
  projectId?: string | null;
}

const NextBundleSuggestionSchema = z.object({
  bundle: z.string(),
  bundleName: z.string(),
  missingTools: z.array(z.string()),
  missingToolNames: z.array(z.string()),
  additionalCost: z.number(),
  potentialSavings: z.number(),
});

const PricingPreviewSchema = z.object({
  baseCost: z.number(),
  discount: z.number(),
  finalCost: z.number(),
  bundleApplied: z.string().nullable(),
  bundleName: z.string().nullable(),
  savingsPercent: z.number(),
  nextBundleSuggestion: NextBundleSuggestionSchema.optional(),
});

export interface NextBundleSuggestion {
  bundle: string;
  bundleName: string;
  missingTools: string[];
  missingToolNames: string[];
  additionalCost: number;  // Credits
  potentialSavings: number;  // Credits
}

export interface PricingPreview {
  baseCost: number;  // Total credits needed
  discount: number;  // Always 0 (no discounts)
  finalCost: number;  // Same as baseCost
  bundleApplied: string | null;  // Always null
  bundleName: string | null;  // Always null
  savingsPercent: number;  // Always 0
  nextBundleSuggestion?: NextBundleSuggestion;  // Always undefined
}

export interface ToolStats {
  toolName: string;
  toolLabel: string;
  executionCount: number;
  totalRevenue: number;
  totalApiCost: number;
}

export interface ResearchAnalytics {
  totalRevenue: number;
  totalApiCost: number;
  profitMargin: number;
  totalExecutions: number;
  cacheHitRate: number;
  cacheSavings: number;
  avgCostPerTool: number;
  topTools: ToolStats[];
  dateRange: number;
}


// Client prerequisite checking
export interface ClientToolStatus {
  toolName: string;
  canRun: boolean;
  completed: boolean;  // Has this tool been run for this client
  missingRequired: string[];
  missingRecommended: string[];
  lastRunAt?: string;  // ISO 8601 timestamp of last run
}

export interface ClientPrerequisiteResponse {
  clientId: string;
  tools: ClientToolStatus[];
  completedTools: string[];  // All tools completed for this client
}

const ClientToolStatusSchema = z.object({
  tool_name: z.string(),
  can_run: z.boolean(),
  completed: z.boolean(),
  missing_required: z.array(z.string()),
  missing_recommended: z.array(z.string()),
  last_run_at: z.string().nullable().optional(),
});

const ClientPrerequisiteResponseSchema = z.object({
  client_id: z.string(),
  tools: z.array(ClientToolStatusSchema),
  completed_tools: z.array(z.string()),
});

export const researchApi = {
  async listTools(): Promise<ResearchTool[]> {
    const { data } = await apiClient.get('/api/research/tools');
    return z.array(ResearchToolSchema).parse(data);
  },

  async run(input: RunResearchInput): Promise<ResearchRunResult> {
    // Convert camelCase to snake_case for backend compatibility
    const backendInput = {
      project_id: input.projectId,
      client_id: input.clientId,
      tool: input.tool,
      params: input.params,
    };
    const { data } = await apiClient.post('/api/research/run', backendInput);
    return ResearchRunResultSchema.parse(data);
  },

  async getClientHistory(clientId: string, toolName?: string): Promise<ResearchHistoryResponse> {
    const params = toolName ? { tool_name: toolName } : {};
    const { data } = await apiClient.get(
      `/api/research/results/client/${clientId}`,
      { params }
    );
    return ResearchHistoryResponseSchema.parse(data);
  },

  /**
   * Fetch full research results for a client (includes outputs, data, etc.)
   * Returns full response with results array, total count, and IDs
   */
  async getClientResearchResults(clientId: string, toolName?: string): Promise<ResearchResultListResponse> {
    const params = toolName ? { tool_name: toolName } : {};
    const { data } = await apiClient.get(
      `/api/research/results/client/${clientId}`,
      { params }
    );
    return ResearchResultListResponseSchema.parse(data);
  },

  /**
   * Fetch full research results for a project (includes outputs, data, etc.)
   * Returns full response with results array, total count, and IDs
   */
  async getProjectResearchResults(projectId: string, toolName?: string): Promise<ResearchResultListResponse> {
    const params = toolName ? { tool_name: toolName } : {};
    const { data } = await apiClient.get(
      `/api/research/results/project/${projectId}`,
      { params }
    );
    return ResearchResultListResponseSchema.parse(data);
  },

  /**
   * Fetch all research results for the current user across all clients/projects.
   * Supports optional filtering by tool name, client ID, and date range.
   */
  async getAllResults(params?: {
    toolName?: string;
    clientId?: string;
    days?: number;
  }): Promise<ResearchResultListResponse> {
    const query: Record<string, string | number> = {};
    if (params?.toolName && params.toolName !== 'all') query.tool_name = params.toolName;
    if (params?.clientId && params.clientId !== 'all') query.client_id = params.clientId;
    if (params?.days) query.days = params.days;
    const { data } = await apiClient.get('/api/research/results/', { params: query });
    return ResearchResultListResponseSchema.parse(data);
  },

  /**
   * Fetch the content of a research result output file
   */
  async getResearchOutputContent(
    resultId: string,
    outputFormat: string
  ): Promise<{ content: string; format: string }> {
    const { data } = await apiClient.get(
      `/api/research/results/${resultId}/output/${outputFormat}`
    );
    const schema = z.object({ content: z.string(), format: z.string() });
    return schema.parse(data);
  },

  /**
   * Delete a research result
   */
  async deleteResult(resultId: string): Promise<void> {
    await apiClient.delete(`/api/research/results/${resultId}`);
  },

  /**
   * Get pricing preview with bundle detection
   */
  async getPricingPreview(toolIds: string[]): Promise<PricingPreview> {
    const { data } = await apiClient.get('/api/research/pricing-preview', {
      params: { tool_ids: toolIds.join(',') }
    });
    return PricingPreviewSchema.parse(data);
  },

  /**
   * Get research analytics
   */
  async getAnalytics(days: number = 90): Promise<ResearchAnalytics> {
    const { data } = await apiClient.get('/api/research/analytics', {
      params: { days }
    });
    // Analytics schema is complex, will add if needed
    return data;
  },

  /**
   * Get optimal execution order for research tools based on dependencies
   */
  async getExecutionOrder(toolNames: string[]): Promise<{ executionOrder: string[]; toolCount: number }> {
    const { data } = await apiClient.post(
      '/api/research/execution-order',
      { tool_names: toolNames }
    );
    const schema = z.object({
      execution_order: z.array(z.string()),
      tool_count: z.number(),
    });
    const parsed = schema.parse(data);
    return {
      executionOrder: parsed.execution_order,
      toolCount: parsed.tool_count,
    };
  },

  /**
   * Get prerequisite status for tools based on a specific client's completed research.
   * Enables client-specific dependency tracking in the Tool Library page.
   */
  async getClientPrerequisites(
    clientId: string,
    toolNames?: string[]
  ): Promise<ClientPrerequisiteResponse> {
    const params = toolNames ? { tool_names: toolNames.join(',') } : {};
    const { data } = await apiClient.get(
      `/api/research/prerequisites/client/${clientId}`,
      { params }
    );
    const parsed = ClientPrerequisiteResponseSchema.parse(data);

    // Convert snake_case to camelCase
    return {
      clientId: parsed.client_id,
      tools: parsed.tools.map(t => ({
        toolName: t.tool_name,
        canRun: t.can_run,
        completed: t.completed,
        missingRequired: t.missing_required,
        missingRecommended: t.missing_recommended,
        lastRunAt: t.last_run_at || undefined,
      })),
      completedTools: parsed.completed_tools,
    };
  },
};
