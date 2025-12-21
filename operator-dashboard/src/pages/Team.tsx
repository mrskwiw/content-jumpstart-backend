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
        return 'bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-700';
      case 'editor':
        return 'bg-primary-100 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 border-primary-200 dark:border-primary-700';
      case 'viewer':
        return 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700';
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
        return 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-700';
      case 'inactive':
        return 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700';
      case 'invited':
        return 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-700';
      default:
        return 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700';
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
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Team Collaboration</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Manage team members, roles, and permissions</p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600"
        >
          <UserPlus className="h-4 w-4" />
          Invite Member
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Team Members</p>
              <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mt-1">{teamStats.totalMembers}</p>
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">{teamStats.activeMembers} active</p>
            </div>
            <div className="rounded-lg bg-primary-100 dark:bg-primary-900/20 p-3">
              <Users className="h-6 w-6 text-primary-600 dark:text-primary-400" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Active Projects</p>
              <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mt-1">{teamStats.totalProjects}</p>
            </div>
            <div className="rounded-lg bg-purple-100 dark:bg-purple-900/20 p-3">
              <Activity className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Avg Quality</p>
              <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mt-1">{teamStats.avgQuality}%</p>
            </div>
            <div className="rounded-lg bg-emerald-100 dark:bg-emerald-900/20 p-3">
              <CheckCircle className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Hours This Month</p>
              <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mt-1">{teamStats.totalHours}</p>
            </div>
            <div className="rounded-lg bg-orange-100 dark:bg-orange-900/20 p-3">
              <Clock className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400 dark:text-neutral-500" />
              <input
                type="text"
                placeholder="Search team members..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 pl-10 pr-4 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
              />
            </div>
          </div>

          {/* Role Filter */}
          <div className="sm:w-40">
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400 dark:text-neutral-500" />
              <select
                value={roleFilter}
                onChange={e => setRoleFilter(e.target.value)}
                className="w-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 pl-10 pr-4 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400 appearance-none"
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
              className="w-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-4 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400 appearance-none"
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
              className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium whitespace-nowrap"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Team Members Table */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Member
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Projects
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Posts
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Quality
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Last Active
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
              {filteredMembers.map(member => {
                const RoleIcon = getRoleIcon(member.role);
                return (
                  <tr key={member.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center text-white font-semibold">
                          {member.name.split(' ').map(n => n[0]).join('')}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{member.name}</p>
                          <p className="text-xs text-neutral-600 dark:text-neutral-400">{member.email}</p>
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
                      <p className="text-sm text-neutral-900 dark:text-neutral-100">{member.projectsAssigned}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-neutral-900 dark:text-neutral-100">{member.postsGenerated}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                        {member.avgQuality > 0 ? `${member.avgQuality}%` : '-'}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-neutral-600 dark:text-neutral-400">{formatTimeAgo(member.lastActive)}</p>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="relative inline-block">
                        <button
                          onClick={() => setShowMemberMenu(showMemberMenu === member.id ? null : member.id)}
                          className="rounded-lg p-2 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>
                        {showMemberMenu === member.id && (
                          <div className="absolute right-0 mt-2 w-48 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-lg z-10">
                            <button
                              onClick={() => {
                                setSelectedMember(member);
                                setShowMemberMenu(null);
                              }}
                              className="flex items-center gap-2 w-full px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
                            >
                              <Edit className="h-4 w-4" />
                              Edit Role
                            </button>
                            <button className="flex items-center gap-2 w-full px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
                              <Mail className="h-4 w-4" />
                              Send Email
                            </button>
                            <button className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20">
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
            <Users className="h-12 w-12 text-neutral-400 dark:text-neutral-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">No team members found</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Try adjusting your filters</p>
          </div>
        )}
      </div>

      {/* Permissions Matrix */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4 flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Permissions Matrix
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-neutral-200 dark:border-neutral-700">
                <th className="px-4 py-3 text-left text-sm font-medium text-neutral-700 dark:text-neutral-300">Permission</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-neutral-700 dark:text-neutral-300">Admin</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-neutral-700 dark:text-neutral-300">Editor</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-neutral-700 dark:text-neutral-300">Viewer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
              {permissions.map(permission => (
                <tr key={permission.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{permission.name}</p>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400">{permission.description}</p>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {permission.roles.includes('admin') ? (
                      <CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400 mx-auto" />
                    ) : (
                      <X className="h-5 w-5 text-neutral-300 dark:text-neutral-700 mx-auto" />
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {permission.roles.includes('editor') ? (
                      <CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400 mx-auto" />
                    ) : (
                      <X className="h-5 w-5 text-neutral-300 dark:text-neutral-700 mx-auto" />
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {permission.roles.includes('viewer') ? (
                      <CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400 mx-auto" />
                    ) : (
                      <X className="h-5 w-5 text-neutral-300 dark:text-neutral-700 mx-auto" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Recent Team Activity
        </h2>
        <div className="space-y-3">
          {activityLogs.slice(0, 5).map(log => (
            <div key={log.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
                {log.userName.split(' ').map(n => n[0]).join('')}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-neutral-900 dark:text-neutral-100">
                  <span className="font-medium">{log.userName}</span> · {log.action}
                </p>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-0.5">{log.details}</p>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">{formatTimeAgo(log.timestamp)}</p>
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-neutral-950/60 px-4">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Invite Team Member</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Send an invitation to join your team</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="colleague@company.com"
              className="w-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value as UserRole)}
              className="w-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
            >
              <option value="viewer">Viewer - Read-only access</option>
              <option value="editor">Editor - Can create and edit content</option>
              <option value="admin">Admin - Full access including settings</option>
            </select>
          </div>

          <div className="rounded-lg border border-primary-200 dark:border-primary-700 bg-primary-50 dark:bg-primary-900/20 p-3">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-primary-700 dark:text-primary-300">
                An invitation email will be sent to this address with setup instructions.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
          >
            Cancel
          </button>
          <button
            disabled={!email || isSubmitting}
            onClick={() => onSubmit({ email, role })}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50"
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-neutral-950/60 px-4">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Edit Role</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Change role for {member.name}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value as UserRole)}
              className="w-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
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
            className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
          >
            Cancel
          </button>
          <button
            disabled={role === member.role || isSubmitting}
            onClick={() => onSubmit(role)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50"
          >
            {isSubmitting ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
