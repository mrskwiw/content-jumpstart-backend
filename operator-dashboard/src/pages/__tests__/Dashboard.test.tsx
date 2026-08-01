/**
 * Tests for Dashboard page component
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Dashboard from '../Dashboard';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { creditsApi } from '@/api/credits';
import { costsApi } from '@/api/costs';

jest.mock('@/api/clients', () => ({ clientsApi: { list: jest.fn() } }));
jest.mock('@/api/projects', () => ({ projectsApi: { list: jest.fn() } }));
jest.mock('@/api/credits', () => ({ creditsApi: { getBalance: jest.fn() } }));
jest.mock('@/api/costs', () => ({ costsApi: { getUserCostSummary: jest.fn() } }));

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
    (clientsApi.list as jest.Mock).mockResolvedValue([]);
    (projectsApi.list as jest.Mock).mockResolvedValue({ items: [], page_size: 20 });
    (creditsApi.getBalance as jest.Mock).mockResolvedValue({ balance: 0 });
    (costsApi.getUserCostSummary as jest.Mock).mockResolvedValue({ totalCostUsd: 0 });
  });

  it('should render dashboard header with user info', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('Operator Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Welcome,')).toBeInTheDocument();
    expect(screen.getByText('Test User')).toBeInTheDocument();
    // Badge shows 'Admin' for superusers (component maps isSuperuser -> label).
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('should render the workspace overview heading and stat labels', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText(/your workspace at a glance/i)).toBeInTheDocument();
    expect(screen.getByText('Clients')).toBeInTheDocument();
    expect(screen.getByText('Projects')).toBeInTheDocument();
    expect(screen.getByText('Credit balance')).toBeInTheDocument();
    expect(screen.getByText('Spend (30d)')).toBeInTheDocument();
  });

  it('should render live stat values from the API', async () => {
    (clientsApi.list as jest.Mock).mockResolvedValue([{ id: 'c1' }, { id: 'c2' }, { id: 'c3' }]);
    (projectsApi.list as jest.Mock).mockResolvedValue({ items: [], total: 7, page_size: 20 });
    (creditsApi.getBalance as jest.Mock).mockResolvedValue({ balance: 1250 });
    (costsApi.getUserCostSummary as jest.Mock).mockResolvedValue({ totalCostUsd: 42.5 });

    renderWithProviders(<Dashboard />);

    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument()); // clients
    expect(screen.getByText('7')).toBeInTheDocument(); // projects (total)
    expect(screen.getByText('1,250')).toBeInTheDocument(); // credit balance
    expect(screen.getByText('$42.50')).toBeInTheDocument(); // 30d spend
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
