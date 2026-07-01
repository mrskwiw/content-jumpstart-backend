import { z } from 'zod';
import apiClient from './client';

export const KeywordTypeValues = ['primary', 'secondary', 'negative', 'quick_win'] as const;
export type KeywordType = (typeof KeywordTypeValues)[number];

export const KeywordResponseSchema = z.object({
  id: z.number(),
  clientId: z.string().optional(),
  client_id: z.string().optional(),
  researchResultId: z.string().nullish(),
  research_result_id: z.string().nullish(),
  keyword: z.string(),
  keywordType: z.string().optional(),
  keyword_type: z.string().optional(),
  searchIntent: z.string().nullish(),
  search_intent: z.string().nullish(),
  difficulty: z.string().nullish(),
  monthlyVolume: z.string().nullish(),
  monthly_volume: z.string().nullish(),
  relevanceScore: z.number().nullish(),
  relevance_score: z.number().nullish(),
  qualityScore: z.number().nullish(),
  quality_score: z.number().nullish(),
  source: z.string(),
  isActive: z.boolean().optional(),
  is_active: z.boolean().optional(),
  notes: z.string().nullish(),
  createdAt: z.string().optional(),
  created_at: z.string().optional(),
  updatedAt: z.string().optional(),
  updated_at: z.string().optional(),
});

export type ClientKeyword = {
  id: number;
  clientId: string;
  researchResultId?: string | null;
  keyword: string;
  keywordType: KeywordType;
  searchIntent?: string | null;
  difficulty?: string | null;
  monthlyVolume?: string | null;
  relevanceScore?: number | null;
  qualityScore?: number | null;
  source: 'research_tool' | 'manual';
  isActive: boolean;
  notes?: string | null;
  createdAt: string;
  updatedAt: string;
};

export type KeywordListResponse = {
  primary: ClientKeyword[];
  secondary: ClientKeyword[];
  negative: ClientKeyword[];
  quick_win: ClientKeyword[];
  total: number;
};

export interface KeywordCreate {
  keyword: string;
  keywordType: KeywordType;
  searchIntent?: string;
  difficulty?: string;
  monthlyVolume?: string;
  relevanceScore?: number;
  qualityScore?: number;
  notes?: string;
}

export interface KeywordBulkResult {
  imported: number;
  skipped: number;
  deactivated: number;
  message: string;
}

export interface KeywordUpdate {
  keyword?: string;
  searchIntent?: string;
  difficulty?: string;
  notes?: string;
  isActive?: boolean;
}

function normalise(raw: z.infer<typeof KeywordResponseSchema>): ClientKeyword {
  return {
    id: raw.id,
    clientId: (raw.clientId ?? raw.client_id) as string,
    researchResultId: raw.researchResultId ?? raw.research_result_id,
    keyword: raw.keyword,
    keywordType: ((raw.keywordType ?? raw.keyword_type) as KeywordType) ?? 'negative',
    searchIntent: raw.searchIntent ?? raw.search_intent,
    difficulty: raw.difficulty,
    monthlyVolume: raw.monthlyVolume ?? raw.monthly_volume,
    relevanceScore: raw.relevanceScore ?? raw.relevance_score,
    qualityScore: raw.qualityScore ?? raw.quality_score,
    source: raw.source as 'research_tool' | 'manual',
    isActive: (raw.isActive ?? raw.is_active) ?? true,
    notes: raw.notes,
    createdAt: (raw.createdAt ?? raw.created_at) as string,
    updatedAt: (raw.updatedAt ?? raw.updated_at) as string,
  };
}

const KeywordListResponseSchema = z.object({
  primary: z.array(KeywordResponseSchema),
  secondary: z.array(KeywordResponseSchema),
  negative: z.array(KeywordResponseSchema),
  quick_win: z.array(KeywordResponseSchema),
  total: z.number(),
});

export const keywordsApi = {
  async getKeywords(clientId: string, type?: KeywordType): Promise<KeywordListResponse> {
    const params = type ? { type } : {};
    const { data } = await apiClient.get(`/api/clients/${clientId}/keywords`, { params });
    const parsed = KeywordListResponseSchema.parse(data);
    return {
      primary: parsed.primary.map(normalise),
      secondary: parsed.secondary.map(normalise),
      negative: parsed.negative.map(normalise),
      quick_win: parsed.quick_win.map(normalise),
      total: parsed.total,
    };
  },

  async getKeywordsByType(clientId: string, type: KeywordType): Promise<ClientKeyword[]> {
    const result = await keywordsApi.getKeywords(clientId, type);
    return result[type];
  },

  async addKeyword(clientId: string, payload: KeywordCreate): Promise<ClientKeyword> {
    const body = {
      keyword: payload.keyword,
      keyword_type: payload.keywordType,
      search_intent: payload.searchIntent,
      difficulty: payload.difficulty,
      notes: payload.notes,
    };
    const { data } = await apiClient.post(`/api/clients/${clientId}/keywords`, body);
    return normalise(KeywordResponseSchema.parse(data));
  },

  async updateKeyword(
    clientId: string,
    keywordId: number,
    payload: KeywordUpdate
  ): Promise<ClientKeyword> {
    const body: Record<string, unknown> = {};
    if (payload.keyword !== undefined) body.keyword = payload.keyword;
    if (payload.searchIntent !== undefined) body.search_intent = payload.searchIntent;
    if (payload.difficulty !== undefined) body.difficulty = payload.difficulty;
    if (payload.notes !== undefined) body.notes = payload.notes;
    if (payload.isActive !== undefined) body.is_active = payload.isActive;
    const { data } = await apiClient.put(
      `/api/clients/${clientId}/keywords/${keywordId}`,
      body
    );
    return normalise(KeywordResponseSchema.parse(data));
  },

  async deleteKeyword(clientId: string, keywordId: number): Promise<void> {
    await apiClient.delete(`/api/clients/${clientId}/keywords/${keywordId}`);
  },

  async bulkUpsert(clientId: string, keywords: KeywordCreate[]): Promise<KeywordBulkResult> {
    // Backend caps a single bulk request at 50 items (KeywordBulkUpsert).
    const body = {
      keywords: keywords.map((k) => ({
        keyword: k.keyword,
        keyword_type: k.keywordType,
        search_intent: k.searchIntent,
        difficulty: k.difficulty,
        monthly_volume: k.monthlyVolume,
        relevance_score: k.relevanceScore,
        quality_score: k.qualityScore,
        notes: k.notes,
      })),
    };
    const { data } = await apiClient.post(`/api/clients/${clientId}/keywords/bulk`, body);
    return {
      imported: data.imported ?? 0,
      skipped: data.skipped ?? 0,
      deactivated: data.deactivated ?? 0,
      message: data.message ?? '',
    };
  },

  async importFromResult(
    clientId: string,
    resultId: string
  ): Promise<{ imported: number; skipped: number; message: string }> {
    const { data } = await apiClient.post(
      `/api/clients/${clientId}/keywords/import/${resultId}`
    );
    return data;
  },
};
