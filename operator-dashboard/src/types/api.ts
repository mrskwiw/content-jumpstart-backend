export interface User {
  id: string;
  email: string;
  full_name: string;
  name?: string; // Deprecated - use full_name
  role?: 'admin' | 'operator' | 'qa_reviewer' | 'account_manager'; // Not used in backend - check is_superuser instead
  is_superuser: boolean;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}
