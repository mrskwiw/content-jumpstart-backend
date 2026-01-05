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
    ]),
    markDelivered: jest.fn().mockResolvedValue({}),
  },
}));

jest.mock('@/api/clients', () => ({
  clientsApi: {
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
    expect(screen.getByText(/Mark Delivered/i)).toBeInTheDocument();
  });
});
