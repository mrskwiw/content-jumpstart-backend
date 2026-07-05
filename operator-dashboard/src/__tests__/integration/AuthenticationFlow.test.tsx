/**
 * Integration Test: Authentication Flow
 * Tests the complete user authentication journey
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/contexts/AuthContext';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import { authApi } from '@/api/auth';

jest.mock('@/api/auth');

const mockAuthApi = authApi as jest.Mocked<typeof authApi>;

describe('Authentication Flow Integration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    localStorage.clear();
    jest.clearAllMocks();
  });

  it('should complete full login flow', async () => {
    const user = userEvent.setup();

    // Mock successful login
    mockAuthApi.login.mockResolvedValue({
      access_token: 'test-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer',
      user: {
        id: 'user-1',
        email: 'test@example.com',
        full_name: 'Test User',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/login']}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/dashboard" element={<Dashboard />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Should show login form
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = document.getElementById('password') as HTMLInputElement;

    expect(emailInput).toBeInTheDocument();
    expect(passwordInput).toBeInTheDocument();

    // Fill in credentials
    await user.type(emailInput, 'test@example.com');
    if (passwordInput) {
      await user.type(passwordInput, 'password123');
    }

    // Submit login form
    const loginButton = screen.getByRole('button', { name: /sign in|login/i });
    await user.click(loginButton);

    // Should call login API
    await waitFor(() => {
      expect(mockAuthApi.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });

    // Should store tokens in localStorage
    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe('test-token');
      expect(localStorage.getItem('refresh_token')).toBe('refresh-token');
    });

    // Should store user data
    const storedUser = localStorage.getItem('user');
    expect(storedUser).toBeTruthy();
    if (storedUser) {
      const parsedUser = JSON.parse(storedUser);
      expect(parsedUser.email).toBe('test@example.com');
    }
  });

  it('should show error on failed login', async () => {
    const user = userEvent.setup();

    // Mock failed login
    mockAuthApi.login.mockRejectedValue(new Error('Invalid credentials'));

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/login']}>
            <Login />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Fill in credentials
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = document.getElementById('password') as HTMLInputElement;

    await user.type(emailInput, 'wrong@example.com');
    if (passwordInput) {
      await user.type(passwordInput, 'wrongpass');
    }

    // Submit
    const loginButton = screen.getByRole('button', { name: /sign in|login/i });
    await user.click(loginButton);

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/invalid|error|failed/i)).toBeInTheDocument();
    });

    // Should NOT store tokens
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('should persist authentication across page reloads', () => {
    // Set up authenticated state
    localStorage.setItem('access_token', 'existing-token');
    localStorage.setItem('user', JSON.stringify({
      id: 'user-1',
      email: 'test@example.com',
      full_name: 'Test User',
      is_active: true,
      is_superuser: false,
      created_at: '2024-01-01T00:00:00Z',
    }));

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/dashboard']}>
            <Dashboard />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Should be authenticated (not redirected to login)
    expect(screen.getByText(/dashboard|overview/i)).toBeInTheDocument();
  });

  it('should complete logout flow', async () => {
    const user = userEvent.setup();

    // Set up authenticated state
    localStorage.setItem('access_token', 'test-token');
    localStorage.setItem('user', JSON.stringify({
      id: 'user-1',
      email: 'test@example.com',
      full_name: 'Test User',
      is_active: true,
      is_superuser: false,
      created_at: '2024-01-01T00:00:00Z',
    }));

    mockAuthApi.logout.mockResolvedValue(undefined);

    const TestComponent = () => {
      const { logout } = require('@/contexts/AuthContext').useAuth();
      return (
        <div>
          <button onClick={logout}>Logout</button>
          <div>Dashboard Content</div>
        </div>
      );
    };

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter>
            <TestComponent />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Click logout
    const logoutButton = screen.getByText('Logout');
    await user.click(logoutButton);

    // Should call logout API
    await waitFor(() => {
      expect(mockAuthApi.logout).toHaveBeenCalled();
    });
  });
});
