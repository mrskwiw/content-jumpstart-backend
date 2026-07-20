import apiClient from './client';

export interface PlatformCredential {
  id: string;
  platform: string;
  client_id?: string | null;
  account_ref?: string | null;
  display_name?: string | null;
  is_active: boolean;
}

export interface ScheduledPost {
  id: string;
  platform: string;
  content: string;
  status: string;
  scheduled_for: string;
  posted_at?: string | null;
  platform_url?: string | null;
  error_message?: string | null;
  retry_count: number;
}

export interface OAuthStatus {
  configured: string[];
  all: string[];
}

export const distributionApi = {
  async platforms(): Promise<string[]> {
    const { data } = await apiClient.get<{ platforms: string[] }>('/api/distribution/platforms');
    return data.platforms;
  },
  async oauthStatus(): Promise<OAuthStatus> {
    const { data } = await apiClient.get<OAuthStatus>('/api/distribution/oauth/status');
    return data;
  },
  async oauthStart(platform: string): Promise<string> {
    const { data } = await apiClient.get<{ authorize_url: string }>(
      `/api/distribution/oauth/${platform}/start`,
    );
    return data.authorize_url;
  },
  async patchCredential(
    id: string,
    body: { account_ref?: string; display_name?: string; is_active?: boolean },
  ): Promise<PlatformCredential> {
    const { data } = await apiClient.patch<PlatformCredential>(
      `/api/distribution/credentials/${id}`,
      body,
    );
    return data;
  },
  async listCredentials(): Promise<PlatformCredential[]> {
    const { data } = await apiClient.get<PlatformCredential[]>('/api/distribution/credentials');
    return data;
  },
  async connect(body: {
    platform: string;
    access_token: string;
    display_name?: string;
    account_ref?: string;
    client_id?: string;
  }): Promise<PlatformCredential> {
    const { data } = await apiClient.post<PlatformCredential>('/api/distribution/credentials', body);
    return data;
  },
  async deleteCredential(id: string): Promise<void> {
    await apiClient.delete(`/api/distribution/credentials/${id}`);
  },
  async schedule(body: {
    platform: string;
    content: string;
    scheduled_for: string;
    project_id?: string;
    client_id?: string;
    media_url?: string;
  }): Promise<ScheduledPost> {
    const { data } = await apiClient.post<ScheduledPost>('/api/distribution/schedule', body);
    return data;
  },
  async queue(params?: { status?: string; project_id?: string }): Promise<ScheduledPost[]> {
    const { data } = await apiClient.get<ScheduledPost[]>('/api/distribution/queue', { params });
    return data;
  },
  async publishNow(id: string): Promise<ScheduledPost> {
    const { data } = await apiClient.post<ScheduledPost>(`/api/distribution/publish/${id}`);
    return data;
  },
};
