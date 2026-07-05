/**
 * Unit tests for keywords API module.
 *
 * Tests the normalise() function (snake_case ↔ camelCase), schema validation,
 * and all keywordsApi methods (request URLs, payload shapes, return types).
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import type { AxiosInstance } from 'axios';
import apiClient from '../client';
import { keywordsApi, KeywordResponseSchema, type ClientKeyword, type KeywordType } from '../keywords';

// ---------------------------------------------------------------------------
// Mock the shared API client
// ---------------------------------------------------------------------------

jest.mock('../client');

const mockedApiClient = apiClient as jest.Mocked<AxiosInstance>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeSnakeCaseResponse(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    client_id: 'client-abc',
    research_result_id: null,
    keyword: 'content marketing',
    keyword_type: 'primary',
    search_intent: 'informational',
    difficulty: 'medium',
    monthly_volume: '1K-10K',
    relevance_score: 8.5,
    quality_score: 75.0,
    source: 'manual',
    is_active: true,
    notes: 'Focus keyword',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    ...overrides,
  };
}

function makeCamelCaseResponse(overrides: Record<string, unknown> = {}) {
  return {
    id: 2,
    clientId: 'client-xyz',
    researchResultId: 'rr-001',
    keyword: 'seo audit',
    keywordType: 'secondary',
    searchIntent: 'commercial',
    difficulty: 'high',
    monthlyVolume: '100-1K',
    relevanceScore: 7.0,
    qualityScore: 60.0,
    source: 'research_tool',
    isActive: true,
    notes: null,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-02T00:00:00Z',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// KeywordResponseSchema
// ---------------------------------------------------------------------------

describe('KeywordResponseSchema', () => {
  it('parses snake_case backend response', () => {
    const raw = makeSnakeCaseResponse();
    const parsed = KeywordResponseSchema.parse(raw);
    expect(parsed.id).toBe(1);
    expect(parsed.keyword).toBe('content marketing');
    expect(parsed.is_active).toBe(true);
  });

  it('parses camelCase response', () => {
    const raw = makeCamelCaseResponse();
    const parsed = KeywordResponseSchema.parse(raw);
    expect(parsed.id).toBe(2);
    expect(parsed.keywordType).toBe('secondary');
  });

  it('accepts null / undefined optional fields', () => {
    const raw = makeSnakeCaseResponse({
      research_result_id: null,
      search_intent: null,
      difficulty: null,
      monthly_volume: null,
      relevance_score: null,
      quality_score: null,
      notes: null,
    });
    expect(() => KeywordResponseSchema.parse(raw)).not.toThrow();
  });

  it('rejects missing required fields', () => {
    expect(() =>
      KeywordResponseSchema.parse({ keyword: 'test', source: 'manual' })
    ).toThrow();
  });
});

// ---------------------------------------------------------------------------
// normalise() — indirect test via getKeywords()
// ---------------------------------------------------------------------------

describe('normalise() via getKeywords()', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('maps snake_case fields to camelCase', async () => {
    const snakeList = {
      primary: [makeSnakeCaseResponse()],
      secondary: [],
      negative: [],
      quick_win: [],
      total: 1,
    };
    (mockedApiClient.get as jest.MockedFunction<AxiosInstance['get']>).mockResolvedValue({ data: snakeList } as any);

    const result = await keywordsApi.getKeywords('client-abc');
    const kw = result.primary[0];

    expect(kw.clientId).toBe('client-abc');
    expect(kw.keywordType).toBe('primary');
    expect(kw.searchIntent).toBe('informational');
    expect(kw.monthlyVolume).toBe('1K-10K');
    expect(kw.relevanceScore).toBe(8.5);
    expect(kw.qualityScore).toBe(75.0);
    expect(kw.isActive).toBe(true);
    expect(kw.createdAt).toBe('2026-01-01T00:00:00Z');
  });

  it('maps camelCase fields when backend sends them', async () => {
    const camelList = {
      primary: [],
      secondary: [makeCamelCaseResponse()],
      negative: [],
      quick_win: [],
      total: 1,
    };
    (mockedApiClient.get as jest.MockedFunction<AxiosInstance['get']>).mockResolvedValue({ data: camelList } as any);

    const result = await keywordsApi.getKeywords('client-xyz');
    const kw = result.secondary[0];

    expect(kw.clientId).toBe('client-xyz');
    expect(kw.keywordType).toBe('secondary');
    expect(kw.researchResultId).toBe('rr-001');
  });

  it('defaults isActive to true when both keys absent', async () => {
    const raw = { ...makeSnakeCaseResponse() };
    // @ts-expect-error — intentionally removing both to test fallback
    delete raw.is_active;
    const list = { primary: [raw], secondary: [], negative: [], quick_win: [], total: 1 };
    (mockedApiClient.get as jest.MockedFunction<AxiosInstance['get']>).mockResolvedValue({ data: list } as any);

    const result = await keywordsApi.getKeywords('client-abc');
    expect(result.primary[0].isActive).toBe(true);
  });

  it('defaults keywordType to "negative" when both keys absent', async () => {
    const raw = { ...makeSnakeCaseResponse() };
    // @ts-expect-error — intentionally removing both keys
    delete raw.keyword_type;
    const list = { primary: [raw], secondary: [], negative: [], quick_win: [], total: 1 };
    (mockedApiClient.get as jest.MockedFunction<AxiosInstance['get']>).mockResolvedValue({ data: list } as any);

    const result = await keywordsApi.getKeywords('client-abc');
    expect(result.primary[0].keywordType).toBe('negative');
  });
});

// ---------------------------------------------------------------------------
// getKeywords()
// ---------------------------------------------------------------------------

describe('getKeywords()', () => {
  beforeEach(() => { jest.clearAllMocks(); });

  it('calls correct URL without type filter', async () => {
    const empty = { primary: [], secondary: [], negative: [], quick_win: [], total: 0 };
    (mockedApiClient.get as jest.MockedFunction<AxiosInstance['get']>).mockResolvedValue({ data: empty } as any);

    await keywordsApi.getKeywords('client-123');

    expect(mockedApiClient.get).toHaveBeenCalledWith('/api/clients/client-123/keywords', { params: {} });
  });

  it('passes type filter as query param', async () => {
    const empty = { primary: [], secondary: [], negative: [], quick_win: [], total: 0 };
    (mockedApiClient.get as jest.MockedFunction<AxiosInstance['get']>).mockResolvedValue({ data: empty } as any);

    await keywordsApi.getKeywords('client-123', 'negative');

    expect(mockedApiClient.get).toHaveBeenCalledWith(
      '/api/clients/client-123/keywords',
      { params: { type: 'negative' } }
    );
  });

  it('returns grouped structure', async () => {
    const response = {
      primary: [makeSnakeCaseResponse()],
      secondary: [],
      negative: [],
      quick_win: [],
      total: 1,
    };
    (mockedApiClient.get as jest.MockedFunction<AxiosInstance['get']>).mockResolvedValue({ data: response } as any);

    const result = await keywordsApi.getKeywords('client-123');
    expect(result.total).toBe(1);
    expect(result.primary).toHaveLength(1);
    expect(result.secondary).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// getKeywordsByType()
// ---------------------------------------------------------------------------

describe('getKeywordsByType()', () => {
  beforeEach(() => { jest.clearAllMocks(); });

  it('returns only the requested type array', async () => {
    const response = {
      primary: [makeSnakeCaseResponse()],
      secondary: [],
      negative: [],
      quick_win: [],
      total: 1,
    };
    (mockedApiClient.get as jest.MockedFunction<AxiosInstance['get']>).mockResolvedValue({ data: response } as any);

    const result = await keywordsApi.getKeywordsByType('client-123', 'primary');
    expect(result).toHaveLength(1);
    expect(result[0].keywordType).toBe('primary');
  });

  it('returns empty array for a type with no keywords', async () => {
    const response = { primary: [], secondary: [], negative: [], quick_win: [], total: 0 };
    (mockedApiClient.get as jest.MockedFunction<AxiosInstance['get']>).mockResolvedValue({ data: response } as any);

    const result = await keywordsApi.getKeywordsByType('client-123', 'negative');
    expect(result).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// addKeyword()
// ---------------------------------------------------------------------------

describe('addKeyword()', () => {
  beforeEach(() => { jest.clearAllMocks(); });

  it('converts camelCase payload to snake_case for backend', async () => {
    (mockedApiClient.post as jest.MockedFunction<AxiosInstance['post']>).mockResolvedValue({
      data: makeSnakeCaseResponse({ keyword: 'email strategy', keyword_type: 'primary' }),
    } as any);

    await keywordsApi.addKeyword('client-abc', {
      keyword: 'email strategy',
      keywordType: 'primary',
      searchIntent: 'informational',
      difficulty: 'medium',
      notes: 'key focus',
    });

    expect(mockedApiClient.post).toHaveBeenCalledWith('/api/clients/client-abc/keywords', {
      keyword: 'email strategy',
      keyword_type: 'primary',
      search_intent: 'informational',
      difficulty: 'medium',
      notes: 'key focus',
    });
  });

  it('returns normalised ClientKeyword', async () => {
    (mockedApiClient.post as jest.MockedFunction<AxiosInstance['post']>).mockResolvedValue({
      data: makeSnakeCaseResponse(),
    } as any);

    const result = await keywordsApi.addKeyword('client-abc', {
      keyword: 'content marketing',
      keywordType: 'primary',
    });

    expect(result.keyword).toBe('content marketing');
    expect(result.keywordType).toBe('primary');
    expect(result.source).toBe('manual');
  });
});

// ---------------------------------------------------------------------------
// updateKeyword()
// ---------------------------------------------------------------------------

describe('updateKeyword()', () => {
  beforeEach(() => { jest.clearAllMocks(); });

  it('sends only provided fields as snake_case', async () => {
    (mockedApiClient.put as jest.MockedFunction<AxiosInstance['put']>).mockResolvedValue({
      data: makeSnakeCaseResponse({ notes: 'Updated note' }),
    } as any);

    await keywordsApi.updateKeyword('client-abc', 1, { notes: 'Updated note' });

    expect(mockedApiClient.put).toHaveBeenCalledWith(
      '/api/clients/client-abc/keywords/1',
      { notes: 'Updated note' }
    );
  });

  it('converts isActive → is_active', async () => {
    (mockedApiClient.put as jest.MockedFunction<AxiosInstance['put']>).mockResolvedValue({
      data: makeSnakeCaseResponse({ is_active: false }),
    } as any);

    await keywordsApi.updateKeyword('client-abc', 1, { isActive: false });

    expect(mockedApiClient.put).toHaveBeenCalledWith(
      '/api/clients/client-abc/keywords/1',
      { is_active: false }
    );
  });

  it('converts searchIntent → search_intent', async () => {
    (mockedApiClient.put as jest.MockedFunction<AxiosInstance['put']>).mockResolvedValue({
      data: makeSnakeCaseResponse(),
    } as any);

    await keywordsApi.updateKeyword('client-abc', 1, { searchIntent: 'commercial' });

    const call = (mockedApiClient.put as jest.MockedFunction<AxiosInstance['put']>).mock.calls[0];
    expect((call[1] as Record<string, unknown>)['search_intent']).toBe('commercial');
    expect((call[1] as Record<string, unknown>)['searchIntent']).toBeUndefined();
  });

  it('omits undefined fields', async () => {
    (mockedApiClient.put as jest.MockedFunction<AxiosInstance['put']>).mockResolvedValue({
      data: makeSnakeCaseResponse(),
    } as any);

    await keywordsApi.updateKeyword('client-abc', 1, {});

    const call = (mockedApiClient.put as jest.MockedFunction<AxiosInstance['put']>).mock.calls[0];
    expect(call[1]).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// deleteKeyword()
// ---------------------------------------------------------------------------

describe('deleteKeyword()', () => {
  beforeEach(() => { jest.clearAllMocks(); });

  it('calls DELETE on correct URL', async () => {
    (mockedApiClient.delete as jest.MockedFunction<AxiosInstance['delete']>).mockResolvedValue({} as any);

    await keywordsApi.deleteKeyword('client-abc', 42);

    expect(mockedApiClient.delete).toHaveBeenCalledWith('/api/clients/client-abc/keywords/42');
  });

  it('returns void on success', async () => {
    (mockedApiClient.delete as jest.MockedFunction<AxiosInstance['delete']>).mockResolvedValue({} as any);

    const result = await keywordsApi.deleteKeyword('client-abc', 1);
    expect(result).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// importFromResult()
// ---------------------------------------------------------------------------

describe('importFromResult()', () => {
  beforeEach(() => { jest.clearAllMocks(); });

  it('posts to correct URL', async () => {
    (mockedApiClient.post as jest.MockedFunction<AxiosInstance['post']>).mockResolvedValue({
      data: { imported: 5, skipped: 0, message: 'Imported 5 keywords.' },
    } as any);

    await keywordsApi.importFromResult('client-abc', 'rr-001');

    expect(mockedApiClient.post).toHaveBeenCalledWith(
      '/api/clients/client-abc/keywords/import/rr-001'
    );
  });

  it('returns import stats', async () => {
    (mockedApiClient.post as jest.MockedFunction<AxiosInstance['post']>).mockResolvedValue({
      data: { imported: 3, skipped: 2, message: 'Imported 3 keywords from research result.' },
    } as any);

    const result = await keywordsApi.importFromResult('client-abc', 'rr-001');
    expect(result.imported).toBe(3);
    expect(result.skipped).toBe(2);
    expect(result.message).toBe('Imported 3 keywords from research result.');
  });
});

// ---------------------------------------------------------------------------
// bulkUpsert()
// ---------------------------------------------------------------------------

describe('bulkUpsert()', () => {
  beforeEach(() => { jest.clearAllMocks(); });

  it('maps camelCase items to snake_case and posts to /bulk', async () => {
    (mockedApiClient.post as jest.MockedFunction<AxiosInstance['post']>).mockResolvedValue({
      data: { imported: 2, skipped: 1, deactivated: 0, message: 'Done: 2 added, 1 already existed.' },
    } as any);

    const result = await keywordsApi.bulkUpsert('client-abc', [
      {
        keyword: 'seo audit',
        keywordType: 'primary',
        searchIntent: 'commercial',
        monthlyVolume: '1K-10K',
        relevanceScore: 8.5,
        qualityScore: 90,
      },
      { keyword: 'cheap tools', keywordType: 'negative' },
    ]);

    expect(mockedApiClient.post).toHaveBeenCalledWith('/api/clients/client-abc/keywords/bulk', {
      keywords: [
        {
          keyword: 'seo audit',
          keyword_type: 'primary',
          search_intent: 'commercial',
          difficulty: undefined,
          monthly_volume: '1K-10K',
          relevance_score: 8.5,
          quality_score: 90,
          notes: undefined,
        },
        {
          keyword: 'cheap tools',
          keyword_type: 'negative',
          search_intent: undefined,
          difficulty: undefined,
          monthly_volume: undefined,
          relevance_score: undefined,
          quality_score: undefined,
          notes: undefined,
        },
      ],
    });
    expect(result.imported).toBe(2);
    expect(result.skipped).toBe(1);
    expect(result.deactivated).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// KeywordType values
// ---------------------------------------------------------------------------

describe('KeywordTypeValues', () => {
  it('covers all four types', () => {
    const { KeywordTypeValues } = require('../keywords');
    expect(KeywordTypeValues).toContain('primary');
    expect(KeywordTypeValues).toContain('secondary');
    expect(KeywordTypeValues).toContain('negative');
    expect(KeywordTypeValues).toContain('quick_win');
  });
});
