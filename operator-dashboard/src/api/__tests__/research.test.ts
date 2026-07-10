import { describe, it, expect, beforeEach } from "@jest/globals";
import type { AxiosResponse } from "axios";
import { researchApi } from "../research";
import apiClient from "../client";

jest.mock("../client");

describe("researchApi.getClientHistory", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should call GET endpoint with clientId", async () => {
    const mockResponse = {
      data: {
        results: [],
        total: 0,
        clientId: "cli-123",
      },
    };

    (apiClient.get as jest.MockedFunction<typeof apiClient.get>).mockResolvedValueOnce(mockResponse as unknown as AxiosResponse);

    const result = await researchApi.getClientHistory("cli-123");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/research/results/client/cli-123",
      { params: {} }
    );
    expect(result).toEqual(mockResponse.data);
  });

  it("should include tool_name parameter when provided", async () => {
    const mockResponse = {
      data: {
        results: [],
        total: 0,
        clientId: "cli-123",
      },
    };

    (apiClient.get as jest.MockedFunction<typeof apiClient.get>).mockResolvedValueOnce(mockResponse as unknown as AxiosResponse);

    await researchApi.getClientHistory("cli-123", "voice_analysis");

    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/research/results/client/cli-123",
      { params: { tool_name: "voice_analysis" } }
    );
  });

  it("should return research history data", async () => {
    const mockData = {
      results: [
        {
          id: "res-1",
          toolName: "voice_analysis",
          createdAt: "2026-02-20T10:00:00Z",
          status: "completed",
        },
      ],
      total: 1,
      clientId: "cli-123",
    };

    (apiClient.get as jest.MockedFunction<typeof apiClient.get>).mockResolvedValueOnce({ data: mockData } as unknown as AxiosResponse);

    const result = await researchApi.getClientHistory("cli-123");

    expect(result).toEqual(mockData);
    expect(result.results).toHaveLength(1);
    expect(result.results[0].toolName).toBe("voice_analysis");
  });

  it("should handle multiple research results", async () => {
    const mockData = {
      results: [
        {
          id: "res-1",
          toolName: "voice_analysis",
          createdAt: "2026-02-20T10:00:00Z",
          status: "completed",
        },
        {
          id: "res-2",
          toolName: "seo_keywords",
          createdAt: "2026-02-15T10:00:00Z",
          status: "completed",
        },
        {
          id: "res-3",
          toolName: "brand_archetype",
          createdAt: "2026-02-10T10:00:00Z",
          status: "completed",
        },
      ],
      total: 3,
      clientId: "cli-123",
    };

    (apiClient.get as jest.MockedFunction<typeof apiClient.get>).mockResolvedValueOnce({ data: mockData } as unknown as AxiosResponse);

    const result = await researchApi.getClientHistory("cli-123");

    expect(result.total).toBe(3);
    expect(result.results).toHaveLength(3);
  });

  it("should handle empty results", async () => {
    const mockData = {
      results: [],
      total: 0,
      clientId: "cli-123",
    };

    (apiClient.get as jest.MockedFunction<typeof apiClient.get>).mockResolvedValueOnce({ data: mockData } as unknown as AxiosResponse);

    const result = await researchApi.getClientHistory("cli-123");

    expect(result.results).toEqual([]);
    expect(result.total).toBe(0);
  });

  it("should handle API errors", async () => {
    (apiClient.get as jest.MockedFunction<typeof apiClient.get>).mockRejectedValueOnce(new Error("Network error"));

    await expect(researchApi.getClientHistory("cli-123")).rejects.toThrow("Network error");
  });

  it("should handle 404 for non-existent client", async () => {
    (apiClient.get as jest.MockedFunction<typeof apiClient.get>).mockRejectedValueOnce({ response: { status: 404 } });

    await expect(researchApi.getClientHistory("cli-999")).rejects.toBeTruthy();
  });

  it("should handle 403 for unauthorized access", async () => {
    (apiClient.get as jest.MockedFunction<typeof apiClient.get>).mockRejectedValueOnce({ response: { status: 403 } });

    await expect(researchApi.getClientHistory("cli-123")).rejects.toBeTruthy();
  });
});

describe("generatorApi.exportPackage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should send includeResearch parameter to backend", async () => {
    const { generatorApi } = await import("../generator");

    const mockResponse = {
      data: {
        id: "del-123",
        projectId: "proj-123",
        clientId: "cli-456",
        format: "docx",
        path: "/path/to/file.docx",
        createdAt: "2026-02-20T10:00:00Z",
        status: "ready",
      },
    };

    (apiClient.post as jest.MockedFunction<typeof apiClient.post>).mockResolvedValueOnce(mockResponse as unknown as AxiosResponse);

    await generatorApi.exportPackage({
      projectId: "proj-123",
      clientId: "cli-456",
      format: "docx",
      includeAuditLog: false,
      includeResearch: true,
    });

    expect(apiClient.post).toHaveBeenCalledWith("/api/generator/export", {
      project_id: "proj-123",
      client_id: "cli-456",
      format: "docx",
      include_audit_log: false,
      include_research: true,
    });
  });

  it("should convert camelCase to snake_case", async () => {
    const { generatorApi } = await import("../generator");

    (apiClient.post as jest.MockedFunction<typeof apiClient.post>).mockResolvedValueOnce({
      data: {
        id: "del-123",
        projectId: "proj-123",
        clientId: "cli-456",
        format: "md",
        path: "/path/to/file.md",
        createdAt: "2026-02-20T10:00:00Z",
        status: "ready",
      },
    } as unknown as AxiosResponse);

    await generatorApi.exportPackage({
      projectId: "proj-123",
      clientId: "cli-456",
      format: "md",
      includeAuditLog: true,
      includeResearch: true,
    });

    const callArgs = (apiClient.post as jest.MockedFunction<typeof apiClient.post>).mock.calls[0];
    expect(callArgs[1]).toHaveProperty("include_research");
    expect(callArgs[1]).toHaveProperty("include_audit_log");
    expect(callArgs[1]).not.toHaveProperty("includeResearch");
    expect(callArgs[1]).not.toHaveProperty("includeAuditLog");
  });
});
