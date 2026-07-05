/**
 * Tests for users API module (admin user management)
 */
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { usersApi } from '../users';
import apiClient from '../client';
import type { SystemUser, UserStats, CreateUserRequest } from '@/types/user';

// Mock the API client
jest.mock('../client');

const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('Users API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('list', () => {
    it('should fetch users list with pagination', async () => {
      const mockUsers: SystemUser[] = [
        { id: 'user-1', email: 'test@example.com', fullName: 'Test User', is_active: true, isSuperuser: false, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      ];

      mockedApiClient.get.mockResolvedValue({ data: mockUsers } as any);

      const result = await usersApi.list(0, 100);

      expect(apiClient.get).toHaveBeenCalledWith('/api/admin/users', {
        params: { skip: 0, limit: 100 },
      });

      expect(result).toEqual(mockUsers);
    });
  });

  describe('getStats', () => {
    it('should fetch user statistics', async () => {
      const mockStats: UserStats = {
        total: 10,
        active: 8,
        inactive: 2,
        admins: 1,
      };

      mockedApiClient.get.mockResolvedValue({ data: mockStats } as any);

      const result = await usersApi.getStats();

      expect(apiClient.get).toHaveBeenCalledWith('/api/admin/users/stats');
      expect(result).toEqual(mockStats);
    });
  });

  describe('listInactive', () => {
    it('should fetch inactive users', async () => {
      const mockInactiveUsers: SystemUser[] = [
        { id: 'user-2', email: 'inactive@example.com', fullName: 'Inactive User', is_active: false, isSuperuser: false, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      ];

      mockedApiClient.get.mockResolvedValue({ data: mockInactiveUsers } as any);

      const result = await usersApi.listInactive(0, 100);

      expect(apiClient.get).toHaveBeenCalledWith('/api/admin/users/inactive', {
        params: { skip: 0, limit: 100 },
      });

      expect(result).toEqual(mockInactiveUsers);
    });
  });

  describe('create', () => {
    it('should create new user', async () => {
      const newUser: CreateUserRequest = {
        email: 'new@example.com',
        fullName: 'New User',
        password: 'password123',
        isSuperuser: false,
      };

      const mockResponse: SystemUser = {
        id: 'user-new',
        email: newUser.email,
        fullName: newUser.fullName,
        is_active: true,
        isSuperuser: false, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockResponse } as any);

      const result = await usersApi.create(newUser);

      expect(apiClient.post).toHaveBeenCalledWith('/api/admin/users', {
        email: newUser.email,
        fullName: newUser.fullName,
        password: newUser.password,
        isSuperuser: false,
      });

      expect(result).toEqual(mockResponse);
    });
  });

  describe('activate', () => {
    it('should activate user', async () => {
      const mockUser: SystemUser = {
        id: 'user-1',
        email: 'test@example.com',
        fullName: 'Test User',
        is_active: true,
        isSuperuser: false, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockUser } as any);

      const result = await usersApi.activate('user-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/admin/users/user-1/activate');
      expect(result).toEqual(mockUser);
    });
  });

  describe('deactivate', () => {
    it('should deactivate user', async () => {
      const mockUser: SystemUser = {
        id: 'user-1',
        email: 'test@example.com',
        fullName: 'Test User',
        is_active: false,
        isSuperuser: false, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockUser } as any);

      const result = await usersApi.deactivate('user-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/admin/users/user-1/deactivate');
      expect(result).toEqual(mockUser);
    });
  });

  describe('promote', () => {
    it('should promote user to admin', async () => {
      const mockUser: SystemUser = {
        id: 'user-1',
        email: 'test@example.com',
        fullName: 'Test User',
        is_active: true,
        isSuperuser: true, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockUser } as any);

      const result = await usersApi.promote('user-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/admin/users/user-1/promote');
      expect(result).toEqual(mockUser);
    });
  });

  describe('demote', () => {
    it('should demote user from admin', async () => {
      const mockUser: SystemUser = {
        id: 'user-1',
        email: 'test@example.com',
        fullName: 'Test User',
        is_active: true,
        isSuperuser: false, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockUser } as any);

      const result = await usersApi.demote('user-1');

      expect(apiClient.post).toHaveBeenCalledWith('/api/admin/users/user-1/demote');
      expect(result).toEqual(mockUser);
    });
  });

  describe('resetPassword', () => {
    it('should reset user password', async () => {
      const mockUser: SystemUser = {
        id: 'user-1',
        email: 'test@example.com',
        fullName: 'Test User',
        is_active: true,
        isSuperuser: false, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
      };

      mockedApiClient.post.mockResolvedValue({ data: mockUser } as any);

      const result = await usersApi.resetPassword('user-1', 'newpassword123');

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/admin/users/user-1/reset-password',
        { new_password: 'newpassword123' }
      );

      expect(result).toEqual(mockUser);
    });
  });
});
