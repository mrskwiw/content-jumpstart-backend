import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/__tests__/setup/test-utils";
import { ExportPanel } from "@/components/wizard/ExportPanel";
import { generatorApi } from "@/api/generator";
import type { Deliverable } from "@/types/domain";
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

  it("should have research checkbox checked by default", () => {
    renderComponent();
    const checkbox = screen.getByLabelText(/include research results/i);
    expect(checkbox).toBeChecked();
  });

  it("should toggle research results checkbox", () => {
    renderComponent();
    const checkbox = screen.getByLabelText(/include research results/i);

    // Checked by default -> first click unchecks
    fireEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();

    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();
  });

  it("should call exportPackage with includeResearch=true by default", async () => {
    jest.mocked(generatorApi.exportPackage).mockResolvedValueOnce({ id: "del-123" } as unknown as Deliverable);
    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: /export/i }));

    await waitFor(() => {
      expect(generatorApi.exportPackage).toHaveBeenCalledWith({
        projectId: "proj-123",
        clientId: "cli-456",
        format: "docx",
        target: "docx",
        includeAuditLog: false,
        includeResearch: true,
      });
    });
  });

  it("should call exportPackage with includeResearch=false when unchecked", async () => {
    jest.mocked(generatorApi.exportPackage).mockResolvedValueOnce({ id: "del-123" } as unknown as Deliverable);
    renderComponent();

    const checkbox = screen.getByLabelText(/include research results/i);
    fireEvent.click(checkbox); // uncheck (checked by default)
    fireEvent.click(screen.getByRole("button", { name: /export/i }));

    await waitFor(() => {
      expect(generatorApi.exportPackage).toHaveBeenCalledWith({
        projectId: "proj-123",
        clientId: "cli-456",
        format: "docx",
        target: "docx",
        includeAuditLog: false,
        includeResearch: false,
      });
    });
  });

  it("should work with both checkboxes checked", async () => {
    jest.mocked(generatorApi.exportPackage).mockResolvedValueOnce({ id: "del-123" } as unknown as Deliverable);
    renderComponent();

    // Research is checked by default; only need to check the audit log.
    fireEvent.click(screen.getByLabelText(/include audit log/i));
    fireEvent.click(screen.getByRole("button", { name: /export/i }));

    await waitFor(() => {
      expect(generatorApi.exportPackage).toHaveBeenCalledWith({
        projectId: "proj-123",
        clientId: "cli-456",
        format: "docx",
        target: "docx",
        includeAuditLog: true,
        includeResearch: true,
      });
    });
  });

  it("should work with markdown format", async () => {
    jest.mocked(generatorApi.exportPackage).mockResolvedValueOnce({ id: "del-123" } as unknown as Deliverable);
    renderComponent();

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "md" } });
    fireEvent.click(screen.getByRole("button", { name: /export/i }));

    await waitFor(() => {
      expect(generatorApi.exportPackage).toHaveBeenCalledWith({
        projectId: "proj-123",
        clientId: "cli-456",
        format: "md",
        target: "markdown",
        includeAuditLog: false,
        includeResearch: true,
      });
    });
  });
});
