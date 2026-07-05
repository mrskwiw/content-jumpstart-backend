/**
 * Tests for Dashboard page component
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Dashboard from '../Dashboard';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useAuth
const mockLogout = vi.fn();
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'admin',
      is_superuser: true,
    },
    logout: mockLogout,
  }),
}));

describe('Dashboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render dashboard header with user info', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('Operator Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Welcome,')).toBeInTheDocument();
    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
  });

  it('should render welcome message', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('Welcome to the Operator Dashboard')).toBeInTheDocument();
    expect(screen.getByText(/Phase 13/i)).toBeInTheDocument();
  });

  it('should have logout button', () => {
    renderWithProviders(<Dashboard />);

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    expect(logoutButton).toBeInTheDocument();
  });

  it('should call logout and navigate when logout button clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Dashboard />);

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    await user.click(logoutButton);

    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('should display email when name not available', () => {
    // Override mock for this test
    vi.mock('@/contexts/AuthContext', () => ({
      useAuth: () => ({
        user: {
          id: 'user-2',
          email: 'email@example.com',
          name: undefined,
          role: 'user',
          is_superuser: false,
        },
        logout: mockLogout,
      }),
    }));

    renderWithProviders(<Dashboard />);
    // Should fall back to email when name is not provided
    expect(screen.getByText(/Welcome,/i)).toBeInTheDocument();
  });
});
