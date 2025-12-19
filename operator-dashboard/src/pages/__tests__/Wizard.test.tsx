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
  },
}));

jest.mock('@/api/runs', () => ({
  runsApi: {
    list: jest.fn().mockResolvedValue([]),
  },
}));

jest.mock('@/api/posts', () => ({
  postsApi: {
    list: jest.fn().mockResolvedValue([
      {
        id: 'post1',
        projectId: 'p1',
        runId: 'r1',
        content: 'foo',
        status: 'flagged',
        flags: ['too short', 'missing CTA'],
      },
    ]),
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
  it('renders flagged posts in quality gate', async () => {
    const { wrapper } = renderWithProviders([
      { pathname: '/dashboard/wizard', state: { projectId: 'p1', clientId: 'c1' } },
    ]);
    render(<Wizard />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Flagged posts: 1/)).toBeInTheDocument();
    });
    expect(screen.getByText(/missing CTA/i)).toBeInTheDocument();
  });
});
