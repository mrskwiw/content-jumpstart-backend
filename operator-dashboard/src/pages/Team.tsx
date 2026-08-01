import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, UserPlus, Shield, Crown, Trash2, LogOut, FolderInput, X } from 'lucide-react';
import { toast } from 'sonner';
import { teamsApi } from '@/api/teams';
import { useAuth } from '@/contexts/AuthContext';
import type { TeamRole } from '@/types/team';

const ASSIGNABLE_ROLES: TeamRole[] = ['admin', 'editor', 'viewer'];
const TEAM_KEY = ['team', 'me'] as const;

function roleBadgeClass(role: TeamRole): string {
  switch (role) {
    case 'owner':
      return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300';
    case 'admin':
      return 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300';
    case 'editor':
      return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300';
    default:
      return 'bg-neutral-200 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300';
  }
}

function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : fallback;
}

export default function Team() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [newTeamName, setNewTeamName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  // Least privilege by default (matches the backend AddMemberRequest default); the
  // owner/admin must deliberately raise the role before inviting.
  const [inviteRole, setInviteRole] = useState<TeamRole>('viewer');

  const { data, isLoading, isError } = useQuery({
    queryKey: TEAM_KEY,
    queryFn: () => teamsApi.getMyTeam(),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: TEAM_KEY });
  const mutationOpts = (successMsg: string, failMsg: string) => ({
    onSuccess: () => {
      invalidate();
      toast.success(successMsg);
    },
    onError: (err: unknown) => toast.error(errorDetail(err, failMsg)),
  });

  const createTeam = useMutation({
    mutationFn: (name: string) => teamsApi.createTeam(name),
    ...mutationOpts('Team created', 'Failed to create team'),
  });
  const addMember = useMutation({
    mutationFn: (input: { email: string; role: TeamRole }) =>
      teamsApi.addMember(input.email, input.role),
    onSuccess: () => {
      invalidate();
      setInviteEmail('');
      toast.success('Member added');
    },
    onError: (err: unknown) => toast.error(errorDetail(err, 'Failed to add member')),
  });
  const changeRole = useMutation({
    mutationFn: (input: { userId: string; role: TeamRole }) =>
      teamsApi.changeRole(input.userId, input.role),
    ...mutationOpts('Role updated', 'Failed to update role'),
  });
  const removeMember = useMutation({
    mutationFn: (userId: string) => teamsApi.removeMember(userId),
    ...mutationOpts('Member removed', 'Failed to remove member'),
  });
  const transferOwnership = useMutation({
    mutationFn: (userId: string) => teamsApi.transferOwnership(userId),
    ...mutationOpts('Ownership transferred', 'Failed to transfer ownership'),
  });
  const deleteTeam = useMutation({
    mutationFn: () => teamsApi.deleteTeam(),
    ...mutationOpts('Team deleted', 'Failed to delete team'),
  });
  const adoptResources = useMutation({
    mutationFn: () => teamsApi.adoptResources(),
    onSuccess: (res) => {
      invalidate();
      toast.success(`Moved ${res.moved} item(s) into the team`);
    },
    onError: (err: unknown) => toast.error(errorDetail(err, 'Failed to move resources')),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-neutral-500">
        Loading team…
      </div>
    );
  }
  if (isError) {
    return <div className="p-6 text-red-600 dark:text-red-400">Failed to load team.</div>;
  }

  const team = data?.team ?? null;

  // ── Solo (no team): offer to create one ──────────────────────────────────────
  if (!team) {
    return (
      <div className="mx-auto max-w-xl p-6">
        <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center dark:border-neutral-700 dark:bg-neutral-900">
          <Users className="mx-auto mb-3 h-10 w-10 text-neutral-400" />
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            You're not on a team yet
          </h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Create a team to collaborate — your existing clients and projects move into it,
            and you can invite others.
          </p>
          <form
            className="mt-5 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (newTeamName.trim()) createTeam.mutate(newTeamName.trim());
            }}
          >
            <input
              type="text"
              value={newTeamName}
              onChange={(e) => setNewTeamName(e.target.value)}
              placeholder="Team name"
              className="flex-1 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
            />
            <button
              type="submit"
              disabled={createTeam.isPending || !newTeamName.trim()}
              className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              Create team
            </button>
          </form>
        </div>
      </div>
    );
  }

  const canManage = team.my_role === 'owner' || team.my_role === 'admin';
  const isOwner = team.my_role === 'owner';
  const otherMembers = team.members.filter((m) => m.role !== 'owner');

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
            {team.name}
          </h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            {team.members.length} member{team.members.length === 1 ? '' : 's'} · you are{' '}
            <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${roleBadgeClass(team.my_role)}`}>
              {team.my_role}
            </span>
          </p>
        </div>
        <button
          type="button"
          onClick={() => adoptResources.mutate()}
          disabled={adoptResources.isPending}
          className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-600 dark:text-neutral-200 dark:hover:bg-neutral-800"
          title="Move your own solo clients/projects into this team"
        >
          <FolderInput className="h-4 w-4" /> Bring my work in
        </button>
      </div>

      {/* Invite (owner/admin only) */}
      {canManage && (
        <form
          className="flex flex-wrap items-center gap-2 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900"
          onSubmit={(e) => {
            e.preventDefault();
            if (inviteEmail.trim())
              addMember.mutate({ email: inviteEmail.trim(), role: inviteRole });
          }}
        >
          <UserPlus className="h-4 w-4 text-neutral-400" />
          <input
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="teammate@example.com"
            className="flex-1 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as TeamRole)}
            className="rounded-md border border-neutral-300 bg-white px-2 py-2 text-sm text-neutral-900 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
          >
            {ASSIGNABLE_ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={addMember.isPending || !inviteEmail.trim()}
            className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            Invite
          </button>
        </form>
      )}

      {/* Members */}
      <div className="overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-700">
        <table className="w-full text-sm">
          <thead className="bg-neutral-50 text-left text-neutral-500 dark:bg-neutral-800/50 dark:text-neutral-400">
            <tr>
              <th className="px-4 py-2 font-medium">Member</th>
              <th className="px-4 py-2 font-medium">Role</th>
              <th className="px-4 py-2 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
            {team.members.map((m) => {
              const isSelf = m.user_id === user?.id;
              const canEditThis = canManage && m.role !== 'owner';
              return (
                <tr key={m.user_id} className="bg-white dark:bg-neutral-900">
                  <td className="px-4 py-3">
                    <div className="font-medium text-neutral-900 dark:text-neutral-100">
                      {m.full_name || m.email}
                      {isSelf && (
                        <span className="ml-1 text-xs text-neutral-400">(you)</span>
                      )}
                    </div>
                    <div className="text-xs text-neutral-500 dark:text-neutral-400">{m.email}</div>
                  </td>
                  <td className="px-4 py-3">
                    {canEditThis ? (
                      <select
                        value={m.role}
                        onChange={(e) => {
                          const role = e.target.value as TeamRole;
                          if (role === m.role) return;
                          if (
                            window.confirm(
                              `Change ${m.full_name || m.email}'s role to ${role}?`
                            )
                          )
                            changeRole.mutate({ userId: m.user_id, role });
                        }}
                        className="rounded-md border border-neutral-300 bg-white px-2 py-1 text-xs dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
                      >
                        {ASSIGNABLE_ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span
                        className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${roleBadgeClass(m.role)}`}
                      >
                        {m.role === 'owner' ? <Crown className="h-3 w-3" /> : <Shield className="h-3 w-3" />}
                        {m.role}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {isOwner && !isSelf && (
                        <button
                          type="button"
                          onClick={() => {
                            if (
                              window.confirm(
                                `Make ${m.full_name || m.email} the owner? You'll become an admin.`
                              )
                            )
                              transferOwnership.mutate(m.user_id);
                          }}
                          disabled={transferOwnership.isPending}
                          className="text-xs text-amber-700 hover:underline disabled:opacity-50 dark:text-amber-400"
                          title="Make this member the team owner"
                        >
                          Make owner
                        </button>
                      )}
                      {isSelf && m.role !== 'owner' && (
                        <button
                          type="button"
                          onClick={() => {
                            if (window.confirm('Leave this team?')) removeMember.mutate(m.user_id);
                          }}
                          disabled={removeMember.isPending}
                          className="inline-flex items-center gap-1 text-xs text-neutral-600 hover:underline disabled:opacity-50 dark:text-neutral-300"
                        >
                          <LogOut className="h-3.5 w-3.5" /> Leave
                        </button>
                      )}
                      {canManage && !isSelf && m.role !== 'owner' && (
                        <button
                          type="button"
                          onClick={() => {
                            if (window.confirm(`Remove ${m.full_name || m.email} from the team?`))
                              removeMember.mutate(m.user_id);
                          }}
                          disabled={removeMember.isPending}
                          className="inline-flex items-center gap-1 text-xs text-red-600 hover:underline disabled:opacity-50 dark:text-red-400"
                        >
                          <Trash2 className="h-3.5 w-3.5" /> Remove
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Danger zone — owner only */}
      {isOwner && (
        <div className="rounded-lg border border-red-200 bg-red-50/40 p-4 dark:border-red-900/40 dark:bg-red-950/20">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-sm font-medium text-red-800 dark:text-red-300">
                <X className="h-4 w-4" /> Delete team
              </div>
              <p className="text-xs text-red-700/80 dark:text-red-400/80">
                Disbands the team. Each member keeps the clients/projects they created.
                {otherMembers.length > 0 &&
                  ' Transfer ownership first if you only want to leave.'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                if (window.confirm('Delete this team? This cannot be undone.'))
                  deleteTeam.mutate();
              }}
              disabled={deleteTeam.isPending}
              className="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              Delete team
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
