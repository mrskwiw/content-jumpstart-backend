import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Connections from '@/pages/Distribution/Connections';
import { distributionApi } from '@/api/distribution';
import { clientsApi } from '@/api/clients';
import { renderWithProviders } from '@/test-utils';

jest.mock('@/api/distribution', () => ({
  distributionApi: {
    oauthStatus: jest.fn(),
    listCredentials: jest.fn(),
    oauthStart: jest.fn(),
    deleteCredential: jest.fn(),
    patchCredential: jest.fn(),
  },
}));
jest.mock('@/api/clients', () => ({ clientsApi: { list: jest.fn() } }));

const dist = distributionApi as jest.Mocked<typeof distributionApi>;
const clients = clientsApi as jest.Mocked<typeof clientsApi>;

describe('Distribution Connections — per-client OAuth (MULTICLIENT-01)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    dist.oauthStatus.mockResolvedValue({ all: ['linkedin', 'twitter'], configured: ['linkedin'] });
    dist.listCredentials.mockResolvedValue([
      {
        id: 'cr1',
        platform: 'linkedin',
        client_id: 'c1',
        display_name: 'LinkedIn — Acme',
        is_active: true,
      },
    ]);
    dist.oauthStart.mockResolvedValue('https://oauth/authorize');
    clients.list.mockResolvedValue([
      { id: 'c1', name: 'Acme', businessDescription: '', createdAt: '2026-01-01T00:00:00Z' },
    ] as never);
  });

  it('starts OAuth scoped to the selected client', async () => {
    const { wrapper } = renderWithProviders();
    render(<Connections />, { wrapper });

    // Pick a client for the new connection.
    await waitFor(() => expect(screen.getByRole('option', { name: 'Acme' })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/connect a new account for/i), {
      target: { value: 'c1' },
    });

    // Click the (only enabled) Connect button — LinkedIn is configured.
    const connectBtns = screen.getAllByRole('button', { name: 'Connect' });
    const enabled = connectBtns.find((b) => !(b as HTMLButtonElement).disabled)!;
    fireEvent.click(enabled);

    await waitFor(() => expect(dist.oauthStart).toHaveBeenCalledWith('linkedin', 'c1'));
  });

  it('labels each existing credential with its client', async () => {
    const { wrapper } = renderWithProviders();
    render(<Connections />, { wrapper });

    // The connected LinkedIn credential is shown under its client "Acme".
    await waitFor(() => expect(screen.getByText('LinkedIn — Acme')).toBeInTheDocument());
    // "Acme" appears both as a client option and as the credential's client badge.
    expect(screen.getAllByText('Acme').length).toBeGreaterThan(1);
  });
});
