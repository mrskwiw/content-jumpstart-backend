import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FileText,
  Download,
  Filter,
  Search,
  User,
  Settings,
  FileEdit,
  Trash2,
  Upload,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  Shield,
  Clock,
  Calendar,
} from 'lucide-react';

// Types
interface AuditLog {
  id: string;
  timestamp: string;
  user: {
    id: string;
    name: string;
    email: string;
    role: string;
  };
  action: string;
  actionType: 'create' | 'read' | 'update' | 'delete' | 'export' | 'system' | 'security';
  resource: string;
  resourceType: 'project' | 'deliverable' | 'user' | 'settings' | 'template' | 'client';
  details: string;
  ipAddress: string;
  status: 'success' | 'failed' | 'warning';
  metadata?: {
    changes?: Record<string, { old: any; new: any }>;
    reason?: string;
    [key: string]: any;
  };
}

interface ComplianceStats {
  totalEvents: number;
  todayEvents: number;
  failedActions: number;
  securityEvents: number;
  avgEventsPerDay: number;
  retentionDays: number;
}

// Mock data
const mockAuditLogs: AuditLog[] = [
  {
    id: 'log-001',
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    user: {
      id: 'user-001',
      name: 'Sarah Johnson',
      email: 'sarah.j@company.com',
      role: 'Admin',
    },
    action: 'Updated deliverable status',
    actionType: 'update',
    resource: 'Deliverable #D-2024-003',
    resourceType: 'deliverable',
    details: 'Changed status from "Ready" to "Delivered"',
    ipAddress: '192.168.1.100',
    status: 'success',
    metadata: {
      changes: {
        status: { old: 'ready', new: 'delivered' },
      },
    },
  },
  {
    id: 'log-002',
    timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    user: {
      id: 'user-002',
      name: 'Michael Chen',
      email: 'michael.c@company.com',
      role: 'Editor',
    },
    action: 'Exported client data',
    actionType: 'export',
    resource: 'Client: Acme Corp',
    resourceType: 'client',
    details: 'Exported deliverables list as CSV',
    ipAddress: '192.168.1.105',
    status: 'success',
    metadata: {
      exportFormat: 'csv',
      recordCount: 30,
    },
  },
  {
    id: 'log-003',
    timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    user: {
      id: 'user-003',
      name: 'Emily Rodriguez',
      email: 'emily.r@company.com',
      role: 'Viewer',
    },
    action: 'Failed to delete project',
    actionType: 'delete',
    resource: 'Project #P-2024-015',
    resourceType: 'project',
    details: 'Insufficient permissions to delete project',
    ipAddress: '192.168.1.110',
    status: 'failed',
    metadata: {
      reason: 'Permission denied: Viewer role cannot delete projects',
    },
  },
  {
    id: 'log-004',
    timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    user: {
      id: 'user-001',
      name: 'Sarah Johnson',
      email: 'sarah.j@company.com',
      role: 'Admin',
    },
    action: 'Created new user',
    actionType: 'create',
    resource: 'User: Alex Thompson',
    resourceType: 'user',
    details: 'Added new team member with Editor role',
    ipAddress: '192.168.1.100',
    status: 'success',
    metadata: {
      newUser: {
        email: 'alex.t@company.com',
        role: 'editor',
      },
    },
  },
  {
    id: 'log-005',
    timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    user: {
      id: 'system',
      name: 'System',
      email: 'system@company.com',
      role: 'System',
    },
    action: 'Automated backup completed',
    actionType: 'system',
    resource: 'Database backup',
    resourceType: 'settings',
    details: 'Daily backup completed successfully',
    ipAddress: '127.0.0.1',
    status: 'success',
    metadata: {
      backupSize: '2.4 GB',
      duration: '3m 42s',
    },
  },
  {
    id: 'log-006',
    timestamp: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
    user: {
      id: 'user-004',
      name: 'David Kim',
      email: 'david.k@company.com',
      role: 'Admin',
    },
    action: 'Updated security settings',
    actionType: 'security',
    resource: 'Security Configuration',
    resourceType: 'settings',
    details: 'Enabled two-factor authentication requirement',
    ipAddress: '192.168.1.115',
    status: 'success',
    metadata: {
      changes: {
        requireTwoFactor: { old: false, new: true },
      },
    },
  },
  {
    id: 'log-007',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    user: {
      id: 'user-002',
      name: 'Michael Chen',
      email: 'michael.c@company.com',
      role: 'Editor',
    },
    action: 'Multiple login failures',
    actionType: 'security',
    resource: 'Authentication System',
    resourceType: 'settings',
    details: '3 failed login attempts detected',
    ipAddress: '192.168.1.105',
    status: 'warning',
    metadata: {
      attempts: 3,
      reason: 'Incorrect password',
    },
  },
  {
    id: 'log-008',
    timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    user: {
      id: 'user-001',
      name: 'Sarah Johnson',
      email: 'sarah.j@company.com',
      role: 'Admin',
    },
    action: 'Generated analytics report',
    actionType: 'create',
    resource: 'Monthly Performance Report',
    resourceType: 'project',
    details: 'Created monthly performance report for November 2024',
    ipAddress: '192.168.1.100',
    status: 'success',
    metadata: {
      reportType: 'monthly',
      period: '2024-11',
      metrics: ['quality', 'throughput', 'revenue'],
    },
  },
  {
    id: 'log-009',
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    user: {
      id: 'user-003',
      name: 'Emily Rodriguez',
      email: 'emily.r@company.com',
      role: 'Viewer',
    },
    action: 'Viewed client details',
    actionType: 'read',
    resource: 'Client: TechStart Inc',
    resourceType: 'client',
    details: 'Accessed client profile and project history',
    ipAddress: '192.168.1.110',
    status: 'success',
  },
  {
    id: 'log-010',
    timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    user: {
      id: 'user-002',
      name: 'Michael Chen',
      email: 'michael.c@company.com',
      role: 'Editor',
    },
    action: 'Updated template library',
    actionType: 'update',
    resource: 'Template: Problem Recognition',
    resourceType: 'template',
    details: 'Updated template structure and guidelines',
    ipAddress: '192.168.1.105',
    status: 'success',
    metadata: {
      changes: {
        guidelines: { old: 'Brief guidelines', new: 'Detailed step-by-step guidelines' },
      },
    },
  },
  {
    id: 'log-011',
    timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    user: {
      id: 'system',
      name: 'System',
      email: 'system@company.com',
      role: 'System',
    },
    action: 'Data retention policy executed',
    actionType: 'system',
    resource: 'Old audit logs',
    resourceType: 'settings',
    details: 'Archived logs older than 90 days',
    ipAddress: '127.0.0.1',
    status: 'success',
    metadata: {
      archivedCount: 1245,
      retentionDays: 90,
    },
  },
  {
    id: 'log-012',
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    user: {
      id: 'user-004',
      name: 'David Kim',
      email: 'david.k@company.com',
      role: 'Admin',
    },
    action: 'Deleted inactive user',
    actionType: 'delete',
    resource: 'User: John Smith',
    resourceType: 'user',
    details: 'Removed user account after 90 days of inactivity',
    ipAddress: '192.168.1.115',
    status: 'success',
    metadata: {
      reason: 'Inactive for 90+ days',
      lastActive: '2024-08-15',
    },
  },
];

const mockComplianceStats: ComplianceStats = {
  totalEvents: 8456,
  todayEvents: 127,
  failedActions: 23,
  securityEvents: 8,
  avgEventsPerDay: 142,
  retentionDays: 90,
};

// Helper functions
const getActionTypeIcon = (type: string) => {
  switch (type) {
    case 'create':
      return FileEdit;
    case 'read':
      return FileText;
    case 'update':
      return Settings;
    case 'delete':
      return Trash2;
    case 'export':
      return Download;
    case 'system':
      return Info;
    case 'security':
      return Shield;
    default:
      return FileText;
  }
};

const getActionTypeColor = (type: string) => {
  switch (type) {
    case 'create':
      return 'text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/20';
    case 'read':
      return 'text-primary-600 dark:text-primary-400 bg-primary-100 dark:bg-primary-900/20';
    case 'update':
      return 'text-orange-600 dark:text-orange-400 bg-orange-100 dark:bg-orange-900/20';
    case 'delete':
      return 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/20';
    case 'export':
      return 'text-purple-600 dark:text-purple-400 bg-purple-100 dark:bg-purple-900/20';
    case 'system':
      return 'text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800';
    case 'security':
      return 'text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/20';
    default:
      return 'text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'success':
      return CheckCircle;
    case 'failed':
      return XCircle;
    case 'warning':
      return AlertTriangle;
    default:
      return Info;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'success':
      return 'text-emerald-600 dark:text-emerald-400';
    case 'failed':
      return 'text-red-600 dark:text-red-400';
    case 'warning':
      return 'text-amber-600 dark:text-amber-400';
    default:
      return 'text-neutral-600 dark:text-neutral-400';
  }
};

const formatTimeAgo = (timestamp: string) => {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  return `${diffDays}d ago`;
};

const formatDateTime = (timestamp: string) => {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

export default function AuditTrail() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedActionType, setSelectedActionType] = useState<string>('all');
  const [selectedResourceType, setSelectedResourceType] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedUser, setSelectedUser] = useState<string>('all');
  const [dateRange, setDateRange] = useState<string>('all');
  const [showExportModal, setShowExportModal] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  // Fetch audit logs
  const { data: auditLogs = [] } = useQuery<AuditLog[]>({
    queryKey: ['audit-logs'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockAuditLogs;
    },
  });

  // Fetch compliance stats
  const { data: complianceStats } = useQuery<ComplianceStats>({
    queryKey: ['compliance-stats'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockComplianceStats;
    },
  });

  // Filter logs
  const filteredLogs = useMemo(() => {
    let filtered = [...auditLogs];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        log =>
          log.action.toLowerCase().includes(query) ||
          log.resource.toLowerCase().includes(query) ||
          log.details.toLowerCase().includes(query) ||
          log.user.name.toLowerCase().includes(query) ||
          log.user.email.toLowerCase().includes(query)
      );
    }

    // Action type filter
    if (selectedActionType !== 'all') {
      filtered = filtered.filter(log => log.actionType === selectedActionType);
    }

    // Resource type filter
    if (selectedResourceType !== 'all') {
      filtered = filtered.filter(log => log.resourceType === selectedResourceType);
    }

    // Status filter
    if (selectedStatus !== 'all') {
      filtered = filtered.filter(log => log.status === selectedStatus);
    }

    // User filter
    if (selectedUser !== 'all') {
      filtered = filtered.filter(log => log.user.id === selectedUser);
    }

    // Date range filter
    if (dateRange !== 'all') {
      const now = new Date();
      const ranges: Record<string, number> = {
        today: 1,
        week: 7,
        month: 30,
        quarter: 90,
      };
      const days = ranges[dateRange];
      if (days) {
        const cutoff = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
        filtered = filtered.filter(log => new Date(log.timestamp) >= cutoff);
      }
    }

    return filtered;
  }, [auditLogs, searchQuery, selectedActionType, selectedResourceType, selectedStatus, selectedUser, dateRange]);

  // Get unique users
  const uniqueUsers = useMemo(() => {
    const users = new Map();
    auditLogs.forEach(log => {
      if (!users.has(log.user.id)) {
        users.set(log.user.id, log.user);
      }
    });
    return Array.from(users.values());
  }, [auditLogs]);

  const handleExport = (format: 'csv' | 'json') => {
    console.log(`Exporting ${filteredLogs.length} logs as ${format.toUpperCase()}`);
    setShowExportModal(false);
  };

  if (!complianceStats) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 dark:border-primary-500 border-r-transparent"></div>
          <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">Loading audit trail...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Audit Trail</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Compliance logging and activity monitoring</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-6">
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Total Events</p>
            <FileText className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
          </div>
          <p className="mt-2 text-3xl font-bold text-neutral-900 dark:text-neutral-100">{complianceStats.totalEvents.toLocaleString()}</p>
          <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">All time</p>
        </div>

        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Today</p>
            <Calendar className="h-5 w-5 text-primary-400 dark:text-primary-500" />
          </div>
          <p className="mt-2 text-3xl font-bold text-primary-600 dark:text-primary-400">{complianceStats.todayEvents}</p>
          <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">+{Math.round((complianceStats.todayEvents / complianceStats.avgEventsPerDay - 1) * 100)}% vs avg</p>
        </div>

        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Failed Actions</p>
            <XCircle className="h-5 w-5 text-red-400 dark:text-red-500" />
          </div>
          <p className="mt-2 text-3xl font-bold text-red-600 dark:text-red-400">{complianceStats.failedActions}</p>
          <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Last 30 days</p>
        </div>

        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Security Events</p>
            <Shield className="h-5 w-5 text-amber-400 dark:text-amber-500" />
          </div>
          <p className="mt-2 text-3xl font-bold text-amber-600 dark:text-amber-400">{complianceStats.securityEvents}</p>
          <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Last 30 days</p>
        </div>

        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Avg Per Day</p>
            <Clock className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
          </div>
          <p className="mt-2 text-3xl font-bold text-neutral-900 dark:text-neutral-100">{complianceStats.avgEventsPerDay}</p>
          <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">30-day average</p>
        </div>

        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Retention</p>
            <Info className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
          </div>
          <p className="mt-2 text-3xl font-bold text-neutral-900 dark:text-neutral-100">{complianceStats.retentionDays}d</p>
          <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Then archived</p>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
        <div className="space-y-4">
          {/* Search */}
          <div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-400 dark:text-neutral-500" />
              <input
                type="text"
                placeholder="Search by action, resource, user, or details..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 py-2 pl-10 pr-4 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
              />
            </div>
          </div>

          {/* Filter Row */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-5">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-neutral-700 dark:text-neutral-300">Action Type</label>
              <select
                value={selectedActionType}
                onChange={e => setSelectedActionType(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
              >
                <option value="all">All Actions</option>
                <option value="create">Create</option>
                <option value="read">Read</option>
                <option value="update">Update</option>
                <option value="delete">Delete</option>
                <option value="export">Export</option>
                <option value="system">System</option>
                <option value="security">Security</option>
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-neutral-700 dark:text-neutral-300">Resource Type</label>
              <select
                value={selectedResourceType}
                onChange={e => setSelectedResourceType(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
              >
                <option value="all">All Resources</option>
                <option value="project">Projects</option>
                <option value="deliverable">Deliverables</option>
                <option value="user">Users</option>
                <option value="settings">Settings</option>
                <option value="template">Templates</option>
                <option value="client">Clients</option>
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-neutral-700 dark:text-neutral-300">Status</label>
              <select
                value={selectedStatus}
                onChange={e => setSelectedStatus(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
              >
                <option value="all">All Statuses</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="warning">Warning</option>
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-neutral-700 dark:text-neutral-300">User</label>
              <select
                value={selectedUser}
                onChange={e => setSelectedUser(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
              >
                <option value="all">All Users</option>
                {uniqueUsers.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-neutral-700 dark:text-neutral-300">Date Range</label>
              <select
                value={dateRange}
                onChange={e => setDateRange(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
              >
                <option value="all">All Time</option>
                <option value="today">Today</option>
                <option value="week">Last 7 Days</option>
                <option value="month">Last 30 Days</option>
                <option value="quarter">Last 90 Days</option>
              </select>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700 pt-4">
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Showing <span className="font-semibold text-neutral-900 dark:text-neutral-100">{filteredLogs.length}</span> of{' '}
              <span className="font-semibold text-neutral-900 dark:text-neutral-100">{auditLogs.length}</span> events
            </p>
            <button
              onClick={() => setShowExportModal(true)}
              className="flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            >
              <Download className="h-4 w-4" />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-700 dark:text-neutral-300">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-700 dark:text-neutral-300">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-700 dark:text-neutral-300">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-700 dark:text-neutral-300">
                  Resource
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-700 dark:text-neutral-300">
                  IP Address
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-700 dark:text-neutral-300">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-700 dark:text-neutral-300">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700 bg-white dark:bg-neutral-900">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center">
                    <Filter className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-600" />
                    <h3 className="mt-4 text-sm font-medium text-neutral-900 dark:text-neutral-100">No events found</h3>
                    <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">Try adjusting your filters</p>
                  </td>
                </tr>
              ) : (
                filteredLogs.map(log => {
                  const ActionIcon = getActionTypeIcon(log.actionType);
                  const StatusIcon = getStatusIcon(log.status);

                  return (
                    <tr
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className="cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-800"
                    >
                      <td className="whitespace-nowrap px-6 py-4">
                        <div>
                          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{formatTimeAgo(log.timestamp)}</p>
                          <p className="text-xs text-neutral-500 dark:text-neutral-400">{formatDateTime(log.timestamp)}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-800">
                            <User className="h-4 w-4 text-neutral-600 dark:text-neutral-400" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{log.user.name}</p>
                            <p className="text-xs text-neutral-500 dark:text-neutral-400">{log.user.role}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className={`rounded-lg p-2 ${getActionTypeColor(log.actionType)}`}>
                            <ActionIcon className="h-4 w-4" />
                          </div>
                          <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{log.action}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div>
                          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{log.resource}</p>
                          <p className="text-xs text-neutral-500 dark:text-neutral-400 capitalize">{log.resourceType}</p>
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4">
                        <p className="font-mono text-xs text-neutral-600 dark:text-neutral-400">{log.ipAddress}</p>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4">
                        <div className="flex items-center gap-1.5">
                          <StatusIcon className={`h-4 w-4 ${getStatusColor(log.status)}`} />
                          <span className={`text-sm font-medium capitalize ${getStatusColor(log.status)}`}>
                            {log.status}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2">{log.details}</p>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-neutral-950/60">
          <div className="w-full max-w-md rounded-lg bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 p-6 shadow-xl">
            <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-100">Export Audit Logs</h2>
            <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
              Export {filteredLogs.length} filtered events for compliance reporting
            </p>

            <div className="mt-6 space-y-3">
              <button
                onClick={() => handleExport('csv')}
                className="flex w-full items-center justify-between rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 p-4 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                <div>
                  <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">CSV Format</p>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400">Excel-compatible spreadsheet format</p>
                </div>
                <FileText className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
              </button>

              <button
                onClick={() => handleExport('json')}
                className="flex w-full items-center justify-between rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 p-4 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                <div>
                  <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">JSON Format</p>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400">Machine-readable structured data</p>
                </div>
                <FileText className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
              </button>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setShowExportModal(false)}
                className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Log Detail Modal */}
      {selectedLog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-neutral-950/60"
          onClick={() => setSelectedLog(null)}
        >
          <div
            className="w-full max-w-2xl rounded-lg bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 p-6 shadow-xl"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-100">Event Details</h2>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">ID: {selectedLog.id}</p>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300"
              >
                <XCircle className="h-6 w-6" />
              </button>
            </div>

            <div className="mt-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Timestamp</p>
                  <p className="mt-1 text-sm text-neutral-900 dark:text-neutral-100">{formatDateTime(selectedLog.timestamp)}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Time Ago</p>
                  <p className="mt-1 text-sm text-neutral-900 dark:text-neutral-100">{formatTimeAgo(selectedLog.timestamp)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">User</p>
                  <p className="mt-1 text-sm font-semibold text-neutral-900 dark:text-neutral-100">{selectedLog.user.name}</p>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400">{selectedLog.user.email}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Role</p>
                  <p className="mt-1 text-sm text-neutral-900 dark:text-neutral-100">{selectedLog.user.role}</p>
                </div>
              </div>

              <div>
                <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Action</p>
                <p className="mt-1 text-sm font-semibold text-neutral-900 dark:text-neutral-100">{selectedLog.action}</p>
                <p className="text-xs text-neutral-600 dark:text-neutral-400 capitalize">Type: {selectedLog.actionType}</p>
              </div>

              <div>
                <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Resource</p>
                <p className="mt-1 text-sm font-semibold text-neutral-900 dark:text-neutral-100">{selectedLog.resource}</p>
                <p className="text-xs text-neutral-600 dark:text-neutral-400 capitalize">Type: {selectedLog.resourceType}</p>
              </div>

              <div>
                <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Details</p>
                <p className="mt-1 text-sm text-neutral-900 dark:text-neutral-100">{selectedLog.details}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">IP Address</p>
                  <p className="mt-1 font-mono text-sm text-neutral-900 dark:text-neutral-100">{selectedLog.ipAddress}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Status</p>
                  <div className="mt-1 flex items-center gap-1.5">
                    {(() => {
                      const StatusIcon = getStatusIcon(selectedLog.status);
                      return (
                        <>
                          <StatusIcon className={`h-4 w-4 ${getStatusColor(selectedLog.status)}`} />
                          <span className={`text-sm font-medium capitalize ${getStatusColor(selectedLog.status)}`}>
                            {selectedLog.status}
                          </span>
                        </>
                      );
                    })()}
                  </div>
                </div>
              </div>

              {selectedLog.metadata && Object.keys(selectedLog.metadata).length > 0 && (
                <div>
                  <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Additional Metadata</p>
                  <div className="mt-2 rounded-lg bg-neutral-50 dark:bg-neutral-800 p-4">
                    <pre className="text-xs text-neutral-900 dark:text-neutral-100 overflow-x-auto">
                      {JSON.stringify(selectedLog.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
