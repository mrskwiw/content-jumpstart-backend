/**
 * Admin API client functions
 */

import apiClient from './client';

export interface GrantCreditsRequest {
  user_id: string;
  credits: number;
  reason: string;
}

export interface GrantCreditsResponse {
  user_email: string;
  credits_granted: number;
  new_balance: number;
  reason: string;
  granted_by: string;
}

export interface User {
  id: string;
  email: string;
  fullName: string;
  isActive: boolean;
  isSuperuser: boolean;
  createdAt: string;
  updatedAt: string | null;
}

export const adminApi = {
  /**
   * Grant free credits to a user (super admin only)
   */
  async grantCredits(request: GrantCreditsRequest): Promise<GrantCreditsResponse> {
    const response = await apiClient.post('/admin/credits/grant', request);
    return response.data;
  },

  /**
   * Get list of all users (for user selector)
   */
  async listUsers(params?: { skip?: number; limit?: number }): Promise<User[]> {
    const response = await apiClient.get('/admin/users', { params });
    return response.data;
  },
};

export default adminApi;
