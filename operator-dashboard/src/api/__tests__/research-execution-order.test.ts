import { describe, it, expect, beforeEach, jest } from "@jest/globals";
import type { AxiosResponse } from "axios";
import { researchApi } from "../research";
import apiClient from "../client";

jest.mock("../client");

const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

/** Raw snake_case shape returned by POST /api/research/execution-order. */
interface ExecutionOrderResponse {
  execution_order: string[];
  tool_count: number;
  parallel_groups?: string[][];
  dependency_map: Record<string, string[]>;
}

describe("researchApi.getExecutionOrder", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("returns executionOrder, toolCount, and parallelGroups from response", async () => {
    mockedApiClient.post.mockResolvedValueOnce({
      data: {
        execution_order: ["seo_keyword_research", "platform_strategy", "content_calendar"],
        tool_count: 3,
        parallel_groups: [
          ["seo_keyword_research"],
          ["platform_strategy"],
          ["content_calendar"],
        ],
        dependency_map: {
          seo_keyword_research: [],
          platform_strategy: ["seo_keyword_research"],
          content_calendar: ["platform_strategy"],
        },
      },
    } as AxiosResponse<ExecutionOrderResponse>);

    const result = await researchApi.getExecutionOrder([
      "content_calendar",
      "platform_strategy",
      "seo_keyword_research",
    ]);

    expect(result.executionOrder).toEqual([
      "seo_keyword_research",
      "platform_strategy",
      "content_calendar",
    ]);
    expect(result.toolCount).toBe(3);
    expect(result.parallelGroups).toEqual([
      ["seo_keyword_research"],
      ["platform_strategy"],
      ["content_calendar"],
    ]);
  });

  it("posts tool_names to the correct endpoint", async () => {
    mockedApiClient.post.mockResolvedValueOnce({
      data: {
        execution_order: ["voice_analysis"],
        tool_count: 1,
        parallel_groups: [["voice_analysis"]],
        dependency_map: { voice_analysis: [] },
      },
    } as AxiosResponse<ExecutionOrderResponse>);

    await researchApi.getExecutionOrder(["voice_analysis"]);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/research/execution-order",
      { tool_names: ["voice_analysis"] }
    );
  });

  it("returns empty parallelGroups for empty tool list", async () => {
    mockedApiClient.post.mockResolvedValueOnce({
      data: {
        execution_order: [],
        tool_count: 0,
        parallel_groups: [],
        dependency_map: {},
      },
    } as AxiosResponse<ExecutionOrderResponse>);

    const result = await researchApi.getExecutionOrder([]);

    expect(result.executionOrder).toEqual([]);
    expect(result.toolCount).toBe(0);
    expect(result.parallelGroups).toEqual([]);
  });

  it("returns independent tier-1 tools in a single parallel group", async () => {
    mockedApiClient.post.mockResolvedValueOnce({
      data: {
        execution_order: ["voice_analysis", "brand_archetype", "seo_keyword_research"],
        tool_count: 3,
        parallel_groups: [["voice_analysis", "brand_archetype", "seo_keyword_research"]],
        dependency_map: {
          voice_analysis: [],
          brand_archetype: [],
          seo_keyword_research: [],
        },
      },
    } as AxiosResponse<ExecutionOrderResponse>);

    const result = await researchApi.getExecutionOrder([
      "voice_analysis",
      "brand_archetype",
      "seo_keyword_research",
    ]);

    expect(result.parallelGroups).toHaveLength(1);
    expect(result.parallelGroups[0]).toHaveLength(3);
  });

  it("throws when response is missing parallel_groups field", async () => {
    mockedApiClient.post.mockResolvedValueOnce({
      data: {
        execution_order: ["seo_keyword_research"],
        tool_count: 1,
        // parallel_groups intentionally absent — simulates old backend
      },
    } as AxiosResponse<ExecutionOrderResponse>);

    await expect(
      researchApi.getExecutionOrder(["seo_keyword_research"])
    ).rejects.toThrow();
  });
});
