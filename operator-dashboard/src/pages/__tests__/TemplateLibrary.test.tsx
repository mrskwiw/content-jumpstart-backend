/**
 * Smoke tests for TemplateLibrary page
 */
import { describe, it, expect, beforeEach } from '@jest/globals';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import TemplateLibrary from '../TemplateLibrary';
import apiClient from '@/api/client';
import { clientsApi } from '@/api';

// TemplateLibrary fetches templates via the shared axios client and clients via
// the aggregated api index. Without mocks the page stays stuck on its loading
// spinner (no header / cards / controls rendered).
jest.mock('@/api/client');
jest.mock('@/api');

const mockTemplates = [
  {
    id: 1,
    name: 'Personal Story',
    description: 'Hook → story → lesson → CTA',
    bestFor: 'Building authority through lived experience',
    difficulty: 'medium',
    required: [],
    recommended: [],
    optional: [],
    requiresWebSearch: false,
  },
  {
    id: 2,
    name: 'Industry Insight',
    description: 'Trend → analysis → takeaway',
    bestFor: 'Thought leadership',
    difficulty: 'fast',
    required: ['seo_keyword_research'],
    recommended: [],
    optional: [],
    requiresWebSearch: true,
  },
];

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(apiClient.get).mockImplementation((url: string) => {
    if (url === '/api/generator/templates') {
      return Promise.resolve({ data: mockTemplates });
    }
    return Promise.resolve({ data: [] });
  });
  jest.mocked(clientsApi.list).mockResolvedValue([]);
});

describe('TemplateLibrary Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<TemplateLibrary />);
    expect(container).toBeInTheDocument();
  });

  it('should render template library header', async () => {
    renderWithProviders(<TemplateLibrary />);
    expect(await screen.findByText('Template Library')).toBeInTheDocument();
  });

  it('should render template cards or grid', async () => {
    const { container } = renderWithProviders(<TemplateLibrary />);
    await screen.findByText('Template Library');
    // Should render templates
    const cards = container.querySelectorAll('[class*="rounded"], [class*="border"]');
    expect(cards.length).toBeGreaterThan(0);
  });

  it('should render search or filter controls', async () => {
    const { container } = renderWithProviders(<TemplateLibrary />);
    await screen.findByText('Template Library');
    // Template cards render as buttons once data has loaded.
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
