/**
 * Tests for Alert component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Alert, AlertTitle, AlertDescription } from '../Alert';

describe('Alert', () => {
  it('should render with default variant', () => {
    render(<Alert>Default alert message</Alert>);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Default alert message')).toBeInTheDocument();
  });

  it('should render with info variant', () => {
    render(<Alert variant="info">Info message</Alert>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveClass('bg-blue-50');
  });

  it('should render with success variant', () => {
    render(<Alert variant="success">Success message</Alert>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveClass('bg-emerald-50');
  });

  it('should render with warning variant', () => {
    render(<Alert variant="warning">Warning message</Alert>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveClass('bg-amber-50');
  });

  it('should render with danger variant', () => {
    render(<Alert variant="danger">Error message</Alert>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveClass('bg-red-50');
  });

  it('should show icon by default', () => {
    const { container } = render(<Alert>Message</Alert>);
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('should hide icon when showIcon is false', () => {
    const { container } = render(<Alert showIcon={false}>Message</Alert>);
    const icon = container.querySelector('svg');
    expect(icon).not.toBeInTheDocument();
  });

  it('should render custom icon', () => {
    const CustomIcon = () => <span data-testid="custom-icon">★</span>;
    render(
      <Alert icon={<CustomIcon />}>
        Message
      </Alert>
    );
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });

  it('should render close button when onClose is provided', () => {
    const mockOnClose = jest.fn();
    render(<Alert onClose={mockOnClose}>Closable alert</Alert>);

    const closeButton = screen.getByRole('button', { name: /close/i });
    expect(closeButton).toBeInTheDocument();
  });

  it('should call onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    const mockOnClose = jest.fn();

    render(<Alert onClose={mockOnClose}>Closable alert</Alert>);

    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('should not render close button when onClose is not provided', () => {
    render(<Alert>Non-closable alert</Alert>);
    expect(screen.queryByRole('button', { name: /close/i })).not.toBeInTheDocument();
  });

  it('should render with AlertTitle', () => {
    render(
      <Alert>
        <AlertTitle>Alert Title</AlertTitle>
        <AlertDescription>Alert description</AlertDescription>
      </Alert>
    );

    expect(screen.getByText('Alert Title')).toBeInTheDocument();
    expect(screen.getByText('Alert description')).toBeInTheDocument();
  });

  it('should apply correct icon color for each variant', () => {
    const { container: infoContainer } = render(<Alert variant="info">Info</Alert>);
    expect(infoContainer.querySelector('.text-blue-600')).toBeInTheDocument();

    const { container: successContainer } = render(<Alert variant="success">Success</Alert>);
    expect(successContainer.querySelector('.text-emerald-600')).toBeInTheDocument();

    const { container: warningContainer } = render(<Alert variant="warning">Warning</Alert>);
    expect(warningContainer.querySelector('.text-amber-600')).toBeInTheDocument();

    const { container: dangerContainer } = render(<Alert variant="danger">Danger</Alert>);
    expect(dangerContainer.querySelector('.text-red-600')).toBeInTheDocument();
  });

  it('should accept custom className', () => {
    render(<Alert className="custom-alert">Custom</Alert>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveClass('custom-alert');
  });

  it('should render AlertTitle with custom className', () => {
    render(
      <Alert>
        <AlertTitle className="custom-title">Title</AlertTitle>
      </Alert>
    );
    const title = screen.getByText('Title');
    expect(title).toHaveClass('custom-title');
  });

  it('should render AlertDescription with custom className', () => {
    render(
      <Alert>
        <AlertDescription className="custom-desc">Description</AlertDescription>
      </Alert>
    );
    const desc = screen.getByText('Description');
    expect(desc).toHaveClass('custom-desc');
  });
});
