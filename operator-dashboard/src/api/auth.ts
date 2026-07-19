import apiClient from './client';
import type { User, LoginRequest, LoginResponse, RefreshTokenResponse } from '@/types/api';

// Backend response type — backend UserResponse uses alias_generator (camelCase)
interface BackendLoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  mfa_setup_required?: boolean;
  mfa_setup_token?: string;
  user: {
    id: string;
    email: string;
    fullName: string;
    isActive: boolean;
    isSuperuser: boolean;
    createdAt: string;
    updatedAt?: string;
  };
}

export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const { data, status, headers } = await apiClient.post<BackendLoginResponse>('/api/auth/login', credentials);

    const contentType = headers['content-type'] || headers['Content-Type'] || '';
    const hasTokens =
      typeof data?.access_token === 'string' &&
      typeof data?.refresh_token === 'string' &&
      typeof data?.user === 'object';

    if (!hasTokens) {
      const snippet = JSON.stringify(data ?? {}, null, 0).slice(0, 120);
      throw new Error(
        `Login failed: unexpected response (status ${status}, content-type ${contentType}). Payload preview: ${snippet}`
      );
    }

    const backendUser = data.user;
    const user: User = {
      id: backendUser.id,
      email: backendUser.email,
      fullName: backendUser.fullName,
      isSuperuser: backendUser.isSuperuser,
      isActive: backendUser.isActive,
      createdAt: backendUser.createdAt,
      updatedAt: backendUser.updatedAt,
    };

    return {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      token_type: data.token_type,
      mfa_setup_required: data.mfa_setup_required,
      mfa_setup_token: data.mfa_setup_token,
      user,
    };
  },

  refresh: async (refreshToken: string): Promise<RefreshTokenResponse> => {
    const { data } = await apiClient.post<RefreshTokenResponse>('/api/auth/refresh', {
      refresh_token: refreshToken,
    });
    return data;
  },

  changePassword: async (
    currentPassword: string,
    newPassword: string
  ): Promise<{ status: string; message: string }> => {
    const { data } = await apiClient.post('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return data;
  },

  logout: async (): Promise<void> => {
    // Call logout endpoint if backend has one
    // await apiClient.post('/api/auth/logout');

    // Clear local storage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
};
