import { render, screen, waitFor } from '@testing-library/react';
import Wizard from '@/pages/Wizard';
import { renderWithProviders } from '@/test-utils';

jest.mock('@/api/projects', () => ({
  projectsApi: {
    get: jest.fn().mockResolvedValue({
      id: 'p1',
      clientId: 'c1',
      name: 'Demo Project',
      status: 'qa',
      templates: ['t1'],
      platforms: ['linkedin'],
    }),
    create: jest.fn(),
  },
}));

jest.mock('@/api/clients', () => ({
  clientsApi: {
    list: jest.fn().mockResolvedValue([]),
    get: jest.fn().mockResolvedValue({ id: 'c1', name: 'Client c1' }),
    create: jest.fn(),
    update: jest.fn(),
  },
}));

jest.mock('@/api/runs', () => ({
  runsApi: {
    list: jest.fn().mockResolvedValue([]),
  },
}));

jest.mock('@/api/posts', () => ({
  postsApi: {
    // The component reads postsResponse.items (paginated shape), not a bare array.
    list: jest.fn().mockResolvedValue({
      items: [
        {
          id: 'post1',
          projectId: 'p1',
          runId: 'r1',
          content: 'foo',
          status: 'flagged',
          flags: ['too short', 'missing CTA'],
          createdAt: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      pageSize: 500,
      totalPages: 1,
    }),
  },
}));

jest.mock('@/api/generator', () => ({
  generatorApi: {
    generateAll: jest.fn().mockResolvedValue({ id: 'run1', projectId: 'p1', startedAt: new Date().toISOString() }),
    regenerate: jest.fn().mockResolvedValue({ id: 'run2', projectId: 'p1', startedAt: new Date().toISOString() }),
    exportPackage: jest.fn().mockResolvedValue({
      id: 'd1',
      projectId: 'p1',
      clientId: 'c1',
      format: 'docx',
      path: 'outputs/doc.docx',
      createdAt: new Date().toISOString(),
      status: 'ready',
    }),
  },
}));

describe('Wizard page', () => {
  it('surfaces the flagged post count in the wizard status panel', async () => {
    const { wrapper } = renderWithProviders([
      { pathname: '/dashboard/wizard', state: { projectId: 'p1', clientId: 'c1' } },
    ]);
    render(<Wizard />, { wrapper });

    // Project + posts queries resolve and populate the always-visible status panel.
    // The labels ("Flagged:", "Generated:") live in a <strong> with the value in a
    // sibling text node, so assert against the containing paragraph's text content.
    await screen.findByText(/Demo Project/);
    await waitFor(() => {
      expect(screen.getByText('Flagged:').parentElement).toHaveTextContent('Flagged: 1');
    });
    expect(screen.getByText('Generated:').parentElement).toHaveTextContent('Generated: 1 posts');
  });
});
