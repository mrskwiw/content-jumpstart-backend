/**
 * Tests for the KeywordEditor page — loads user-scoped keywords, renders the four
 * type tabs, and switches tabs. Research "Refresh" button appears only when a
 * completed SEO research result exists.
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import KeywordEditor from '../KeywordEditor';

jest.mock('sonner', () => ({
  toast: Object.assign(jest.fn(), { success: jest.fn(), error: jest.fn() }),
}));
jest.mock('@/api/keywords', () => ({
  keywordsApi: {
    getKeywords: jest.fn(),
    addKeyword: jest.fn(),
    updateKeyword: jest.fn(),
    deleteKeyword: jest.fn(),
    importFromResult: jest.fn(),
  },
}));
jest.mock('@/api/research', () => ({
  researchApi: { getClientHistory: jest.fn() },
}));

import { keywordsApi } from '@/api/keywords';
import { researchApi } from '@/api/research';
const mockKw = keywordsApi as jest.Mocked<typeof keywordsApi>;
const mockResearch = researchApi as jest.Mocked<typeof researchApi>;

const EMPTY_LIST = { primary: [], secondary: [], negative: [], quick_win: [], total: 0 };

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/dashboard/clients/client-1/keywords']}>
        <Routes>
          <Route path="/dashboard/clients/:clientId/keywords" element={<KeywordEditor />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('KeywordEditor', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockKw.getKeywords.mockResolvedValue(EMPTY_LIST);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mockResearch.getClientHistory.mockResolvedValue({ results: [] } as any);
  });

  it('loads keywords for the routed client', async () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /keyword editor/i })).toBeInTheDocument();
    await waitFor(() => expect(mockKw.getKeywords).toHaveBeenCalledWith('client-1'));
  });

  it('renders all four keyword-type tabs', async () => {
    renderPage();
    for (const label of ['Primary', 'Secondary', 'Negative', 'Quick Wins']) {
      expect(screen.getByRole('button', { name: new RegExp(label, 'i') })).toBeInTheDocument();
    }
    await waitFor(() => expect(mockKw.getKeywords).toHaveBeenCalled());
  });

  it('switches the active tab on click', async () => {
    renderPage();
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /negative/i }));
    await waitFor(() => expect(screen.getByText(/to avoid/i)).toBeInTheDocument());
  });
});
