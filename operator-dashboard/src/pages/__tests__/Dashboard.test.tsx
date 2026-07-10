/**
 * Tests for Dashboard page component
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Dashboard from '../Dashboard';

// Mock useNavigate
// NOTE: factory must be synchronous — an async factory returns a Promise as the
// module, leaving BrowserRouter/etc. undefined and crashing the shared providers.
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useAuth
// Field names follow the current camelCase User model (fullName / isSuperuser),
// not the legacy snake_case shape.
const mockLogout = jest.fn();
jest.mock('@/contexts/AuthContext', () => ({
  // Passthrough provider so shared test-utils (which wraps in AuthProvider) works.
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => ({
    user: {
      id: 'user-1',
      email: 'test@example.com',
      fullName: 'Test User',
      isSuperuser: true,
    },
    logout: mockLogout,
  }),
}));

describe('Dashboard Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render dashboard header with user info', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('Operator Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Welcome,')).toBeInTheDocument();
    expect(screen.getByText('Test User')).toBeInTheDocument();
    // Badge shows 'Admin' for superusers (component maps isSuperuser -> label).
    expect(screen.getByText('Admin')).toBeInTheDocument();
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
    jest.mock('@/contexts/AuthContext', () => ({
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
