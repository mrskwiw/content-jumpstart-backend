/**
 * Tests for auth API module
 */
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import type { AxiosResponse } from 'axios';
import { authApi } from '../auth';
import apiClient from '../client';

// Mock the API client
jest.mock('../client');

const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('Auth API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('login', () => {
    it('should login successfully', async () => {
      const mockResponse = {
        data: {
          access_token: 'token',
          refresh_token: 'refresh',
          token_type: 'bearer',
          user: {
            id: 'user-1',
            email: 'test@example.com',
            full_name: 'Test User',
            is_active: true,
            is_superuser: false,
            createdAt: '2024-01-01T00:00:00Z',
          },
        },
        status: 200,
        headers: { 'content-type': 'application/json' },
      };

      mockedApiClient.post.mockResolvedValue(mockResponse as unknown as AxiosResponse);

      const result = await authApi.login({
        email: 'test@example.com',
        password: 'password123',
      });

      expect(apiClient.post).toHaveBeenCalledWith('/api/auth/login', {
        email: 'test@example.com',
        password: 'password123',
      });

      expect(result.access_token).toBe('token');
      expect(result.refresh_token).toBe('refresh');
      expect(result.user.email).toBe('test@example.com');
    });
  });

  describe('logout', () => {
    it('should clear local storage', async () => {
      // Setup localStorage with tokens
      localStorage.setItem('access_token', 'test-token');
      localStorage.setItem('refresh_token', 'test-refresh');
      localStorage.setItem('user', JSON.stringify({ id: 'user-1' }));

      await authApi.logout();

      // Verify localStorage is cleared
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
      expect(localStorage.getItem('user')).toBeNull();
    });
  });

  describe('refresh', () => {
    it('should refresh access token', async () => {
      const mockResponse = {
        data: {
          access_token: 'new-token',
          token_type: 'bearer',
        },
      };

      mockedApiClient.post.mockResolvedValue(mockResponse as unknown as AxiosResponse);

      const result = await authApi.refresh('old-refresh-token');

      expect(apiClient.post).toHaveBeenCalledWith('/api/auth/refresh', {
        refresh_token: 'old-refresh-token',
      });

      expect(result.access_token).toBe('new-token');
    });
  });
});
