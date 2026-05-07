/**
 * UsersTab - Admin-only user management tab for Settings page
 *
 * Provides functionality to:
 * - View all system users with stats
 * - Create new users
 * - Activate/deactivate users
 * - Promote/demote admin privileges
 */
import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { usersApi } from '@/api/users';
import type { SystemUser, CreateUserRequest } from '@/types/user';
import {
  Users,
  UserPlus,
  Shield,
  ShieldOff,
  CheckCircle,
  XCircle,
  Search,
  MoreVertical,
  X,
  AlertCircle,
  UserX,
  UserCheck,
  Key,
} from 'lucide-react';

// Stats Card Component
function StatsCard({
  label,
  value,
  icon: Icon,
  colorClass,
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  colorClass: string;
}) {
  return (
    <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${colorClass}`}>{value}</p>
        </div>
        <div className={`rounded-lg p-3 ${colorClass.replace('text-', 'bg-').replace('-600', '-100').replace('-400', '-900/20')}`}>
          <Icon className={`h-6 w-6 ${colorClass}`} />
        </div>
      </div>
    </div>
  );
}

// Add User Modal
function AddUserModal({
  onClose,
  onSubmit,
  isSubmitting,
}: {
  onClose: () => void;
  onSubmit: (data: CreateUserRequest) => void;
  isSubmitting: boolean;
}) {
  const [formData, setFormData] = useState({
    email: '',
    fullName: '',
    password: '',
    isSuperuser: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.email) newErrors.email = 'Email is required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) newErrors.email = 'Invalid email';
    if (!formData.fullName) newErrors.fullName = 'Name is required';
    else if (formData.fullName.length < 2) newErrors.fullName = 'Name too short';
    // pragma: allowlist nextline secret
    if (!formData.password) newErrors.password = 'Password is required';  // pragma: allowlist secret
    else if (formData.password.length < 8) newErrors.password = 'Min 8 characters';  // pragma: allowlist secret
    else if (!/[A-Z]/.test(formData.password)) newErrors.password = 'Need uppercase letter';  // pragma: allowlist secret
    else if (!/[a-z]/.test(formData.password)) newErrors.password = 'Need lowercase letter';  // pragma: allowlist secret
    else if (!/[0-9]/.test(formData.password)) newErrors.password = 'Need digit';  // pragma: allowlist secret

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateForm()) {
      onSubmit(formData);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Add New User</h2>
          <button
            aria-label="Close dialog"
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Email
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="user@example.com"
              className={`w-full px-3 py-2 rounded-md border ${
                errors.email
                  ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
                  : 'border-neutral-300 dark:border-neutral-600 focus:border-primary-500 focus:ring-primary-500'
              } bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100`}
            />
            {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Full Name
            </label>
            <input
              type="text"
              value={formData.fullName}
              onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
              placeholder="John Doe"
              className={`w-full px-3 py-2 rounded-md border ${
                errors.fullName
                  ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
                  : 'border-neutral-300 dark:border-neutral-600 focus:border-primary-500 focus:ring-primary-500'
              } bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100`}
            />
            {errors.fullName && <p className="text-xs text-red-500 mt-1">{errors.fullName}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Password
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="Min 8 chars, upper, lower, digit"
              className={`w-full px-3 py-2 rounded-md border ${
                errors.password
                  ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
                  : 'border-neutral-300 dark:border-neutral-600 focus:border-primary-500 focus:ring-primary-500'
              } bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100`}
            />
            {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password}</p>}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="isSuperuser"
              checked={formData.isSuperuser}
              onChange={(e) => setFormData({ ...formData, isSuperuser: e.target.checked })}
              className="h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
            />
            <label htmlFor="isSuperuser" className="text-sm text-neutral-700 dark:text-neutral-300">
              Grant admin privileges
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-md"
            >
              {isSubmitting ? 'Creating...' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// User Actions Menu
function UserActionsMenu({
  user,
  isCurrentUser,
  onActivate,
  onDeactivate,
  onPromote,
  onDemote,
  onResetPassword,
}: {
  user: SystemUser;
  isCurrentUser: boolean;
  onActivate: (userId: string) => void;
  onDeactivate: (userId: string) => void;
  onPromote: (userId: string) => void;
  onDemote: (userId: string) => void;
  onResetPassword: (user: SystemUser) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        aria-label="User actions menu"
        onClick={() => setOpen(!open)}
        className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded"
      >
        <MoreVertical className="h-4 w-4 text-neutral-500" />
      </button>

      {open && (
        <>
          {/* Backdrop to close menu */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />

          <div className="absolute right-0 mt-1 w-48 rounded-md border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-lg z-20">
            {/* Activate/Deactivate */}
            {user.isActive ? (
              <button
                className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                onClick={() => {
                  onDeactivate(user.id);
                  setOpen(false);
                }}
                disabled={isCurrentUser}
              >
                <UserX className="h-4 w-4" />
                Deactivate
              </button>
            ) : (
              <button
                className="w-full px-4 py-2 text-left text-sm text-emerald-600 dark:text-emerald-400 hover:bg-neutral-50 dark:hover:bg-neutral-800 flex items-center gap-2"
                onClick={() => {
                  onActivate(user.id);
                  setOpen(false);
                }}
              >
                <UserCheck className="h-4 w-4" />
                Activate
              </button>
            )}

            <div className="border-t border-neutral-200 dark:border-neutral-700" />

            {/* Promote/Demote */}
            {user.isSuperuser ? (
              <button
                className="w-full px-4 py-2 text-left text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                onClick={() => {
                  onDemote(user.id);
                  setOpen(false);
                }}
                disabled={isCurrentUser}
              >
                <ShieldOff className="h-4 w-4" />
                Remove Admin
              </button>
            ) : (
              <button
                className="w-full px-4 py-2 text-left text-sm text-amber-600 dark:text-amber-400 hover:bg-neutral-50 dark:hover:bg-neutral-800 flex items-center gap-2"
                onClick={() => {
                  onPromote(user.id);
                  setOpen(false);
                }}
              >
                <Shield className="h-4 w-4" />
                Make Admin
              </button>
            )}

            <div className="border-t border-neutral-200 dark:border-neutral-700" />

            {/* Reset Password */}
            <button
              className="w-full px-4 py-2 text-left text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 flex items-center gap-2"
              onClick={() => {
                onResetPassword(user);
                setOpen(false);
              }}
            >
              <Key className="h-4 w-4" />
              Reset Password
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// Main UsersTab Component
export default function UsersTab() {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'user'>('all');
  const [showPasswordResetModal, setShowPasswordResetModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<SystemUser | null>(null);
  const [newPassword, setNewPassword] = useState('');

  // Queries
  const { data: users = [], isLoading: usersLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => usersApi.list(),
  });

  const { data: stats } = useQuery({
    queryKey: ['admin-users-stats'],
    queryFn: () => usersApi.getStats(),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: CreateUserRequest) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      queryClient.invalidateQueries({ queryKey: ['admin-users-stats'] });
      setShowAddModal(false);
    },
  });

  const activateMutation = useMutation({
    mutationFn: (userId: string) => usersApi.activate(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      queryClient.invalidateQueries({ queryKey: ['admin-users-stats'] });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (userId: string) => usersApi.deactivate(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      queryClient.invalidateQueries({ queryKey: ['admin-users-stats'] });
    },
  });

  const promoteMutation = useMutation({
    mutationFn: (userId: string) => usersApi.promote(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      queryClient.invalidateQueries({ queryKey: ['admin-users-stats'] });
    },
  });

  const demoteMutation = useMutation({
    mutationFn: (userId: string) => usersApi.demote(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      queryClient.invalidateQueries({ queryKey: ['admin-users-stats'] });
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: ({ userId, password }: { userId: string; password: string }) =>
      usersApi.resetPassword(userId, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setShowPasswordResetModal(false);
      setNewPassword('');
      setSelectedUser(null);
    },
  });

  // Filtered users
  const filteredUsers = useMemo(() => {
    let filtered = users;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (u) =>
          u.email.toLowerCase().includes(query) ||
          u.fullName?.toLowerCase().includes(query)
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter((u) =>
        statusFilter === 'active' ? u.isActive : !u.isActive
      );
    }

    // Role filter
    if (roleFilter !== 'all') {
      filtered = filtered.filter((u) =>
        roleFilter === 'admin' ? u.isSuperuser : !u.isSuperuser
      );
    }

    return filtered;
  }, [users, searchQuery, statusFilter, roleFilter]);

  if (usersLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            User Management
          </h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            Manage operator accounts and permissions
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md"
        >
          <UserPlus className="h-4 w-4" />
          Add User
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatsCard
            label="Total Users"
            value={stats.total}
            icon={Users}
            colorClass="text-primary-600 dark:text-primary-400"
          />
          <StatsCard
            label="Active"
            value={stats.active}
            icon={CheckCircle}
            colorClass="text-emerald-600 dark:text-emerald-400"
          />
          <StatsCard
            label="Admins"
            value={stats.admins}
            icon={Shield}
            colorClass="text-amber-600 dark:text-amber-400"
          />
          <StatsCard
            label="Inactive"
            value={stats.inactive}
            icon={XCircle}
            colorClass="text-neutral-500 dark:text-neutral-400"
          />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search by email or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 focus:border-primary-500 focus:ring-primary-500"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as 'all' | 'active' | 'inactive')}
          className="px-3 py-2 rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>

        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value as 'all' | 'admin' | 'user')}
          className="px-3 py-2 rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100"
        >
          <option value="all">All Roles</option>
          <option value="admin">Admins</option>
          <option value="user">Users</option>
        </select>

        {(searchQuery || statusFilter !== 'all' || roleFilter !== 'all') && (
          <button
            onClick={() => {
              setSearchQuery('');
              setStatusFilter('all');
              setRoleFilter('all');
            }}
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Users Table */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 overflow-hidden">
        <table className="w-full">
          <thead className="bg-neutral-50 dark:bg-neutral-800">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                User
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Role
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center">
                  <AlertCircle className="h-8 w-8 text-neutral-400 mx-auto mb-2" />
                  <p className="text-neutral-600 dark:text-neutral-400">No users found</p>
                </td>
              </tr>
            ) : (
              filteredUsers.map((user) => {
                const isCurrentUser = user.id === currentUser?.id;
                return (
                  <tr key={user.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                          <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                            {user.fullName?.charAt(0) || user.email.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-neutral-900 dark:text-neutral-100">
                            {user.email}
                          </p>
                          {isCurrentUser && (
                            <span className="text-xs text-primary-600 dark:text-primary-400">
                              (You)
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">
                      {user.fullName || '—'}
                    </td>
                    <td className="px-4 py-3">
                      {user.isSuperuser ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400">
                          <Shield className="h-3 w-3" />
                          Admin
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400">
                          User
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {user.isActive ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400">
                          <CheckCircle className="h-3 w-3" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400">
                          <XCircle className="h-3 w-3" />
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <UserActionsMenu
                        user={user}
                        isCurrentUser={isCurrentUser}
                        onActivate={(id) => activateMutation.mutate(id)}
                        onDeactivate={(id) => deactivateMutation.mutate(id)}
                        onPromote={(id) => promoteMutation.mutate(id)}
                        onDemote={(id) => demoteMutation.mutate(id)}
                        onResetPassword={(u) => {
                          setSelectedUser(u);
                          setShowPasswordResetModal(true);
                        }}
                      />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Showing {filteredUsers.length} of {users.length} users
          </p>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <AddUserModal
          onClose={() => setShowAddModal(false)}
          onSubmit={(data) => createMutation.mutate(data)}
          isSubmitting={createMutation.isPending}
        />
      )}

      {/* Password Reset Modal */}
      {showPasswordResetModal && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60">
          <div className="w-full max-w-md rounded-lg bg-white dark:bg-neutral-900 p-6 shadow-xl border border-neutral-200 dark:border-neutral-700">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                Reset Password
              </h3>
              <button
                aria-label="Close password reset dialog"
                onClick={() => {
                  setShowPasswordResetModal(false);
                  setNewPassword('');
                  setSelectedUser(null);
                }}
                className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded"
              >
                <X className="h-5 w-5 text-neutral-500" />
              </button>
            </div>

            <p className="mb-4 text-sm text-neutral-600 dark:text-neutral-400">
              Reset password for <strong className="text-neutral-900 dark:text-neutral-100">{selectedUser.email}</strong>
            </p>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-1 text-neutral-700 dark:text-neutral-300">
                New Password
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="Enter new password"
              />
              {newPassword && newPassword.length < 8 && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                  Password must be at least 8 characters
                </p>
              )}
              <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                Must include uppercase, lowercase, and digit
              </p>
            </div>

            {resetPasswordMutation.isError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                <p className="text-sm text-red-600 dark:text-red-400">
                  Failed to reset password. Please try again.
                </p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowPasswordResetModal(false);
                  setNewPassword('');
                  setSelectedUser(null);
                }}
                className="flex-1 px-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (selectedUser && newPassword && newPassword.length >= 8) {
                    resetPasswordMutation.mutate({
                      userId: selectedUser.id,
                      password: newPassword,
                    });
                  }
                }}
                disabled={!newPassword || newPassword.length < 8 || resetPasswordMutation.isPending}
                className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {resetPasswordMutation.isPending ? 'Resetting...' : 'Reset Password'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
