import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bell,
  CheckCircle,
  AlertCircle,
  Clock,
  Flag,
  Filter,
  Search,
  X,
  Archive,
  Trash2,
  Eye,
  EyeOff,
  Calendar,
  User,
  FileText,
  Settings,
  Plus,
} from 'lucide-react';

// Notification types
type NotificationType = 'task' | 'alert' | 'reminder' | 'mention' | 'system';
type NotificationPriority = 'low' | 'medium' | 'high' | 'urgent';
type NotificationStatus = 'unread' | 'read' | 'archived';

// Notification interface
interface Notification {
  id: string;
  type: NotificationType;
  priority: NotificationPriority;
  status: NotificationStatus;
  title: string;
  message: string;
  timestamp: string;
  actionUrl?: string;
  actionLabel?: string;
  assignedTo?: string;
  dueDate?: string;
  relatedProject?: string;
  relatedClient?: string;
}

// Task interface
interface Task {
  id: string;
  title: string;
  description: string;
  priority: NotificationPriority;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  assignedTo: string;
  createdBy: string;
  dueDate: string;
  createdAt: string;
  completedAt?: string;
  project?: string;
  client?: string;
}

// Mock notifications
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'task',
    priority: 'high',
    status: 'unread',
    title: 'Review content for Acme Corp',
    message: 'Quality assurance check needed for 30 posts',
    timestamp: '2025-12-17T14:30:00',
    actionUrl: '/dashboard/content',
    actionLabel: 'Review Now',
    assignedTo: 'You',
    dueDate: '2025-12-18',
    relatedProject: 'PRJ-001',
    relatedClient: 'Acme Corp',
  },
  {
    id: '2',
    type: 'alert',
    priority: 'urgent',
    status: 'unread',
    title: 'Deliverable deadline approaching',
    message: 'TechStart Inc deliverable due in 2 hours',
    timestamp: '2025-12-17T13:00:00',
    actionUrl: '/dashboard/deliverables',
    actionLabel: 'View Deliverable',
    dueDate: '2025-12-17T15:00:00',
    relatedProject: 'PRJ-002',
    relatedClient: 'TechStart Inc',
  },
  {
    id: '3',
    type: 'reminder',
    priority: 'medium',
    status: 'unread',
    title: 'Follow up with StartupXYZ',
    message: 'Check client satisfaction 2 weeks after delivery',
    timestamp: '2025-12-17T10:00:00',
    actionUrl: '/dashboard/clients/startup-xyz',
    actionLabel: 'Send Email',
    relatedClient: 'StartupXYZ',
  },
  {
    id: '4',
    type: 'mention',
    priority: 'low',
    status: 'read',
    title: 'Michael mentioned you',
    message: 'In comment on GrowthCo project',
    timestamp: '2025-12-16T16:30:00',
    actionUrl: '/dashboard/projects/growthco',
    actionLabel: 'View Comment',
    relatedProject: 'PRJ-003',
    relatedClient: 'GrowthCo',
  },
  {
    id: '5',
    type: 'system',
    priority: 'low',
    status: 'read',
    title: 'System update available',
    message: 'New features and improvements ready to install',
    timestamp: '2025-12-16T09:00:00',
    actionUrl: '/dashboard/settings',
    actionLabel: 'Learn More',
  },
  {
    id: '6',
    type: 'task',
    priority: 'medium',
    status: 'archived',
    title: 'Update template library',
    message: 'Add new templates based on client feedback',
    timestamp: '2025-12-15T14:00:00',
    assignedTo: 'Sarah Johnson',
    dueDate: '2025-12-20',
  },
];

// Mock tasks
const mockTasks: Task[] = [
  {
    id: '1',
    title: 'Review Acme Corp deliverables',
    description: 'Quality check for 30 LinkedIn posts before final delivery',
    priority: 'high',
    status: 'pending',
    assignedTo: 'You',
    createdBy: 'System',
    dueDate: '2025-12-18',
    createdAt: '2025-12-17T09:00:00',
    project: 'PRJ-001',
    client: 'Acme Corp',
  },
  {
    id: '2',
    title: 'Generate content for NewCo',
    description: 'Create 30 posts based on approved brief',
    priority: 'medium',
    status: 'in_progress',
    assignedTo: 'Michael Chen',
    createdBy: 'Sarah Johnson',
    dueDate: '2025-12-19',
    createdAt: '2025-12-16T10:00:00',
    project: 'PRJ-004',
    client: 'NewCo',
  },
  {
    id: '3',
    title: 'Client satisfaction survey',
    description: 'Send follow-up survey to StartupXYZ',
    priority: 'low',
    status: 'pending',
    assignedTo: 'Emily Rodriguez',
    createdBy: 'System',
    dueDate: '2025-12-20',
    createdAt: '2025-12-15T14:30:00',
    client: 'StartupXYZ',
  },
  {
    id: '4',
    title: 'Update brand voice guide',
    description: 'Incorporate client feedback on tone adjustments',
    priority: 'medium',
    status: 'completed',
    assignedTo: 'You',
    createdBy: 'Sarah Johnson',
    dueDate: '2025-12-17',
    createdAt: '2025-12-14T11:00:00',
    completedAt: '2025-12-17T08:30:00',
    project: 'PRJ-001',
    client: 'Acme Corp',
  },
];

export default function Notifications() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'notifications' | 'tasks'>('notifications');
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [showNewTaskModal, setShowNewTaskModal] = useState(false);

  // Mock queries
  const { data: notifications = mockNotifications } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockNotifications;
    },
  });

  const { data: tasks = mockTasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockTasks;
    },
  });

  // Mutations
  const markAsReadMutation = useMutation({
    mutationFn: async (id: string) => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const archiveMutation = useMutation({
    mutationFn: async (id: string) => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const updateTaskMutation = useMutation({
    mutationFn: async (data: { taskId: string; status: Task['status'] }) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Filter notifications
  const filteredNotifications = useMemo(() => {
    let filtered = notifications;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        n =>
          n.title.toLowerCase().includes(query) ||
          n.message.toLowerCase().includes(query) ||
          n.relatedClient?.toLowerCase().includes(query)
      );
    }

    if (typeFilter) {
      filtered = filtered.filter(n => n.type === typeFilter);
    }

    if (priorityFilter) {
      filtered = filtered.filter(n => n.priority === priorityFilter);
    }

    if (statusFilter) {
      filtered = filtered.filter(n => n.status === statusFilter);
    }

    return filtered;
  }, [notifications, searchQuery, typeFilter, priorityFilter, statusFilter]);

  // Filter tasks
  const filteredTasks = useMemo(() => {
    let filtered = tasks;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        t =>
          t.title.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query) ||
          t.client?.toLowerCase().includes(query)
      );
    }

    if (priorityFilter) {
      filtered = filtered.filter(t => t.priority === priorityFilter);
    }

    if (statusFilter) {
      filtered = filtered.filter(t => t.status === statusFilter);
    }

    return filtered;
  }, [tasks, searchQuery, priorityFilter, statusFilter]);

  // Calculate stats
  const notificationStats = useMemo(() => {
    return {
      total: notifications.length,
      unread: notifications.filter(n => n.status === 'unread').length,
      urgent: notifications.filter(n => n.priority === 'urgent').length,
      tasks: notifications.filter(n => n.type === 'task').length,
    };
  }, [notifications]);

  const taskStats = useMemo(() => {
    return {
      total: tasks.length,
      pending: tasks.filter(t => t.status === 'pending').length,
      inProgress: tasks.filter(t => t.status === 'in_progress').length,
      completed: tasks.filter(t => t.status === 'completed').length,
    };
  }, [tasks]);

  // Get priority badge
  const getPriorityBadge = (priority: NotificationPriority) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'low':
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  // Get type icon
  const getTypeIcon = (type: NotificationType) => {
    switch (type) {
      case 'task':
        return CheckCircle;
      case 'alert':
        return AlertCircle;
      case 'reminder':
        return Clock;
      case 'mention':
        return User;
      case 'system':
        return Settings;
    }
  };

  // Format time ago
  const formatTimeAgo = (dateString: string) => {
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
          <h1 className="text-2xl font-bold text-slate-900">Notifications & Tasks</h1>
          <p className="text-sm text-slate-600 mt-1">Manage alerts, reminders, and tasks</p>
        </div>
        <button
          onClick={() => setShowNewTaskModal(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          New Task
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Unread</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{notificationStats.unread}</p>
            </div>
            <div className="rounded-lg bg-blue-100 p-3">
              <Bell className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Urgent</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{notificationStats.urgent}</p>
            </div>
            <div className="rounded-lg bg-red-100 p-3">
              <AlertCircle className="h-6 w-6 text-red-600" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Pending Tasks</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{taskStats.pending}</p>
            </div>
            <div className="rounded-lg bg-orange-100 p-3">
              <Clock className="h-6 w-6 text-orange-600" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">In Progress</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{taskStats.inProgress}</p>
            </div>
            <div className="rounded-lg bg-purple-100 p-3">
              <FileText className="h-6 w-6 text-purple-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab('notifications')}
            className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'notifications'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            Notifications ({notificationStats.total})
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'tasks'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            Tasks ({taskStats.total})
          </button>
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
                placeholder="Search..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-slate-300 pl-10 pr-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Type Filter (Notifications only) */}
          {activeTab === 'notifications' && (
            <div className="sm:w-40">
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <select
                  value={typeFilter}
                  onChange={e => setTypeFilter(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 pl-10 pr-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none"
                >
                  <option value="">All Types</option>
                  <option value="task">Tasks</option>
                  <option value="alert">Alerts</option>
                  <option value="reminder">Reminders</option>
                  <option value="mention">Mentions</option>
                  <option value="system">System</option>
                </select>
              </div>
            </div>
          )}

          {/* Priority Filter */}
          <div className="sm:w-40">
            <select
              value={priorityFilter}
              onChange={e => setPriorityFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none"
            >
              <option value="">All Priorities</option>
              <option value="urgent">Urgent</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="sm:w-40">
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none"
            >
              <option value="">All Statuses</option>
              {activeTab === 'notifications' ? (
                <>
                  <option value="unread">Unread</option>
                  <option value="read">Read</option>
                  <option value="archived">Archived</option>
                </>
              ) : (
                <>
                  <option value="pending">Pending</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </>
              )}
            </select>
          </div>

          {(searchQuery || typeFilter || priorityFilter || statusFilter) && (
            <button
              onClick={() => {
                setSearchQuery('');
                setTypeFilter('');
                setPriorityFilter('');
                setStatusFilter('');
              }}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium whitespace-nowrap"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="space-y-2">
          {filteredNotifications.map(notification => {
            const TypeIcon = getTypeIcon(notification.type);
            return (
              <div
                key={notification.id}
                className={`rounded-lg border bg-white p-4 transition-all ${
                  notification.status === 'unread'
                    ? 'border-blue-200 bg-blue-50/30'
                    : 'border-slate-200'
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div
                    className={`rounded-lg p-2 flex-shrink-0 ${
                      notification.priority === 'urgent'
                        ? 'bg-red-100'
                        : notification.priority === 'high'
                        ? 'bg-orange-100'
                        : 'bg-slate-100'
                    }`}
                  >
                    <TypeIcon
                      className={`h-5 w-5 ${
                        notification.priority === 'urgent'
                          ? 'text-red-600'
                          : notification.priority === 'high'
                          ? 'text-orange-600'
                          : 'text-slate-600'
                      }`}
                    />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div className="flex-1">
                        <h3 className="text-sm font-semibold text-slate-900">{notification.title}</h3>
                        {notification.status === 'unread' && (
                          <span className="inline-block h-2 w-2 rounded-full bg-blue-600 ml-2"></span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`rounded-md border px-2 py-0.5 text-xs font-medium ${getPriorityBadge(notification.priority)}`}>
                          {notification.priority}
                        </span>
                        <span className="text-xs text-slate-500">{formatTimeAgo(notification.timestamp)}</span>
                      </div>
                    </div>

                    <p className="text-sm text-slate-600 mb-3">{notification.message}</p>

                    {/* Metadata */}
                    {(notification.relatedClient || notification.dueDate) && (
                      <div className="flex flex-wrap gap-3 text-xs text-slate-600 mb-3">
                        {notification.relatedClient && (
                          <span className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            {notification.relatedClient}
                          </span>
                        )}
                        {notification.dueDate && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            Due: {new Date(notification.dueDate).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {notification.actionUrl && (
                        <button className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700">
                          {notification.actionLabel || 'View'}
                          →
                        </button>
                      )}
                      {notification.status === 'unread' && (
                        <button
                          onClick={() => markAsReadMutation.mutate(notification.id)}
                          className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900"
                        >
                          <Eye className="h-3 w-3" />
                          Mark Read
                        </button>
                      )}
                      {notification.status !== 'archived' && (
                        <button
                          onClick={() => archiveMutation.mutate(notification.id)}
                          className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900"
                        >
                          <Archive className="h-3 w-3" />
                          Archive
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {filteredNotifications.length === 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
              <Bell className="h-12 w-12 text-slate-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">No notifications</h3>
              <p className="text-sm text-slate-600">You're all caught up!</p>
            </div>
          )}
        </div>
      )}

      {/* Tasks Tab */}
      {activeTab === 'tasks' && (
        <div className="space-y-2">
          {filteredTasks.map(task => (
            <div key={task.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start gap-4">
                {/* Checkbox */}
                <div className="pt-1">
                  <input
                    type="checkbox"
                    checked={task.status === 'completed'}
                    onChange={() =>
                      updateTaskMutation.mutate({
                        taskId: task.id,
                        status: task.status === 'completed' ? 'pending' : 'completed',
                      })
                    }
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                </div>

                {/* Content */}
                <div className="flex-1">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div>
                      <h3
                        className={`text-sm font-semibold ${
                          task.status === 'completed' ? 'text-slate-500 line-through' : 'text-slate-900'
                        }`}
                      >
                        {task.title}
                      </h3>
                      <p className="text-sm text-slate-600 mt-1">{task.description}</p>
                    </div>
                    <span className={`rounded-md border px-2 py-0.5 text-xs font-medium ${getPriorityBadge(task.priority)}`}>
                      {task.priority}
                    </span>
                  </div>

                  {/* Metadata */}
                  <div className="flex flex-wrap gap-4 text-xs text-slate-600 mb-3">
                    <span className="flex items-center gap-1">
                      <User className="h-3 w-3" />
                      {task.assignedTo}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      Due: {new Date(task.dueDate).toLocaleDateString()}
                    </span>
                    {task.client && (
                      <span className="flex items-center gap-1">
                        <FileText className="h-3 w-3" />
                        {task.client}
                      </span>
                    )}
                  </div>

                  {/* Status Badge */}
                  <span
                    className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium ${
                      task.status === 'completed'
                        ? 'bg-green-100 text-green-700 border-green-200'
                        : task.status === 'in_progress'
                        ? 'bg-blue-100 text-blue-700 border-blue-200'
                        : task.status === 'cancelled'
                        ? 'bg-slate-100 text-slate-700 border-slate-200'
                        : 'bg-yellow-100 text-yellow-700 border-yellow-200'
                    }`}
                  >
                    {task.status.replace('_', ' ').charAt(0).toUpperCase() + task.status.slice(1).replace('_', ' ')}
                  </span>
                </div>
              </div>
            </div>
          ))}

          {filteredTasks.length === 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
              <CheckCircle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">No tasks found</h3>
              <p className="text-sm text-slate-600">Try adjusting your filters</p>
            </div>
          )}
        </div>
      )}

      {/* New Task Modal (Placeholder) */}
      {showNewTaskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-slate-900">Create New Task</h3>
              <button
                onClick={() => setShowNewTaskModal(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="text-sm text-slate-600">Task creation form would go here</p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setShowNewTaskModal(false)}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={() => setShowNewTaskModal(false)}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
              >
                Create Task
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
