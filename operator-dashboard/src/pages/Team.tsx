import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users,
  UserPlus,
  Shield,
  Activity,
  Clock,
  CheckCircle,
  MoreVertical,
  Mail,
  Edit,
  Trash2,
  Search,
  Filter,
  Crown,
  Eye,
  X,
  AlertCircle,
} from 'lucide-react';

// User roles
type UserRole = 'admin' | 'editor' | 'viewer';

// Team member interface
interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
  status: 'active' | 'inactive' | 'invited';
  joinedAt: string;
  lastActive: string;
  projectsAssigned: number;
  postsGenerated: number;
  avgQuality: number;
  hoursThisMonth: number;
}

// Permission interface
interface Permission {
  id: string;
  name: string;
  description: string;
  roles: UserRole[];
}

// Activity log interface
interface ActivityLog {
  id: string;
  userId: string;
  userName: string;
  action: string;
  timestamp: string;
  details: string;
}

// Mock data
const mockTeamMembers: TeamMember[] = [
  {
    id: '1',
    name: 'Sarah Johnson',
    email: 'sarah@company.com',
    role: 'admin',
    status: 'active',
    joinedAt: '2024-01-15',
    lastActive: '2025-12-17T14:30:00',
    projectsAssigned: 12,
    postsGenerated: 360,
    avgQuality: 92,
    hoursThisMonth: 45,
  },
  {
    id: '2',
    name: 'Michael Chen',
    email: 'michael@company.com',
    role: 'editor',
    status: 'active',
    joinedAt: '2024-03-20',
    lastActive: '2025-12-17T10:15:00',
    projectsAssigned: 8,
    postsGenerated: 240,
    avgQuality: 88,
    hoursThisMonth: 38,
  },
  {
    id: '3',
    name: 'Emily Rodriguez',
    email: 'emily@company.com',
    role: 'editor',
    status: 'active',
    joinedAt: '2024-06-10',
    lastActive: '2025-12-16T16:45:00',
    projectsAssigned: 10,
    postsGenerated: 300,
    avgQuality: 90,
    hoursThisMonth: 42,
  },
  {
    id: '4',
    name: 'David Park',
    email: 'david@company.com',
    role: 'viewer',
    status: 'active',
    joinedAt: '2024-09-05',
    lastActive: '2025-12-15T09:20:00',
    projectsAssigned: 0,
    postsGenerated: 0,
    avgQuality: 0,
    hoursThisMonth: 12,
  },
  {
    id: '5',
    name: 'Jessica Williams',
    email: 'jessica@company.com',
    role: 'editor',
    status: 'invited',
    joinedAt: '2025-12-10',
    lastActive: '',
    projectsAssigned: 0,
    postsGenerated: 0,
    avgQuality: 0,
    hoursThisMonth: 0,
  },
];

const mockPermissions: Permission[] = [
  {
    id: '1',
    name: 'Create Projects',
    description: 'Can create new client projects',
    roles: ['admin', 'editor'],
  },
  {
    id: '2',
    name: 'Delete Projects',
    description: 'Can permanently delete projects',
    roles: ['admin'],
  },
  {
    id: '3',
    name: 'Generate Content',
    description: 'Can generate posts and content',
    roles: ['admin', 'editor'],
  },
  {
    id: '4',
    name: 'Manage Team',
    description: 'Can invite, edit, and remove team members',
    roles: ['admin'],
  },
  {
    id: '5',
    name: 'View Analytics',
    description: 'Can view dashboard analytics',
    roles: ['admin', 'editor', 'viewer'],
  },
  {
    id: '6',
    name: 'Edit Settings',
    description: 'Can modify system settings',
    roles: ['admin'],
  },
  {
    id: '7',
    name: 'Approve Content',
    description: 'Can approve content for delivery',
    roles: ['admin', 'editor'],
  },
  {
    id: '8',
    name: 'View Projects',
    description: 'Can view project details',
    roles: ['admin', 'editor', 'viewer'],
  },
];

const mockActivityLogs: ActivityLog[] = [
  {
    id: '1',
    userId: '1',
    userName: 'Sarah Johnson',
    action: 'Created Project',
    timestamp: '2025-12-17T14:30:00',
    details: 'Created project "Acme Corp Q1 Campaign"',
  },
  {
    id: '2',
    userId: '2',
    userName: 'Michael Chen',
    action: 'Generated Content',
    timestamp: '2025-12-17T10:15:00',
    details: 'Generated 30 posts for TechStart Inc',
  },
  {
    id: '3',
    userId: '3',
    userName: 'Emily Rodriguez',
    action: 'Approved Deliverable',
    timestamp: '2025-12-16T16:45:00',
    details: 'Approved deliverable for StartupXYZ',
  },
  {
    id: '4',
    userId: '1',
    userName: 'Sarah Johnson',
    action: 'Invited User',
    timestamp: '2025-12-16T09:20:00',
    details: 'Invited Jessica Williams as Editor',
  },
  {
    id: '5',
    userId: '2',
    userName: 'Michael Chen',
    action: 'Updated Project',
    timestamp: '2025-12-15T15:10:00',
    details: 'Updated brief for GrowthCo',
  },
];

export default function Team() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [selectedMember, setSelectedMember] = useState<TeamMember | null>(null);
  const [showMemberMenu, setShowMemberMenu] = useState<string | null>(null);

  // Mock queries
  const { data: teamMembers = mockTeamMembers } = useQuery({
    queryKey: ['team-members'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockTeamMembers;
    },
  });

  const { data: permissions = mockPermissions } = useQuery({
    queryKey: ['permissions'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
      return mockPermissions;
    },
  });

  const { data: activityLogs = mockActivityLogs } = useQuery({
    queryKey: ['activity-logs'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
      return mockActivityLogs;
    },
  });

  // Mutations
  const inviteMutation = useMutation({
    mutationFn: async (data: { email: string; role: UserRole }) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members'] });
      setShowInviteModal(false);
    },
  });

  const updateRoleMutation = useMutation({
    mutationFn: async (data: { memberId: string; role: UserRole }) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members'] });
    },
  });

  // Filter team members
  const filteredMembers = useMemo(() => {
    let filtered = teamMembers;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        m => m.name.toLowerCase().includes(query) || m.email.toLowerCase().includes(query)
      );
    }

    if (roleFilter) {
      filtered = filtered.filter(m => m.role === roleFilter);
    }

    if (statusFilter) {
      filtered = filtered.filter(m => m.status === statusFilter);
    }

    return filtered;
  }, [teamMembers, searchQuery, roleFilter, statusFilter]);

  // Calculate team stats
  const teamStats = useMemo(() => {
    const activeMembers = teamMembers.filter(m => m.status === 'active');
    const totalProjects = activeMembers.reduce((sum, m) => sum + m.projectsAssigned, 0);
    const totalPosts = activeMembers.reduce((sum, m) => sum + m.postsGenerated, 0);
    const avgQuality = activeMembers.length > 0
      ? Math.round(activeMembers.reduce((sum, m) => sum + m.avgQuality, 0) / activeMembers.length)
      : 0;
    const totalHours = activeMembers.reduce((sum, m) => sum + m.hoursThisMonth, 0);

    return {
      totalMembers: teamMembers.length,
      activeMembers: activeMembers.length,
      totalProjects,
      totalPosts,
      avgQuality,
      totalHours,
    };
  }, [teamMembers]);

  // Get role badge styling
  const getRoleBadge = (role: UserRole) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'editor':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'viewer':
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  // Get role icon
  const getRoleIcon = (role: UserRole) => {
    switch (role) {
      case 'admin':
        return Crown;
      case 'editor':
        return Edit;
      case 'viewer':
        return Eye;
    }
  };

  // Get status badge
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'inactive':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      case 'invited':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  // Format time ago
  const formatTimeAgo = (dateString: string) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Team Collaboration</h1>
          <p className="text-sm text-slate-600 mt-1">Manage team members, roles, and permissions</p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
        >
          <UserPlus className="h-4 w-4" />
          Invite Member
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Team Members</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{teamStats.totalMembers}</p>
              <p className="text-xs text-green-600 mt-1">{teamStats.activeMembers} active</p>
            </div>
            <div className="rounded-lg bg-blue-100 p-3">
              <Users className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Active Projects</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{teamStats.totalProjects}</p>
            </div>
            <div className="rounded-lg bg-purple-100 p-3">
              <Activity className="h-6 w-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Avg Quality</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{teamStats.avgQuality}%</p>
            </div>
            <div className="rounded-lg bg-green-100 p-3">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Hours This Month</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{teamStats.totalHours}</p>
            </div>
            <div className="rounded-lg bg-orange-100 p-3">
              <Clock className="h-6 w-6 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search team members..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-slate-300 pl-10 pr-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Role Filter */}
          <div className="sm:w-40">
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <select
                value={roleFilter}
                onChange={e => setRoleFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 pl-10 pr-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none"
              >
                <option value="">All Roles</option>
                <option value="admin">Admin</option>
                <option value="editor">Editor</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
          </div>

          {/* Status Filter */}
          <div className="sm:w-40">
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="invited">Invited</option>
            </select>
          </div>

          {(searchQuery || roleFilter || statusFilter) && (
            <button
              onClick={() => {
                setSearchQuery('');
                setRoleFilter('');
                setStatusFilter('');
              }}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium whitespace-nowrap"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Team Members Table */}
      <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Member
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Projects
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Posts
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Quality
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Last Active
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filteredMembers.map(member => {
                const RoleIcon = getRoleIcon(member.role);
                return (
                  <tr key={member.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold">
                          {member.name.split(' ').map(n => n[0]).join('')}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-900">{member.name}</p>
                          <p className="text-xs text-slate-600">{member.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium ${getRoleBadge(member.role)}`}>
                        <RoleIcon className="h-3 w-3" />
                        {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium ${getStatusBadge(member.status)}`}>
                        {member.status.charAt(0).toUpperCase() + member.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-slate-900">{member.projectsAssigned}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-slate-900">{member.postsGenerated}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-slate-900">
                        {member.avgQuality > 0 ? `${member.avgQuality}%` : '-'}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-slate-600">{formatTimeAgo(member.lastActive)}</p>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="relative inline-block">
                        <button
                          onClick={() => setShowMemberMenu(showMemberMenu === member.id ? null : member.id)}
                          className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>
                        {showMemberMenu === member.id && (
                          <div className="absolute right-0 mt-2 w-48 rounded-lg border border-slate-200 bg-white shadow-lg z-10">
                            <button
                              onClick={() => {
                                setSelectedMember(member);
                                setShowMemberMenu(null);
                              }}
                              className="flex items-center gap-2 w-full px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                            >
                              <Edit className="h-4 w-4" />
                              Edit Role
                            </button>
                            <button className="flex items-center gap-2 w-full px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                              <Mail className="h-4 w-4" />
                              Send Email
                            </button>
                            <button className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                              <Trash2 className="h-4 w-4" />
                              Remove
                            </button>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filteredMembers.length === 0 && (
          <div className="p-12 text-center">
            <Users className="h-12 w-12 text-slate-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No team members found</h3>
            <p className="text-sm text-slate-600">Try adjusting your filters</p>
          </div>
        )}
      </div>

      {/* Permissions Matrix */}
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Permissions Matrix
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Permission</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-700">Admin</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-700">Editor</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-700">Viewer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {permissions.map(permission => (
                <tr key={permission.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-slate-900">{permission.name}</p>
                    <p className="text-xs text-slate-600">{permission.description}</p>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {permission.roles.includes('admin') ? (
                      <CheckCircle className="h-5 w-5 text-green-600 mx-auto" />
                    ) : (
                      <X className="h-5 w-5 text-slate-300 mx-auto" />
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {permission.roles.includes('editor') ? (
                      <CheckCircle className="h-5 w-5 text-green-600 mx-auto" />
                    ) : (
                      <X className="h-5 w-5 text-slate-300 mx-auto" />
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {permission.roles.includes('viewer') ? (
                      <CheckCircle className="h-5 w-5 text-green-600 mx-auto" />
                    ) : (
                      <X className="h-5 w-5 text-slate-300 mx-auto" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Recent Team Activity
        </h2>
        <div className="space-y-3">
          {activityLogs.slice(0, 5).map(log => (
            <div key={log.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
                {log.userName.split(' ').map(n => n[0]).join('')}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-900">
                  <span className="font-medium">{log.userName}</span> · {log.action}
                </p>
                <p className="text-sm text-slate-600 mt-0.5">{log.details}</p>
                <p className="text-xs text-slate-500 mt-1">{formatTimeAgo(log.timestamp)}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Invite Member Modal */}
      {showInviteModal && (
        <InviteModal
          onClose={() => setShowInviteModal(false)}
          onSubmit={(data) => inviteMutation.mutate(data)}
          isSubmitting={inviteMutation.isPending}
        />
      )}

      {/* Edit Role Modal */}
      {selectedMember && (
        <EditRoleModal
          member={selectedMember}
          onClose={() => setSelectedMember(null)}
          onSubmit={(role) => {
            updateRoleMutation.mutate({ memberId: selectedMember.id, role });
            setSelectedMember(null);
          }}
          isSubmitting={updateRoleMutation.isPending}
        />
      )}
    </div>
  );
}

// Invite Modal Component
function InviteModal({
  onClose,
  onSubmit,
  isSubmitting,
}: {
  onClose: () => void;
  onSubmit: (data: { email: string; role: UserRole }) => void;
  isSubmitting: boolean;
}) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<UserRole>('editor');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Invite Team Member</h3>
            <p className="text-sm text-slate-600 mt-1">Send an invitation to join your team</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="colleague@company.com"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value as UserRole)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="viewer">Viewer - Read-only access</option>
              <option value="editor">Editor - Can create and edit content</option>
              <option value="admin">Admin - Full access including settings</option>
            </select>
          </div>

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-blue-700">
                An invitation email will be sent to this address with setup instructions.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            disabled={!email || isSubmitting}
            onClick={() => onSubmit({ email, role })}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            <Mail className="h-4 w-4" />
            {isSubmitting ? 'Sending...' : 'Send Invitation'}
          </button>
        </div>
      </div>
    </div>
  );
}

// Edit Role Modal Component
function EditRoleModal({
  member,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  member: TeamMember;
  onClose: () => void;
  onSubmit: (role: UserRole) => void;
  isSubmitting: boolean;
}) {
  const [role, setRole] = useState<UserRole>(member.role);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Edit Role</h3>
            <p className="text-sm text-slate-600 mt-1">Change role for {member.name}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value as UserRole)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="viewer">Viewer - Read-only access</option>
              <option value="editor">Editor - Can create and edit content</option>
              <option value="admin">Admin - Full access including settings</option>
            </select>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            disabled={role === member.role || isSubmitting}
            onClick={() => onSubmit(role)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
