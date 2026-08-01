/**
 * Tests for the engagement/analytics API module — focused on the business-summary
 * boundary normalization (a partial/schema-skewed 200 must not reach the render path).
 */
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import type { AxiosResponse } from 'axios';
import { engagementApi } from '../engagement';
import apiClient from '../client';

jest.mock('../client');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('engagementApi.businessSummary', () => {
  beforeEach(() => jest.clearAllMocks());

  it('passes the days param and returns the full shape', async () => {
    mockedApiClient.get.mockResolvedValue({
      data: {
        days: 30,
        totals: { projects: 4, posts: 100, clients: 2 },
        monthly: [{ month: '2026-07', projects: 4, posts: 100 }],
        by_client: [{ client_name: 'Acme', projects: 4, posts: 100 }],
        by_template: [{ template_name: 'How-To', usage_count: 50 }],
      },
    } as AxiosResponse);

    const s = await engagementApi.businessSummary(30);

    expect(apiClient.get).toHaveBeenCalledWith('/api/analytics/business-summary', {
      params: { days: 30 },
    });
    expect(s.totals.posts).toBe(100);
    expect(s.by_client).toHaveLength(1);
  });

  it('normalizes a partial payload so the render path never sees undefined', async () => {
    // Missing arrays + missing totals fields (e.g. version skew mid-deploy).
    mockedApiClient.get.mockResolvedValue({
      data: { totals: { projects: 3 } },
    } as AxiosResponse);

    const s = await engagementApi.businessSummary(90);

    expect(s.days).toBe(90); // falls back to the requested window
    expect(s.totals).toEqual({ projects: 3, posts: 0, clients: 0 });
    expect(s.monthly).toEqual([]);
    expect(s.by_client).toEqual([]);
    expect(s.by_template).toEqual([]);
  });

  it('normalizes a completely empty body', async () => {
    mockedApiClient.get.mockResolvedValue({ data: undefined } as AxiosResponse);

    const s = await engagementApi.businessSummary(7);

    expect(s.totals).toEqual({ projects: 0, posts: 0, clients: 0 });
    expect(s.monthly).toEqual([]);
  });
});
