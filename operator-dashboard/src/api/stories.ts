import apiClient from './client';

/** A single narrative section of a story (e.g. challenge, results). Free-form key/value content rendered by the UI. */
export type StorySection = Record<string, unknown>;

/** Structured, sectioned narrative body of a story. Sections are optional and rendered when present. */
export interface StoryContent {
  customer_background?: StorySection;
  challenge?: StorySection;
  decision_process?: StorySection;
  implementation?: StorySection;
  results?: StorySection;
  testimonials?: StorySection;
  future_plans?: StorySection;
  [section: string]: StorySection | undefined;
}

/** Named quantitative results for a story; values are rendered as text in the UI. */
export type StoryMetrics = Record<string, string | number | boolean>;

export interface Story {
  id: string;
  clientId: string;
  projectId?: string;
  userId: string;
  storyType?: string;
  title?: string;
  summary?: string;
  fullStory?: StoryContent;
  keyMetrics?: StoryMetrics;
  emotionalHook?: string;
  source?: string;
  createdAt: string;
  updatedAt: string;
  usageCount: number;
  platformsUsed: string[];
}

export interface StoryListResponse {
  stories: Story[];
  total: number;
}

export interface CreateStoryInput {
  clientId: string;
  projectId?: string;
  storyType?: string;
  title?: string;
  summary?: string;
  fullStory?: StoryContent;
  keyMetrics?: StoryMetrics;
  emotionalHook?: string;
  source?: string;
}

export interface UpdateStoryInput {
  storyType?: string;
  title?: string;
  summary?: string;
  fullStory?: StoryContent;
  keyMetrics?: StoryMetrics;
  emotionalHook?: string;
  source?: string;
}

export interface StoryUsage {
  id: string;
  storyId: string;
  postId: string;
  platform?: string;
  usageType?: string;
  templateId?: number;
  usedAt: string;
}

export interface TrackUsageInput {
  storyId: string;
  postId: string;
  platform?: string;
  usageType?: string;
  templateId?: number;
}

export interface StoryAnalytics {
  storyId: string;
  title?: string;
  totalUses: number;
  platformsUsed: string[];
  templatesUsed: number[];
  firstUsed?: string;
  lastUsed?: string;
}

export const storiesApi = {
  async listClientStories(clientId: string, storyType?: string, limit = 100): Promise<StoryListResponse> {
    const params = new URLSearchParams();
    if (storyType) params.append('story_type', storyType);
    params.append('limit', limit.toString());

    const { data } = await apiClient.get<StoryListResponse>(
      `/api/stories/client/${clientId}?${params.toString()}`
    );
    return data;
  },

  async get(storyId: string): Promise<Story> {
    const { data } = await apiClient.get<Story>(`/api/stories/${storyId}`);
    return data;
  },

  async create(input: CreateStoryInput): Promise<Story> {
    const backendInput: Record<string, unknown> = {
      client_id: input.clientId,
    };

    if (input.projectId !== undefined) backendInput.project_id = input.projectId;
    if (input.storyType !== undefined) backendInput.story_type = input.storyType;
    if (input.title !== undefined) backendInput.title = input.title;
    if (input.summary !== undefined) backendInput.summary = input.summary;
    if (input.fullStory !== undefined) backendInput.full_story = input.fullStory;
    if (input.keyMetrics !== undefined) backendInput.key_metrics = input.keyMetrics;
    if (input.emotionalHook !== undefined) backendInput.emotional_hook = input.emotionalHook;
    if (input.source !== undefined) backendInput.source = input.source;

    const { data } = await apiClient.post<Story>('/api/stories/', backendInput);
    return data;
  },

  async update(storyId: string, input: UpdateStoryInput): Promise<Story> {
    const backendInput: Record<string, unknown> = {};

    if (input.storyType !== undefined) backendInput.story_type = input.storyType;
    if (input.title !== undefined) backendInput.title = input.title;
    if (input.summary !== undefined) backendInput.summary = input.summary;
    if (input.fullStory !== undefined) backendInput.full_story = input.fullStory;
    if (input.keyMetrics !== undefined) backendInput.key_metrics = input.keyMetrics;
    if (input.emotionalHook !== undefined) backendInput.emotional_hook = input.emotionalHook;
    if (input.source !== undefined) backendInput.source = input.source;

    const { data } = await apiClient.put<Story>(`/api/stories/${storyId}`, backendInput);
    return data;
  },

  async delete(storyId: string): Promise<void> {
    await apiClient.delete(`/api/stories/${storyId}`);
  },

  async trackUsage(input: TrackUsageInput): Promise<StoryUsage> {
    const backendInput: Record<string, unknown> = {
      story_id: input.storyId,
      post_id: input.postId,
    };

    if (input.platform !== undefined) backendInput.platform = input.platform;
    if (input.usageType !== undefined) backendInput.usage_type = input.usageType;
    if (input.templateId !== undefined) backendInput.template_id = input.templateId;

    const { data } = await apiClient.post<StoryUsage>('/api/stories/usage', backendInput);
    return data;
  },

  async getAvailableStories(
    clientId: string,
    platform?: string,
    storyType?: string,
    limit = 10
  ): Promise<StoryListResponse> {
    const requestBody: Record<string, unknown> = {
      client_id: clientId,
      limit,
    };

    if (platform !== undefined) requestBody.platform = platform;
    if (storyType !== undefined) requestBody.story_type = storyType;

    const { data } = await apiClient.post<StoryListResponse>('/api/stories/available', requestBody);
    return data;
  },

  async getAnalytics(storyId: string): Promise<StoryAnalytics> {
    const { data } = await apiClient.get<StoryAnalytics>(`/api/stories/${storyId}/analytics`);
    return data;
  },

  async getClientAnalytics(clientId: string): Promise<StoryAnalytics[]> {
    const { data } = await apiClient.get<StoryAnalytics[]>(`/api/stories/client/${clientId}/analytics`);
    return data;
  },
};
