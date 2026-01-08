import apiClient from './client';
import type { LoginRequest, LoginResponse, RefreshTokenResponse } from '@/types/api';

// Backend response type (may differ from frontend LoginResponse)
interface BackendLoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name?: string;
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

    // Map backend user model to frontend User type
    const backendUser = data.user;
    const user: LoginResponse['user'] = {
      id: String(backendUser.id), // Convert number to string
      email: backendUser.email,
      name: backendUser.full_name || backendUser.email.split('@')[0], // Use full_name or fallback to email prefix
      role: 'operator', // Default role since backend doesn't return it yet
    };

    return {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      token_type: data.token_type,
      user,
    };
  },

  refresh: async (refreshToken: string): Promise<RefreshTokenResponse> => {
    const { data } = await apiClient.post<RefreshTokenResponse>('/api/auth/refresh', {
      refresh_token: refreshToken,
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
