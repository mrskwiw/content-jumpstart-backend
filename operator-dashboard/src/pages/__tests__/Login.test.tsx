/**
 * Tests for Login page component
 */
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithRouter } from '@/__tests__/setup/test-utils';
import Login from '../Login';

const authState = {
  login: jest.fn() as jest.MockedFunction<(credentials: { email: string; password: string }) => Promise<void>>,
  isAuthenticated: false,
  isLoading: false,
};

let navigateMock: jest.Mock;

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => authState,
}));

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

describe('Login Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    authState.login.mockReset();
    authState.isAuthenticated = false;
    authState.isLoading = false;
    navigateMock = jest.fn();
  });

  it('should render login form', () => {
    renderWithRouter(<Login />);

    expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/••••••••/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('should handle successful login and go to the splash screen', async () => {
    authState.login.mockResolvedValue(undefined);

    const user = userEvent.setup();
    renderWithRouter(<Login />);

    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'test@example.com');
    await user.type(screen.getByPlaceholderText(/••••••••/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(authState.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });

    expect(navigateMock).toHaveBeenCalledWith('/portfolio-notice', { replace: true });
  });

  it('should display error on failed login', async () => {
    authState.login.mockRejectedValue(new Error('Invalid credentials'));

    const user = userEvent.setup();
    renderWithRouter(<Login />);

    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'test@example.com');
    await user.type(screen.getByPlaceholderText(/••••••••/i), 'wrong-password');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });

  it('should validate required fields', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Login />);

    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(authState.login).not.toHaveBeenCalled();
  });

  it('should toggle password visibility', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Login />);

    const passwordInput = screen.getByPlaceholderText(/••••••••/i) as HTMLInputElement;
    expect(passwordInput.type).toBe('password');

    const toggleButtons = screen.queryAllByRole('button');
    const visibilityToggle = toggleButtons.find((btn) =>
      btn.getAttribute('aria-label')?.includes('password') ||
      btn.textContent?.includes('Show')
    );

    if (visibilityToggle) {
      await user.click(visibilityToggle);
      expect(passwordInput.type).toBe('text');
    }
  });
});
