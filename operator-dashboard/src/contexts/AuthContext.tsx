import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from 'react';
import type { User, LoginRequest } from '@/types/api';
import { authApi } from '@/api/auth';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Proactively refresh the access token on user activity so it never expires
// during an active session. Fires at most once every 15 minutes.
const ACTIVITY_REFRESH_INTERVAL_MS = 15 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const lastRefreshRef = useRef<number>(Date.now());

  // Load user from localStorage on mount
  useEffect(() => {
    const loadUser = () => {
      try {
        const storedUser = localStorage.getItem('user');
        const accessToken = localStorage.getItem('access_token');

        if (storedUser && accessToken) {
          setUser(JSON.parse(storedUser));
        }
      } catch (error) {
        console.error('Failed to load user:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadUser();
  }, []);

  // Silently refresh token on user activity (click or keydown).
  // Debounced to ACTIVITY_REFRESH_INTERVAL_MS so it fires at most once per interval.
  // Keeps the token alive for active users without any perceptible delay.
  useEffect(() => {
    const handleActivity = async () => {
      const now = Date.now();
      if (now - lastRefreshRef.current < ACTIVITY_REFRESH_INTERVAL_MS) return;

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) return;

      try {
        const data = await authApi.refresh(refreshToken);
        localStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token);
        }
        lastRefreshRef.current = now;
      } catch {
        // Refresh failed silently — the 401 interceptor in client.ts will handle
        // it on the next actual API call and redirect to login if needed.
      }
    };

    window.addEventListener('click', handleActivity);
    window.addEventListener('keydown', handleActivity);
    return () => {
      window.removeEventListener('click', handleActivity);
      window.removeEventListener('keydown', handleActivity);
    };
  }, []);

  const login = async (credentials: LoginRequest) => {
    try {
      const response = await authApi.login(credentials);

      if (!response?.access_token || !response?.refresh_token || !response?.user) {
        throw new Error('Login failed: response missing credentials or user data.');
      }

      // Store tokens and user
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
      localStorage.setItem('user', JSON.stringify(response.user));

      setUser(response.user);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
