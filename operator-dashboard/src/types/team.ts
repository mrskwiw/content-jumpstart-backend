// Team collaboration types (COLLAB-01) — mirror the /api/teams backend contract.

export type TeamRole = 'owner' | 'admin' | 'editor' | 'viewer';

export interface TeamMemberInfo {
  user_id: string;
  email: string;
  full_name: string | null;
  role: TeamRole;
}

export interface TeamInfo {
  team_id: string;
  name: string;
  my_role: TeamRole;
  members: TeamMemberInfo[];
}

/** GET /api/teams/me — the caller's team, or `team: null` when they are solo. */
export interface MyTeamResponse {
  team: TeamInfo | null;
}
