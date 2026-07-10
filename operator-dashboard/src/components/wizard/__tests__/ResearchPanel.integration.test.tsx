import { describe, it, expect, beforeEach, jest } from "@jest/globals";
import { render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResearchPanel } from "../ResearchPanel";
import { researchApi } from "@/api/research";

jest.mock("@/api/research");

const mockTools = [
  {
    name: "company_info",
    label: "Company Information",
    category: "foundation",
    status: "available" as const,
    price: 50,
    description: "Research company background",
  },
  {
    name: "competitor_analysis",
    label: "Competitor Analysis",
    category: "seo",
    status: "available" as const,
    price: 100,
    description: "Analyze competitors",
  },
];

const mockHistoryFresh = {
  results: [
    {
      id: "res-1",
      toolName: "company_info",
      toolLabel: "Company Information",
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
      status: "completed",
      durationSeconds: 45,
    },
  ],
  total: 1,
  clientId: "cli-123",
};

const mockHistoryStale = {
  results: [
    {
      id: "res-1",
      toolName: "company_info",
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 45).toISOString(),
      status: "completed",
      durationSeconds: 45,
    },
    {
      id: "res-2",
      toolName: "competitor_analysis",
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
      status: "completed",
      durationSeconds: 120,
    },
  ],
  total: 2,
  clientId: "cli-123",
};

const mockHistoryEmpty = {
  results: [],
  total: 0,
  clientId: "cli-123",
};

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ResearchPanel Integration Tests", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch and display fresh research history with green indicators", async () => {
    jest.mocked(researchApi.listTools).mockResolvedValue(mockTools);
    jest.mocked(researchApi.getClientHistory).mockResolvedValue(mockHistoryFresh);

    renderWithQueryClient(<ResearchPanel projectId="proj-123" clientId="cli-123" />);

    await waitFor(() => {
      expect(screen.getByText("Company Information")).toBeInTheDocument();
    });

    expect(researchApi.getClientHistory).toHaveBeenCalledWith("cli-123");

    const companyInfoCard = screen.getByText("Company Information").closest("button");
    expect(companyInfoCard).toBeInTheDocument();

    const lastRunText = within(companyInfoCard!).getByText(/Last run:/);
    expect(lastRunText).toHaveTextContent("Today");
    expect(lastRunText.parentElement).toHaveClass("text-emerald-600");
  });

  it("should display stale research history with amber indicators", async () => {
    jest.mocked(researchApi.listTools).mockResolvedValue(mockTools);
    jest.mocked(researchApi.getClientHistory).mockResolvedValue(mockHistoryStale);

    renderWithQueryClient(<ResearchPanel projectId="proj-123" clientId="cli-123" />);

    await waitFor(() => {
      expect(screen.getByText("Company Information")).toBeInTheDocument();
    });

    const companyInfoCard = screen.getByText("Company Information").closest("button");
    const lastRunText = within(companyInfoCard!).getByText(/Last run:/);

    expect(lastRunText).toHaveTextContent(/months ago/);
    expect(lastRunText.parentElement).toHaveClass("text-amber-600");
  });

  it("should display fresh competitor analysis correctly", async () => {
    jest.mocked(researchApi.listTools).mockResolvedValue(mockTools);
    jest.mocked(researchApi.getClientHistory).mockResolvedValue(mockHistoryStale);

    renderWithQueryClient(<ResearchPanel projectId="proj-123" clientId="cli-123" />);

    await waitFor(() => {
      expect(screen.getByText("Competitor Analysis")).toBeInTheDocument();
    });

    const competitorCard = screen.getByText("Competitor Analysis").closest("button");
    const lastRunText = within(competitorCard!).getByText(/Last run:/);

    expect(lastRunText).toHaveTextContent("5 days ago");
    expect(lastRunText.parentElement).toHaveClass("text-emerald-600");
  });

  it("should display Never run for tools with no history", async () => {
    jest.mocked(researchApi.listTools).mockResolvedValue(mockTools);
    jest.mocked(researchApi.getClientHistory).mockResolvedValue(mockHistoryEmpty);

    renderWithQueryClient(<ResearchPanel projectId="proj-123" clientId="cli-123" />);

    await waitFor(() => {
      expect(screen.getByText("Company Information")).toBeInTheDocument();
    });

    const allCards = screen.getAllByRole("button").filter(
      (btn) => btn.textContent?.includes("Last run:")
    );

    allCards.forEach((card) => {
      const lastRunText = within(card).getByText(/Last run:/);
      expect(lastRunText).toHaveTextContent("Never run");
      expect(lastRunText.parentElement).toHaveClass("text-slate-500");
    });
  });

  it("should handle missing clientId gracefully", async () => {
    jest.mocked(researchApi.listTools).mockResolvedValue(mockTools);

    renderWithQueryClient(<ResearchPanel projectId="proj-123" />);

    await waitFor(() => {
      expect(screen.getByText("Company Information")).toBeInTheDocument();
    });

    expect(researchApi.getClientHistory).not.toHaveBeenCalled();

    const companyInfoCard = screen.getByText("Company Information").closest("button");
    const lastRunText = within(companyInfoCard!).getByText(/Last run:/);
    expect(lastRunText).toHaveTextContent("Never run");
  });

  it("should handle API errors gracefully", async () => {
    jest.mocked(researchApi.listTools).mockResolvedValue(mockTools);
    jest.mocked(researchApi.getClientHistory).mockRejectedValue(new Error("Network error"));

    renderWithQueryClient(<ResearchPanel projectId="proj-123" clientId="cli-123" />);

    await waitFor(() => {
      expect(screen.getByText("Company Information")).toBeInTheDocument();
    });

    const companyInfoCard = screen.getByText("Company Information").closest("button");
    const lastRunText = within(companyInfoCard!).getByText(/Last run:/);
    expect(lastRunText).toHaveTextContent("Never run");
  });
});
