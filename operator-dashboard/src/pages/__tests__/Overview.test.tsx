/**
 * Smoke tests for Overview page
 */
import { describe, it, expect, jest } from '@jest/globals';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Overview from '../Overview';
import { projectsApi } from '@/api/projects';
import { clientsApi } from '@/api/clients';

// Mock API modules
jest.mock('@/api/projects');
jest.mock('@/api/clients');
jest.mock('@/api/deliverables');
jest.mock('@/api/runs');
jest.mock('@/api/posts');

describe('Overview Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Mock empty responses
    (projectsApi.list as any).mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 });
    (clientsApi.list as any).mockResolvedValue([]);
  });

  it('should render without crashing', () => {
    const { container } = renderWithProviders(<Overview />);
    expect(container).toBeInTheDocument();
  });

  it('should render overview header', () => {
    const { container } = renderWithProviders(<Overview />);
    expect(container).toHaveTextContent('Overview');
  });

  it('should render stat cards', () => {
    const { container } = renderWithProviders(<Overview />);
    // Should render metric cards
    const cards = container.querySelectorAll('[class*="rounded"]');
    expect(cards.length).toBeGreaterThan(0);
  });
});
