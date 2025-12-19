import axios from 'axios';

/**
 * Map auth/login errors to user-friendly messages without exposing internal details.
 */
export function getAuthErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const data = (error.response?.data || {}) as any;
    const code = data.code || data.error || data.type;
    const detail = data.detail || data.message;
    const bodyAsString = typeof data === 'string' ? data : '';

    if (bodyAsString.toLowerCase().includes('<!doctype') || bodyAsString.toLowerCase().includes('<html')) {
      return 'Received HTML instead of an API response. Check VITE_API_URL and that the backend is running.';
    }

    if (status === 400 && code !== 'invalid_credentials') {
      return detail || 'Request was invalid. Please verify your input.';
    }
    if (status === 401 || code === 'invalid_credentials') {
      return detail || 'Invalid email or password. Please try again.';
    }
    if (status === 404 || code === 'user_not_found') {
      return detail || 'Account not found. Please check your email or ask an admin to create one.';
    }
    if (status === 403) return detail || 'You do not have access to this application.';
    if (status === 429) return detail || 'Too many attempts. Please wait and retry.';
    if (status && status >= 500) return detail || 'Server error. Please try again shortly.';

    if (error.code === 'ERR_NETWORK' || status === 0) {
      return 'Cannot reach the server. Check your connection or VPN and try again.';
    }

    return detail || error.message || 'Unexpected error while signing in. Please retry.';
  }

  if (error instanceof Error) {
    return error.message || 'Unexpected error while signing in. Please retry.';
  }

  return 'Unexpected error while signing in. Please retry.';
}
