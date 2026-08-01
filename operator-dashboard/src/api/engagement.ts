import apiClient from './client';

export interface EngagementTotals {
  posts: number;
  likes: number;
  comments: number;
  shares: number;
  impressions: number;
  reach: number;
  engagement: number;
  engagement_rate: number;
}

export interface PlatformRow extends EngagementTotals {
  platform: string;
}

export interface TemplateRow extends EngagementTotals {
  template: string;
}

export interface TopPost {
  platform: string;
  template?: string | null;
  likes: number;
  comments: number;
  shares: number;
  impressions: number;
  engagement_rate: number;
  platform_url?: string | null;
}

export interface BenchmarkRow extends PlatformRow {
  benchmark_tier: string;
}

export interface DailyPoint extends EngagementTotals {
  date: string;
}

export interface Trend {
  direction: 'up' | 'down' | 'flat';
  change_pct: number;
  recent_rate: number;
  prior_rate: number;
}

// Business summary (GAP-UI-01) — real project/post/client/template activity.
// Revenue and quality are intentionally NOT part of this contract (not tracked).
export interface BusinessSummary {
  days: number;
  totals: { projects: number; posts: number; clients: number };
  monthly: Array<{ month: string; projects: number; posts: number }>;
  by_client: Array<{ client_name: string; projects: number; posts: number }>;
  by_template: Array<{ template_name: string; usage_count: number }>;
}

export const engagementApi = {
  async businessSummary(days = 90): Promise<BusinessSummary> {
    const { data } = await apiClient.get<BusinessSummary>('/api/analytics/business-summary', {
      params: { days },
    });
    return data;
  },
  async collect(): Promise<{ collected: number; skipped: number; dry_run: boolean }> {
    const { data } = await apiClient.post('/api/analytics/collect');
    return data;
  },
  async benchmarks(): Promise<BenchmarkRow[]> {
    const { data } = await apiClient.get<BenchmarkRow[]>('/api/analytics/benchmarks');
    return data;
  },
  async daily(days = 30): Promise<DailyPoint[]> {
    const { data } = await apiClient.get<DailyPoint[]>('/api/analytics/daily', { params: { days } });
    return data;
  },
  async trend(): Promise<Trend> {
    const { data } = await apiClient.get<Trend>('/api/analytics/trend');
    return data;
  },
  async insights(): Promise<string[]> {
    const { data } = await apiClient.get<{ insights: string[] }>('/api/analytics/insights');
    return data.insights;
  },
  async overview(): Promise<EngagementTotals> {
    const { data } = await apiClient.get<EngagementTotals>('/api/analytics/overview');
    return data;
  },
  async byPlatform(): Promise<PlatformRow[]> {
    const { data } = await apiClient.get<PlatformRow[]>('/api/analytics/by-platform');
    return data;
  },
  async byTemplate(): Promise<TemplateRow[]> {
    const { data } = await apiClient.get<TemplateRow[]>('/api/analytics/by-template');
    return data;
  },
  async topPosts(): Promise<TopPost[]> {
    const { data } = await apiClient.get<TopPost[]>('/api/analytics/top-posts');
    return data;
  },
  async reportPdf(): Promise<Blob> {
    const { data } = await apiClient.get<Blob>('/api/analytics/report.pdf', {
      responseType: 'blob',
    });
    return data;
  },
};
