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

        // If 401 and we haven't retried yet
        if (error.response?.status === 401 && !originalRequest._retry) {
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

            // Save new access token
            localStorage.setItem('access_token', data.access_token);

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
