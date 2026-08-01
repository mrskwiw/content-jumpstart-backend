import { render, screen, waitFor } from '@testing-library/react';
import Team from '@/pages/Team';
import { teamsApi } from '@/api/teams';
import { renderWithProviders } from '@/test-utils';
import '@testing-library/jest-dom';

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'u-owner', email: 'owner@example.com' } }),
}));

jest.mock('@/api/teams', () => ({
  teamsApi: {
    getMyTeam: jest.fn().mockResolvedValue({
      team: {
        team_id: 't1',
        name: 'Acme Team',
        my_role: 'owner',
        members: [
          { user_id: 'u-owner', email: 'owner@example.com', full_name: 'Owner', role: 'owner' },
          { user_id: 'u-ed', email: 'editor@example.com', full_name: 'Ed', role: 'editor' },
        ],
      },
    }),
  },
}));

describe('Team page', () => {
  it('renders the team + members with owner management controls', async () => {
    const { wrapper } = renderWithProviders();
    render(<Team />, { wrapper });

    await waitFor(() => expect(screen.getByText('Acme Team')).toBeInTheDocument());
    expect(screen.getByText('editor@example.com')).toBeInTheDocument();
    // An owner sees the invite control and the delete-team danger zone.
    expect(screen.getByPlaceholderText('teammate@example.com')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete team' })).toBeInTheDocument();
  });

  it('offers to create a team when the user is solo', async () => {
    (teamsApi.getMyTeam as jest.Mock).mockResolvedValueOnce({ team: null });
    const { wrapper } = renderWithProviders();
    render(<Team />, { wrapper });

    await waitFor(() => expect(screen.getByText(/not on a team yet/i)).toBeInTheDocument());
    expect(screen.getByPlaceholderText('Team name')).toBeInTheDocument();
  });
});
