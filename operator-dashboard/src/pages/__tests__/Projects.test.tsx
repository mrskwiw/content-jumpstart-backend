import { render, screen, waitFor } from '@testing-library/react';
import Projects from '@/pages/Projects';
import { renderWithProviders } from '@/test-utils';
import '@testing-library/jest-dom';

jest.mock('@/api/projects', () => ({
  projectsApi: {
    list: jest.fn().mockResolvedValue({
      items: [
        {
          id: 'p1',
          clientId: 'c1',
          name: 'Demo Project',
          status: 'ready',
          templates: ['t1', 't2'],
          platforms: ['linkedin'],
          lastRunAt: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
      hasNextPage: false,
    }),
  },
}));

describe('Projects page', () => {
  it('renders projects from API', async () => {
    const { wrapper } = renderWithProviders();
    render(<Projects />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Demo Project/)).toBeInTheDocument();
    });

    // Check for status - getAllByText since "ready" appears in filter dropdown too
    expect(screen.getAllByText(/ready/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/ID: p1/i)).toBeInTheDocument();
  });
});
