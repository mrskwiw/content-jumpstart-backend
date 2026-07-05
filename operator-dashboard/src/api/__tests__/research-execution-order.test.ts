import { describe, it, expect, beforeEach } from "@jest/globals";
import { researchApi } from "../research";
import apiClient from "../client";

jest.mock("../client");

describe("researchApi.getExecutionOrder", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("returns executionOrder, toolCount, and parallelGroups from response", async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        execution_order: ["seo_keyword_research", "platform_strategy", "content_calendar"],
        tool_count: 3,
        parallel_groups: [
          ["seo_keyword_research"],
          ["platform_strategy"],
          ["content_calendar"],
        ],
      },
    });

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
    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        execution_order: ["voice_analysis"],
        tool_count: 1,
        parallel_groups: [["voice_analysis"]],
      },
    });

    await researchApi.getExecutionOrder(["voice_analysis"]);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/research/execution-order",
      { tool_names: ["voice_analysis"] }
    );
  });

  it("returns empty parallelGroups for empty tool list", async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        execution_order: [],
        tool_count: 0,
        parallel_groups: [],
      },
    });

    const result = await researchApi.getExecutionOrder([]);

    expect(result.executionOrder).toEqual([]);
    expect(result.toolCount).toBe(0);
    expect(result.parallelGroups).toEqual([]);
  });

  it("returns independent tier-1 tools in a single parallel group", async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        execution_order: ["voice_analysis", "brand_archetype", "seo_keyword_research"],
        tool_count: 3,
        parallel_groups: [["voice_analysis", "brand_archetype", "seo_keyword_research"]],
      },
    });

    const result = await researchApi.getExecutionOrder([
      "voice_analysis",
      "brand_archetype",
      "seo_keyword_research",
    ]);

    expect(result.parallelGroups).toHaveLength(1);
    expect(result.parallelGroups[0]).toHaveLength(3);
  });

  it("throws when response is missing parallel_groups field", async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        execution_order: ["seo_keyword_research"],
        tool_count: 1,
        // parallel_groups intentionally absent — simulates old backend
      },
    });

    await expect(
      researchApi.getExecutionOrder(["seo_keyword_research"])
    ).rejects.toThrow();
  });
});
