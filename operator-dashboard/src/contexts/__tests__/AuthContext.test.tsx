/**
 * Comprehensive tests for AuthContext
 */
import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import { authApi } from '@/api/auth';
import { queryClient } from '@/providers/queryClient';
import type { LoginRequest, User, LoginResponse } from '@/types/api';

jest.mock('@/api/auth');
const mockedAuthApi = authApi as jest.Mocked<typeof authApi>;

describe('AuthContext', () => {
  const mockUser: User = {
    id: 'user-1',
    email: 'test@example.com',
    full_name: 'Test User',
    is_active: true,
    is_superuser: false,
    created_at: '2024-01-01T00:00:00Z',
  };

  const mockLoginResponse: LoginResponse = {
    access_token: 'test_access_token',
    refresh_token: 'test_refresh_token',
    token_type: 'bearer',
    user: mockUser,
  };

  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    (console.error as jest.Mock).mockRestore();
  });

  describe('Provider initialization', () => {
    it('should start with null user and loading true', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });

    it('should load user from localStorage on mount', async () => {
      localStorage.setItem('user', JSON.stringify(mockUser));
      localStorage.setItem('access_token', 'stored_token');

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
    });

    it('should handle invalid JSON in localStorage gracefully', async () => {
      localStorage.setItem('user', 'invalid json');
      localStorage.setItem('access_token', 'token');

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.user).toBeNull();
      expect(console.error).toHaveBeenCalled();
    });

    it('should not set user if only token exists without user data', async () => {
      localStorage.setItem('access_token', 'token');

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.user).toBeNull();
    });
  });

  describe('login', () => {
    it('should login successfully and store tokens', async () => {
      mockedAuthApi.login.mockResolvedValue(mockLoginResponse);

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const credentials: LoginRequest = {
        email: 'test@example.com',
        password: 'password123',
      };

      await act(async () => {
        await result.current.login(credentials);
      });

      expect(mockedAuthApi.login).toHaveBeenCalledWith(credentials);
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
      expect(localStorage.getItem('access_token')).toBe('test_access_token');
      expect(localStorage.getItem('refresh_token')).toBe('test_refresh_token');
      expect(localStorage.getItem('user')).toBe(JSON.stringify(mockUser));
    });

    it('should clear stale query cache on login (fresh start for the new user)', async () => {
      mockedAuthApi.login.mockResolvedValue(mockLoginResponse);
      // A leftover cache entry from a previous session on the same tab.
      queryClient.setQueryData(['projects'], { items: [{ id: 'p-prev' }] });

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.login({ email: 'test@example.com', password: 'password123' });
      });

      expect(queryClient.getQueryData(['projects'])).toBeUndefined();
    });

    it('should throw error if login response is missing access_token', async () => {
      mockedAuthApi.login.mockResolvedValue({
        ...mockLoginResponse,
        access_token: undefined as unknown as string,
      });

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.login({ email: 'test@example.com', password: 'pass' });
        })
      ).rejects.toThrow('Login failed');
    });

    it('should throw error if login API call fails', async () => {
      const error = new Error('Network error');
      mockedAuthApi.login.mockRejectedValue(error);

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.login({ email: 'test@example.com', password: 'pass' });
        })
      ).rejects.toThrow('Network error');

      expect(console.error).toHaveBeenCalledWith('Login failed:', error);
    });
  });

  describe('logout', () => {
    it('should logout successfully and clear user', async () => {
      mockedAuthApi.logout.mockResolvedValue(undefined);
      localStorage.setItem('user', JSON.stringify(mockUser));
      localStorage.setItem('access_token', 'token');

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(mockedAuthApi.logout).toHaveBeenCalled();
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });

    it('should clear the query cache on logout (no cross-user data leak)', async () => {
      mockedAuthApi.logout.mockResolvedValue(undefined);
      localStorage.setItem('user', JSON.stringify(mockUser));
      localStorage.setItem('access_token', 'token');
      // Seed the singleton cache as if the prior operator had loaded data.
      queryClient.setQueryData(['clients'], [{ id: 'c-prev' }]);

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
      await waitFor(() => expect(result.current.user).toEqual(mockUser));

      await act(async () => {
        await result.current.logout();
      });

      expect(queryClient.getQueryData(['clients'])).toBeUndefined();
    });

    it('should clear user even if logout API call fails', async () => {
      mockedAuthApi.logout.mockRejectedValue(new Error('API error'));
      localStorage.setItem('user', JSON.stringify(mockUser));
      localStorage.setItem('access_token', 'token');

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      // Error will propagate from logout, but user should still be cleared
      await act(async () => {
        try {
          await result.current.logout();
        } catch {
          // Expected error from API call
        }
      });

      expect(result.current.user).toBeNull();
    });
  });

  describe('useAuth hook', () => {
    it('should throw error when used outside AuthProvider', () => {
      expect(() => {
        renderHook(() => useAuth());
      }).toThrow('useAuth must be used within an AuthProvider');
    });
  });
});
