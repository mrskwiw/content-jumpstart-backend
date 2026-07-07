import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/__tests__/setup/test-utils";
import { ExportPanel } from "@/components/wizard/ExportPanel";
import { generatorApi } from "@/api/generator";
import { describe, it, expect, beforeEach } from "@jest/globals";

jest.mock("@/api/generator", () => ({
  generatorApi: {
    exportPackage: jest.fn(),
  },
}));

describe("ExportPanel - Research Results Checkbox", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderComponent = (props = {}) => {
    const defaultProps = {
      projectId: "proj-123",
      clientId: "cli-456",
    };

    return renderWithProviders(<ExportPanel {...defaultProps} {...props} />);
  };

  it("should render with research results checkbox", () => {
    renderComponent();
    expect(screen.getByLabelText(/include research results/i)).toBeInTheDocument();
  });

  it("should have research checkbox unchecked by default", () => {
    renderComponent();
    const checkbox = screen.getByLabelText(/include research results/i);
    expect(checkbox).not.toBeChecked();
  });

  it("should toggle research results checkbox", () => {
    renderComponent();
    const checkbox = screen.getByLabelText(/include research results/i);

    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    fireEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();
  });

  it("should call exportPackage with includeResearch=false by default", async () => {
    (generatorApi.exportPackage as any).mockResolvedValueOnce({ id: "del-123" });
    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: /export/i }));

    await waitFor(() => {
      expect(generatorApi.exportPackage).toHaveBeenCalledWith({
        projectId: "proj-123",
        clientId: "cli-456",
        format: "docx",
        includeAuditLog: false,
        includeResearch: false,
      });
    });
  });

  it("should call exportPackage with includeResearch=true when checked", async () => {
    (generatorApi.exportPackage as any).mockResolvedValueOnce({ id: "del-123" });
    renderComponent();

    const checkbox = screen.getByLabelText(/include research results/i);
    fireEvent.click(checkbox);
    fireEvent.click(screen.getByRole("button", { name: /export/i }));

    await waitFor(() => {
      expect(generatorApi.exportPackage).toHaveBeenCalledWith({
        projectId: "proj-123",
        clientId: "cli-456",
        format: "docx",
        includeAuditLog: false,
        includeResearch: true,
      });
    });
  });

  it("should work with both checkboxes checked", async () => {
    (generatorApi.exportPackage as any).mockResolvedValueOnce({ id: "del-123" });
    renderComponent();

    fireEvent.click(screen.getByLabelText(/include audit log/i));
    fireEvent.click(screen.getByLabelText(/include research results/i));
    fireEvent.click(screen.getByRole("button", { name: /export/i }));

    await waitFor(() => {
      expect(generatorApi.exportPackage).toHaveBeenCalledWith({
        projectId: "proj-123",
        clientId: "cli-456",
        format: "docx",
        includeAuditLog: true,
        includeResearch: true,
      });
    });
  });

  it("should work with markdown format", async () => {
    (generatorApi.exportPackage as any).mockResolvedValueOnce({ id: "del-123" });
    renderComponent();

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "md" } });
    fireEvent.click(screen.getByLabelText(/include research results/i));
    fireEvent.click(screen.getByRole("button", { name: /export/i }));

    await waitFor(() => {
      expect(generatorApi.exportPackage).toHaveBeenCalledWith({
        projectId: "proj-123",
        clientId: "cli-456",
        format: "md",
        includeAuditLog: false,
        includeResearch: true,
      });
    });
  });
});
