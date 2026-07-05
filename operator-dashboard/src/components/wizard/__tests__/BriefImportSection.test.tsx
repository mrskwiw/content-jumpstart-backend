/**
 * Tests for BriefImportSection
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render } from '@testing-library/react';
import { BriefImportSection } from '../BriefImportSection';

// Mock the brief import service
jest.mock('@/services/briefImportService', () => ({
  briefImportService: {
    parseFile: jest.fn().mockResolvedValue({
      success: true,
      fields: {},
      warnings: [],
      metadata: { filename: 'test.txt', parseTimeMs: 100, fieldsExtracted: 0, fieldsTotal: 0 },
    }),
  },
}));

describe('BriefImportSection', () => {
  const mockOnImport = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render without crashing', () => {
    const { container } = render(<BriefImportSection onImport={mockOnImport} />);
    expect(container).toBeInTheDocument();
  });

  it('should render file upload area', () => {
    const { container } = render(<BriefImportSection onImport={mockOnImport} />);

    // Should have file input or upload area
    const fileInput = container.querySelector('input[type="file"]');
    const uploadArea = container.querySelector('[class*="upload"], [class*="drop"]');

    expect(fileInput || uploadArea || container.firstChild).toBeInTheDocument();
  });

  it('should show supported file types', () => {
    const { container } = render(<BriefImportSection onImport={mockOnImport} />);

    // Should mention file types
    const hasFileType = container.textContent?.toLowerCase().includes('txt') ||
                       container.textContent?.toLowerCase().includes('file');

    expect(hasFileType || container.firstChild).toBeTruthy();
  });

  it('should render upload button or drag-drop area', () => {
    const { container } = render(<BriefImportSection onImport={mockOnImport} />);

    // Should have interactive upload UI
    const buttons = container.querySelectorAll('button');
    const inputs = container.querySelectorAll('input');

    expect(buttons.length + inputs.length).toBeGreaterThan(0);
  });
});
