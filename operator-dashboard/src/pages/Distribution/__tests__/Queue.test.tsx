import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Queue from '../Queue';
import { distributionApi } from '@/api/distribution';
import { clientsApi } from '@/api/clients';

jest.mock('@/api/distribution', () => ({
  distributionApi: {
    listCredentials: jest.fn(),
    queue: jest.fn(),
    schedule: jest.fn(),
    publishNow: jest.fn(),
  },
}));
jest.mock('@/api/clients', () => ({ clientsApi: { list: jest.fn() } }));

const dist = distributionApi as jest.Mocked<typeof distributionApi>;
const clients = clientsApi as jest.Mocked<typeof clientsApi>;

describe('Distribution Queue — per-client attribution', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    dist.listCredentials.mockResolvedValue([]);
    dist.queue.mockResolvedValue([]);
    dist.schedule.mockResolvedValue({
      id: 'sp1',
      platform: 'stub',
      content: 'hi',
      status: 'pending',
      scheduled_for: '2026-02-10T00:00:00Z',
      retry_count: 0,
    });
    clients.list.mockResolvedValue([
      { id: 'c1', name: 'Acme', businessDescription: '', createdAt: '2026-01-01T00:00:00Z' },
    ] as never);
  });

  it('offers a client selector and schedules with the chosen client_id', async () => {
    renderWithProviders(<Queue />);

    // The client option loads from clientsApi.
    await waitFor(() => expect(screen.getByRole('option', { name: 'Acme' })).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/what do you want to post/i), {
      target: { value: 'Launch post' },
    });
    // Select the client (the combobox whose current value is the empty "No client" option).
    const clientSelect = screen.getByDisplayValue(/no client/i);
    fireEvent.change(clientSelect, { target: { value: 'c1' } });

    fireEvent.click(screen.getByRole('button', { name: /add to queue/i }));

    await waitFor(() =>
      expect(dist.schedule).toHaveBeenCalledWith(
        expect.objectContaining({ content: 'Launch post', client_id: 'c1' })
      )
    );
  });

  it('omits client_id when no client is chosen (account-level)', async () => {
    renderWithProviders(<Queue />);

    fireEvent.change(screen.getByPlaceholderText(/what do you want to post/i), {
      target: { value: 'Account post' },
    });
    fireEvent.click(screen.getByRole('button', { name: /add to queue/i }));

    await waitFor(() => expect(dist.schedule).toHaveBeenCalled());
    expect(dist.schedule).toHaveBeenCalledWith(
      expect.objectContaining({ content: 'Account post', client_id: undefined })
    );
  });
});
