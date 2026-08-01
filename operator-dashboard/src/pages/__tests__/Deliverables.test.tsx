import { render, screen, waitFor } from '@testing-library/react';
import Deliverables from '@/pages/Deliverables';
import { renderWithProviders } from '@/test-utils';

jest.mock('@/api/deliverables', () => ({
  deliverablesApi: {
    list: jest.fn().mockResolvedValue([
      {
        id: 'd1',
        projectId: 'p1',
        clientId: 'c1',
        format: 'docx',
        path: 'outputs/p1/doc.docx',
        createdAt: new Date().toISOString(),
        status: 'ready',
      },
      {
        id: 'd2',
        projectId: 'p1',
        clientId: 'c1',
        format: 'image',
        path: 'media/u/j/asset.png',
        createdAt: new Date().toISOString(),
        status: 'ready',
      },
    ]),
    markDelivered: jest.fn().mockResolvedValue({}),
  },
}));

jest.mock('@/api/clients', () => ({
  clientsApi: {
    // The page resolves client names via clientsApi.list() (getClientName),
    // not clientsApi.get(). Provide both to be safe.
    list: jest.fn().mockResolvedValue([
      {
        id: 'c1',
        name: 'Client c1',
        businessDescription: 'Test business',
        idealCustomer: 'Test customer',
        createdAt: new Date().toISOString(),
      },
    ]),
    get: jest.fn().mockResolvedValue({
      id: 'c1',
      name: 'Client c1',
      businessDescription: 'Test business',
      idealCustomer: 'Test customer',
      createdAt: new Date().toISOString(),
    }),
  },
}));

describe('Deliverables page', () => {
  it('shows grouped deliverables', async () => {
    const { wrapper } = renderWithProviders();
    render(<Deliverables />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Client c1/)).toBeInTheDocument();
    });

    expect(screen.getByText(/outputs\/p1\/doc.docx/i)).toBeInTheDocument();
    // Two deliverables in the mock → one Mark-Delivered control each.
    expect(screen.getAllByText(/Mark Delivered/i).length).toBeGreaterThan(0);
  });

  it('distinguishes media deliverables with a "(media)" format badge', async () => {
    const { wrapper } = renderWithProviders();
    render(<Deliverables />, { wrapper });

    await waitFor(() => expect(screen.getByText(/media\/u\/j\/asset.png/i)).toBeInTheDocument());
    // The image deliverable is flagged as media; the docx one is not.
    expect(screen.getByText('image (media)')).toBeInTheDocument();
    expect(screen.getByText('docx')).toBeInTheDocument();
    expect(screen.queryByText('docx (media)')).not.toBeInTheDocument();
  });
});
