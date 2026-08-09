import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import { setupMockInterceptor } from '@/mocks/handlers';
import { getApiBaseUrl, getUseMocksEnabled } from '@/utils/env';

const API_URL = getApiBaseUrl();
const USE_MOCKS = getUseMocksEnabled();

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Setup mock interceptor if mocks are enabled
    if (USE_MOCKS) {
      setupMockInterceptor(this.client);
    }

    // Request interceptor - add auth token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('access_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle 401 and token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Entitlement gate: the backend answers 402 `account_expired` on EVERY
        // endpoint an expired account is not allowed to reach, so catching it here
        // — rather than per-page — is what makes the redirect hold no matter which
        // request happens to fire first. Keyed on `code`, not the prose, and not on
        // 402 alone (a future billing error could reuse the status).
        if (error.response?.status === 402) {
          const detail = error.response?.data?.detail;
          if (detail?.code === 'account_expired') {
            const target = detail.subscribe_path || '/subscribe';
            // Guard against a redirect loop if /subscribe itself ever 402s.
            if (window.location.pathname !== target) {
              window.location.href = target;
            }
            return Promise.reject(error);
          }
        }

        // Don't intercept 401 errors for login/refresh endpoints - let them bubble up
        const isAuthEndpoint = originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/refresh');

        // If 401 and we haven't retried yet, and it's not an auth endpoint
        if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
          originalRequest._retry = true;

          try {
            const refreshToken = localStorage.getItem('refresh_token');
            if (!refreshToken) {
              // No refresh token, redirect to login
              window.location.href = '/login';
              return Promise.reject(error);
            }

            // Try to refresh token
            const { data } = await axios.post(`${API_URL}/api/auth/refresh`, {
              refresh_token: refreshToken,
            });

            // Save new tokens (both rotate on every refresh)
            localStorage.setItem('access_token', data.access_token);
            if (data.refresh_token) {
              localStorage.setItem('refresh_token', data.refresh_token);
            }

            // Retry original request with new token
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
            }
            return this.client(originalRequest);
          } catch (refreshError) {
            // Refresh failed, clear tokens and redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  getInstance(): AxiosInstance {
    return this.client;
  }
}

const apiClient = new ApiClient();
export default apiClient.getInstance();
