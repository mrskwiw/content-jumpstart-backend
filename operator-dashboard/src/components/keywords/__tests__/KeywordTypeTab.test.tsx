/**
 * Tests for KeywordTypeTab — list rendering, research-metadata display,
 * add flow, cap enforcement, and the delete undo affordance.
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { KeywordTypeTab } from '../KeywordTypeTab';
import type { ClientKeyword } from '@/api/keywords';

jest.mock('sonner', () => ({
  toast: Object.assign(jest.fn(), { success: jest.fn(), error: jest.fn() }),
}));
jest.mock('@/api/keywords', () => ({
  keywordsApi: {
    addKeyword: jest.fn(),
    updateKeyword: jest.fn(),
    deleteKeyword: jest.fn(),
  },
}));

import { keywordsApi } from '@/api/keywords';
const mockApi = keywordsApi as jest.Mocked<typeof keywordsApi>;

function makeKw(over: Partial<ClientKeyword> = {}): ClientKeyword {
  return {
    id: 1,
    clientId: 'client-1',
    keyword: 'seo tips',
    keywordType: 'primary',
    source: 'manual',
    isActive: true,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...over,
  };
}

function renderTab(keywords: ClientKeyword[], maxCount = 50) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <KeywordTypeTab
        clientId="client-1"
        type="primary"
        keywords={keywords}
        label="Primary"
        maxCount={maxCount}
      />
    </QueryClientProvider>
  );
}

describe('KeywordTypeTab', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders active keywords', () => {
    renderTab([makeKw({ keyword: 'content marketing' })]);
    expect(screen.getByText('content marketing')).toBeInTheDocument();
  });

  it('shows an empty state when there are no keywords', () => {
    renderTab([]);
    expect(screen.getByText(/no primary keywords yet/i)).toBeInTheDocument();
  });

  it('surfaces research metadata (intent, volume, relevance) and source', () => {
    renderTab([
      makeKw({
        source: 'research_tool',
        searchIntent: 'commercial',
        monthlyVolume: '1K-10K',
        relevanceScore: 8.5,
      }),
    ]);
    expect(screen.getByText('commercial')).toBeInTheDocument();
    expect(screen.getByText('1K-10K/mo')).toBeInTheDocument();
    expect(screen.getByText('rel 8.5')).toBeInTheDocument();
    expect(screen.getByText('research')).toBeInTheDocument();
  });

  it('adds a keyword via the API on Enter', async () => {
    mockApi.addKeyword.mockResolvedValue(makeKw({ id: 2, keyword: 'new kw' }));
    renderTab([]);
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText(/add primary keyword/i), 'new kw{Enter}');
    await waitFor(() =>
      expect(mockApi.addKeyword).toHaveBeenCalledWith('client-1', {
        keyword: 'new kw',
        keywordType: 'primary',
      })
    );
  });

  it('disables adding when at the per-type cap', () => {
    const kws = Array.from({ length: 3 }, (_, i) => makeKw({ id: i + 1, keyword: `k${i}` }));
    renderTab(kws, 3);
    expect(screen.getByText(/maximum 3 primary keywords reached/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/add primary keyword/i)).toBeDisabled();
  });

  it('shows an undo toast when a keyword is deleted', async () => {
    const { toast } = jest.requireMock('sonner') as { toast: jest.Mock };
    renderTab([makeKw({ keyword: 'remove me' })]);
    const user = userEvent.setup();
    await user.click(screen.getByLabelText('Delete keyword'));
    expect(toast).toHaveBeenCalledWith('Keyword removed', expect.anything());
  });
});
