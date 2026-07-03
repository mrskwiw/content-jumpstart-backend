/**
 * PortfolioNotice and RootRedirect regression tests.
 *
 * Verifies that authenticated users only see the notice once per session and
 * that both the button path and keyboard path persist the dismissal flag.
 */
import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router-dom';
import PortfolioNotice from '@/pages/PortfolioNotice';
import RootRedirect from '@/components/RootRedirect';

const mockUseAuth = jest.fn();

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

function PortfolioNoticeRoute() {
  return (
    <>
      <PortfolioNotice />
      <LocationDisplay />
    </>
  );
}

describe('PortfolioNotice routing', () => {
  beforeEach(() => {
    sessionStorage.clear();
    mockUseAuth.mockReset();
  });

  it('routes authenticated users to the portfolio notice once, then dashboard after dismissal', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });

    const router = createMemoryRouter(
      [
        { path: '/', element: <RootRedirect /> },
        { path: '/login', element: <LocationDisplay /> },
        { path: '/dashboard', element: <LocationDisplay /> },
        { path: '/portfolio-notice', element: <PortfolioNoticeRoute /> },
      ],
      { initialEntries: ['/'] }
    );

    render(<RouterProvider router={router} />);

    expect(await screen.findByTestId('location')).toHaveTextContent('/portfolio-notice');

    fireEvent.click(screen.getByRole('button', { name: /enter dashboard/i }));

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/dashboard'));
    expect(sessionStorage.getItem('portfolioNoticeSeen')).toBe('1');
  });

  it('persists dismissal when continuing with the keyboard', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });

    const router = createMemoryRouter(
      [
        { path: '/', element: <RootRedirect /> },
        { path: '/login', element: <LocationDisplay /> },
        { path: '/dashboard', element: <LocationDisplay /> },
        { path: '/portfolio-notice', element: <PortfolioNoticeRoute /> },
      ],
      { initialEntries: ['/portfolio-notice'] }
    );

    render(<RouterProvider router={router} />);

    fireEvent.keyDown(window, { key: 'Enter' });

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/dashboard'));
    expect(sessionStorage.getItem('portfolioNoticeSeen')).toBe('1');
  });
});
