/**
 * Team collaboration API client (COLLAB-01).
 */
import apiClient from './client';
import type { MyTeamResponse, TeamInfo, TeamRole } from '@/types/team';

export const teamsApi = {
  /** The caller's team (or `{ team: null }` if they're solo). */
  async getMyTeam(): Promise<MyTeamResponse> {
    const { data } = await apiClient.get<MyTeamResponse>('/api/teams/me');
    return data;
  },

  /** Create a team; the caller becomes its owner and their resources move into it. */
  async createTeam(name: string): Promise<TeamInfo> {
    const { data } = await apiClient.post<TeamInfo>('/api/teams', { name });
    return data;
  },

  /** Invite an existing user by email (owner/admin only). */
  async addMember(email: string, role: TeamRole): Promise<TeamInfo> {
    const { data } = await apiClient.post<TeamInfo>('/api/teams/members', { email, role });
    return data;
  },

  /** Change a member's role (owner/admin only). */
  async changeRole(userId: string, role: TeamRole): Promise<TeamInfo> {
    const { data } = await apiClient.patch<TeamInfo>(`/api/teams/members/${userId}`, { role });
    return data;
  },

  /** Remove a member, or leave the team yourself. */
  async removeMember(userId: string): Promise<void> {
    await apiClient.delete(`/api/teams/members/${userId}`);
  },

  /** Transfer ownership to another member (owner only). */
  async transferOwnership(userId: string): Promise<void> {
    await apiClient.post('/api/teams/transfer', { user_id: userId });
  },

  /** Disband the team (owner only) — resources revert to their creators. */
  async deleteTeam(): Promise<void> {
    await apiClient.delete('/api/teams');
  },

  /** Move the caller's own team-less resources into their team. */
  async adoptResources(): Promise<{ moved: number }> {
    const { data } = await apiClient.post<{ status: string; moved: number }>(
      '/api/teams/adopt-resources'
    );
    return data;
  },
};
