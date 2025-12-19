import { render, screen, waitFor } from '@testing-library/react';
import Projects from '@/pages/Projects';
import { renderWithProviders } from '@/test-utils';
import '@testing-library/jest-dom';

jest.mock('@/api/projects', () => ({
  projectsApi: {
    list: jest.fn().mockResolvedValue([
      {
        id: 'p1',
        clientId: 'c1',
        name: 'Demo Project',
        status: 'ready',
        templates: ['t1', 't2'],
        platforms: ['linkedin'],
        lastRunAt: new Date().toISOString(),
      },
    ]),
  },
}));

describe('Projects page', () => {
  it('renders projects from API', async () => {
    const { wrapper } = renderWithProviders();
    render(<Projects />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Demo Project/)).toBeInTheDocument();
    });

    expect(screen.getByText(/ready/i)).toBeInTheDocument();
    expect(screen.getByText(/ID: p1/i)).toBeInTheDocument();
  });
});
