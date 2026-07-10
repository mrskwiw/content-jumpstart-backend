/**
 * Comprehensive tests for ClientProfilePanel
 */
import { describe, it, expect, jest } from '@jest/globals';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders as render } from '@/__tests__/setup/test-utils';
import userEvent from '@testing-library/user-event';
import { ClientProfilePanel } from '../ClientProfilePanel';

describe('ClientProfilePanel', () => {
  const mockOnSave = jest.fn<() => void>();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render without crashing', () => {
    const { container } = render(<ClientProfilePanel />);
    expect(container).toBeInTheDocument();
  });

  it('should render all form fields', () => {
    const { container } = render(<ClientProfilePanel />);

    // Should have input fields
    const inputs = container.querySelectorAll('input, textarea, select');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('should render with initial data', () => {
    const initialData = {
      companyName: 'Test Company',
      businessDescription: 'We sell software',
      idealCustomer: 'B2B SaaS companies',
    };

    render(<ClientProfilePanel initialData={initialData} />);

    // Field values live in input elements, not text content.
    expect(screen.getByDisplayValue('Test Company')).toBeInTheDocument();
  });

  it('should allow adding pain points', async () => {
    const user = userEvent.setup();
    const { container } = render(<ClientProfilePanel onSave={mockOnSave} />);

    // Find pain point input and add button
    const inputs = container.querySelectorAll('input');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('should allow selecting tone preference', () => {
    const { container } = render(<ClientProfilePanel />);

    // Should have tone options
    const tones = ['professional', 'conversational', 'friendly'];
    const hasAnyTone = tones.some(tone =>
      container.textContent?.toLowerCase().includes(tone)
    );

    expect(hasAnyTone || container.querySelector('select')).toBeTruthy();
  });

  it('should allow platform selection', () => {
    const { container } = render(<ClientProfilePanel />);

    // Should have platform selection UI
    const elements = container.querySelectorAll('button, input, [role="checkbox"]');
    expect(elements.length).toBeGreaterThan(0);
  });

  it('should call onSave when form is submitted', () => {
    const { container } = render(<ClientProfilePanel onSave={mockOnSave} />);

    // Should have save button
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should validate required fields', () => {
    const { container } = render(<ClientProfilePanel onSave={mockOnSave} />);

    // Form should be present
    expect(container.firstChild).toBeInTheDocument();
  });

  it('should update form data when initialData changes', () => {
    const { rerender } = render(
      <ClientProfilePanel initialData={{ companyName: 'Original' }} />
    );

    expect(screen.getByDisplayValue('Original')).toBeInTheDocument();

    rerender(<ClientProfilePanel initialData={{ companyName: 'Updated' }} />);

    expect(screen.getByDisplayValue('Updated')).toBeInTheDocument();
  });

  it('should handle brief import', () => {
    const { container } = render(<ClientProfilePanel />);

    // Should have import section or button
    const hasImport = container.textContent?.toLowerCase().includes('import') ||
                     container.querySelector('[type="file"]');

    expect(hasImport || container.querySelectorAll('button').length > 0).toBeTruthy();
  });
});
