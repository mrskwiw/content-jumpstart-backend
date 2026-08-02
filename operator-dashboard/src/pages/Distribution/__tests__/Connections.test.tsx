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
      { id: 'c2', name: 'Globex', businessDescription: '', createdAt: '2026-01-01T00:00:00Z' },
    ] as never);
  });

  it('starts OAuth scoped to the selected client', async () => {
    const { wrapper } = renderWithProviders();
    render(<Connections />, { wrapper });

    // Pick Globex — which has NO existing LinkedIn credential, so Connect is available.
    await waitFor(() => expect(screen.getByRole('option', { name: 'Globex' })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/connect a new account for/i), {
      target: { value: 'c2' },
    });

    // Click the (only enabled) Connect button — LinkedIn is configured.
    const connectBtns = screen.getAllByRole('button', { name: 'Connect' });
    const enabled = connectBtns.find((b) => !(b as HTMLButtonElement).disabled)!;
    fireEvent.click(enabled);

    await waitFor(() => expect(dist.oauthStart).toHaveBeenCalledWith('linkedin', 'c2'));
  });

  it('does not start a fresh OAuth for an already-connected platform/client pair', async () => {
    const { wrapper } = renderWithProviders();
    render(<Connections />, { wrapper });

    // Select Acme — which already has a LinkedIn credential (cr1).
    await waitFor(() => expect(screen.getByRole('option', { name: 'Acme' })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/connect a new account for/i), {
      target: { value: 'c1' },
    });

    // The LinkedIn card now shows "Connected" and its button is disabled.
    await waitFor(() => {
      const connectedBtn = screen.getByRole('button', { name: 'Connected' });
      expect(connectedBtn).toBeDisabled();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Connected' }));
    expect(dist.oauthStart).not.toHaveBeenCalled();
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
