/**
 * Tests for Badge component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Badge } from '../Badge';

describe('Badge', () => {
  it('should render with default variant', () => {
    render(<Badge>Default Badge</Badge>);
    expect(screen.getByText('Default Badge')).toBeInTheDocument();
  });

  it('should render with primary variant', () => {
    render(<Badge variant="primary">Primary</Badge>);
    const badge = screen.getByText('Primary');
    expect(badge).toHaveClass('bg-primary-100');
  });

  it('should render with success variant', () => {
    render(<Badge variant="success">Success</Badge>);
    const badge = screen.getByText('Success');
    expect(badge).toHaveClass('bg-emerald-100');
  });

  it('should render with danger variant', () => {
    render(<Badge variant="danger">Error</Badge>);
    const badge = screen.getByText('Error');
    expect(badge).toHaveClass('bg-red-100');
  });

  it('should render with warning variant', () => {
    render(<Badge variant="warning">Warning</Badge>);
    const badge = screen.getByText('Warning');
    expect(badge).toHaveClass('bg-amber-100');
  });

  it('should render with info variant', () => {
    render(<Badge variant="info">Info</Badge>);
    const badge = screen.getByText('Info');
    expect(badge).toHaveClass('bg-blue-100');
  });

  it('should render with small size', () => {
    render(<Badge size="sm">Small</Badge>);
    const badge = screen.getByText('Small');
    expect(badge).toHaveClass('px-2', 'py-0.5', 'text-xs');
  });

  it('should render with large size', () => {
    render(<Badge size="lg">Large</Badge>);
    const badge = screen.getByText('Large');
    expect(badge).toHaveClass('px-3', 'py-1', 'text-sm');
  });

  it('should render remove button when onRemove is provided', () => {
    const mockOnRemove = jest.fn();
    render(<Badge onRemove={mockOnRemove}>Removable</Badge>);

    const removeButton = screen.getByRole('button');
    expect(removeButton).toBeInTheDocument();
  });

  it('should call onRemove when remove button is clicked', async () => {
    const user = userEvent.setup();
    const mockOnRemove = jest.fn();

    render(<Badge onRemove={mockOnRemove}>Removable</Badge>);

    const removeButton = screen.getByRole('button');
    await user.click(removeButton);

    expect(mockOnRemove).toHaveBeenCalledTimes(1);
  });

  it('should stop propagation when remove button is clicked', async () => {
    const user = userEvent.setup();
    const mockOnRemove = jest.fn();
    const mockParentClick = jest.fn();

    render(
      <div onClick={mockParentClick}>
        <Badge onRemove={mockOnRemove}>Removable</Badge>
      </div>
    );

    const removeButton = screen.getByRole('button');
    await user.click(removeButton);

    expect(mockOnRemove).toHaveBeenCalled();
    expect(mockParentClick).not.toHaveBeenCalled();
  });

  it('should not render remove button when onRemove is not provided', () => {
    render(<Badge>Not Removable</Badge>);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('should render with status-specific variants', () => {
    render(<Badge variant="draft">Draft</Badge>);
    expect(screen.getByText('Draft')).toHaveClass('bg-neutral-100');

    render(<Badge variant="ready">Ready</Badge>);
    expect(screen.getByText('Ready')).toHaveClass('bg-emerald-100');

    render(<Badge variant="delivered">Delivered</Badge>);
    expect(screen.getByText('Delivered')).toHaveClass('bg-emerald-100');
  });

  it('should accept custom className', () => {
    render(<Badge className="custom-class">Custom</Badge>);
    const badge = screen.getByText('Custom');
    expect(badge).toHaveClass('custom-class');
  });
});
