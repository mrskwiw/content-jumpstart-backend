import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { projectsApi } from '@/api/projects';
import { deliverablesApi } from '@/api/deliverables';
import { runsApi } from '@/api/runs';
import { clientsApi } from '@/api/clients';
import type { Project, Deliverable, Run, Client } from '@/types/domain';
import type { PaginatedResponse } from '@/types/pagination';
import { getUseMocksEnabled } from '@/utils/env';
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  TrendingUp,
  Sparkles,
  FileText,
  Activity,
  Users,
  AlertCircle,
  Star,
  DollarSign,
  Calendar,
  FileSearch,
  ArrowRight,
  AlertTriangle
} from 'lucide-react';
import { format, formatDistanceToNow, isAfter, addDays } from 'date-fns';
import { Button, Badge, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';

function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  color = 'primary'
}: {
  title: string;
  value: number | string;
  icon: any;
  trend?: string;
  color?: 'primary' | 'emerald' | 'amber' | 'indigo' | 'purple';
}) {
  const colors = {
    primary: 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300',
    emerald: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400',
    amber: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400',
    indigo: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400',
    purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
  };

  return (
    <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-neutral-900 dark:text-neutral-100">{value}</p>
          {trend && <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{trend}</p>}
        </div>
        <div className={`rounded-lg p-3 ${colors[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}

export default function Overview() {
  const navigate = useNavigate();
  const mocksEnabled = getUseMocksEnabled();

  const { data: projectsResponse } = useQuery<PaginatedResponse<Project>>({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list({}),
  });

  // Extract projects from paginated response
  const projects = projectsResponse?.items ?? [];

  const { data: deliverablesResponse } = useQuery<Deliverable[]>({
    queryKey: ['deliverables'],
    queryFn: () => deliverablesApi.list({}),
  });

  const { data: runsResponse } = useQuery<Run[]>({
    queryKey: ['runs'],
    queryFn: () => runsApi.list({}),
  });

  const { data: clients = [] } = useQuery<Client[]>({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  });

  // Calculate metrics
  const deliverables: Deliverable[] = deliverablesResponse ?? [];
  const runs: Run[] = runsResponse ?? [];
  const totalProjects = projects.length;
  const activeProjects = projects.filter(p =>
    p.status === 'generating' || p.status === 'qa' || p.status === 'ready'
  );
  const activeProjectsCount = activeProjects.length;
  const completedProjects = projects.filter(p =>
    p.status === 'delivered' || p.status === 'exported'
  ).length;
  const pendingDeliverables = deliverables.filter(d => d.status === 'ready').length;

  // NEW: Calculate quality score (average of recent runs)
  const recentRuns = runs.slice(-10); // Last 10 runs
  const avgQualityScore = recentRuns.length > 0
    ? Math.round(
        (recentRuns.reduce((sum, run) => {
          const quality = (run as { qualityScore?: number }).qualityScore ?? 0;
          return sum + quality;
        }, 0) /
          recentRuns.length) *
          100
      ) / 100
    : 0;

  // NEW: Calculate revenue (mock data for now - would come from billing API)
  const mockMonthlyRevenue = completedProjects * 1800; // Avg $1,800/project

  // Client metrics
  const totalClients = clients.length;

  // NEW: Content in review count (projects in QA status)
  const contentInReview = projects.filter(p => p.status === 'qa').length;
  const oldestReviewItem = projects
    .filter(p => p.status === 'qa' && p.lastRunAt)
    .sort((a, b) => new Date(a.lastRunAt!).getTime() - new Date(b.lastRunAt!).getTime())[0];
  const oldestReviewAge = oldestReviewItem
    ? formatDistanceToNow(new Date(oldestReviewItem.lastRunAt!), { addSuffix: true })
    : '';

  // NEW: Pending tasks with priorities
  const pendingTasks = [
    ...projects
      .filter(p => p.status === 'qa')
      .map(p => ({
        id: `review-${p.id}`,
        type: 'review' as const,
        priority: 'high' as const,
        title: `Review content for ${p.name}`,
        project: p.name,
        dueIn: '2 hours',
        projectId: p.id
      })),
    ...deliverables
      .filter(d => d.status === 'ready')
      .slice(0, 3)
      .map(d => ({
        id: `approve-${d.id}`,
        type: 'approve' as const,
        priority: 'medium' as const,
        title: `Approve deliverable`,
        project: d.projectId,
        dueIn: '1 day',
        deliverableId: d.id
      })),
    ...projects
      .filter(p => p.status === 'ready')
      .slice(0, 2)
      .map(p => ({
        id: `deliver-${p.id}`,
        type: 'deliver' as const,
        priority: 'high' as const,
        title: `Deliver to client`,
        project: p.name,
        dueIn: '4 hours',
        projectId: p.id
      }))
  ].sort((a, b) => {
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    return priorityOrder[a.priority] - priorityOrder[b.priority];
  }).slice(0, 5);

  // Enhanced recent activity with more context
  const recentActivity = [
    ...projects
      .filter(p => p.lastRunAt)
      .map(p => ({
        type: 'project' as const,
        id: p.id,
        name: p.name,
        action: p.status === 'delivered' ? 'delivered' : `moved to ${p.status}`,
        timestamp: new Date(p.lastRunAt!),
        user: 'System', // Would come from audit log
        target: p.name
      })),
    ...deliverables
      .filter(d => d.deliveredAt)
      .map(d => ({
        type: 'deliverable' as const,
        id: d.id,
        name: d.projectId,
        action: 'marked delivered',
        timestamp: new Date(d.deliveredAt!),
        user: 'Operator', // Would come from audit log
        target: d.projectId
      })),
  ]
    .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
    .slice(0, 10); // Show last 10 instead of 5

  return (
    <div className="space-y-6">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">Dashboard Overview</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Real-time operational metrics, pending tasks, and recent activity.
        </p>
      </header>

      {/* Stats Grid - 5 metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <StatCard
          title="Active Projects"
          value={activeProjectsCount}
          icon={FolderKanban}
          color="primary"
          trend={`${totalProjects} total`}
        />
        <StatCard
          title="Content in Review"
          value={contentInReview}
          icon={FileSearch}
          color="amber"
          trend={oldestReviewAge ? `Oldest: ${oldestReviewAge}` : ''}
        />
        <StatCard
          title="Deliveries Due Today"
          value={pendingDeliverables}
          icon={Clock}
          color="indigo"
        />
        <StatCard
          title="Quality Score"
          value={avgQualityScore ? `${avgQualityScore}%` : 'N/A'}
          icon={Star}
          color="purple"
          trend="Average across recent projects"
        />
        <StatCard
          title="Revenue This Month"
          value={`$${mockMonthlyRevenue.toLocaleString()}`}
          icon={DollarSign}
          color="emerald"
          trend={`${completedProjects} completed`}
        />
      </div>

      {/* Quick Actions - 5 actions */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-neutral-900 dark:text-neutral-100">Quick Actions</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <button
            onClick={() => navigate('/dashboard/wizard')}
            className="flex items-center gap-3 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 text-left transition-colors hover:border-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20"
          >
            <div className="rounded-lg bg-primary-50 dark:bg-primary-900/20 p-2 text-primary-700 dark:text-primary-300">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="font-semibold text-neutral-900 dark:text-neutral-100">New Project</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400">Start wizard</div>
            </div>
          </button>

          <button
            onClick={() => navigate('/dashboard/projects')}
            className="flex items-center gap-3 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 text-left transition-colors hover:border-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20"
          >
            <div className="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 p-2 text-emerald-600 dark:text-emerald-400">
              <FolderKanban className="h-5 w-5" />
            </div>
            <div>
              <div className="font-semibold text-neutral-900 dark:text-neutral-100">View Projects</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400">{totalProjects} total</div>
            </div>
          </button>

          <button
            onClick={() => navigate('/dashboard/content-review')}
            className="flex items-center gap-3 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 text-left transition-colors hover:border-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20"
          >
            <div className="rounded-lg bg-purple-50 dark:bg-purple-900/20 p-2 text-purple-600 dark:text-purple-400">
              <FileSearch className="h-5 w-5" />
            </div>
            <div>
              <div className="font-semibold text-neutral-900 dark:text-neutral-100">Review Content</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400">{contentInReview} pending</div>
            </div>
          </button>

          <button
            onClick={() => navigate('/dashboard/analytics')}
            className="flex items-center gap-3 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 text-left transition-colors hover:border-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20"
          >
            <div className="rounded-lg bg-indigo-50 dark:bg-indigo-900/20 p-2 text-indigo-600 dark:text-indigo-400">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <div className="font-semibold text-neutral-900 dark:text-neutral-100">View Analytics</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400">Performance</div>
            </div>
          </button>

          <button
            onClick={() => navigate('/dashboard/calendar')}
            className="flex items-center gap-3 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 text-left transition-colors hover:border-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20"
          >
            <div className="rounded-lg bg-amber-50 dark:bg-amber-900/20 p-2 text-amber-600 dark:text-amber-400">
              <Calendar className="h-5 w-5" />
            </div>
            <div>
              <div className="font-semibold text-neutral-900 dark:text-neutral-100">View Calendar</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400">Schedules</div>
            </div>
          </button>
        </div>
      </div>

      {/* Active Projects - Top 5 with details */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Active Projects</h2>
          <button
            onClick={() => navigate('/dashboard/projects')}
            className="text-xs font-medium text-primary-700 dark:text-primary-300 hover:text-primary-600 dark:hover:text-primary-400 flex items-center gap-1"
          >
            View All <ArrowRight className="h-3 w-3" />
          </button>
        </div>

        {activeProjects.length === 0 ? (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">No active projects</p>
        ) : (
          <div className="space-y-4">
            {activeProjects.slice(0, 5).map(project => {
              // Calculate progress based on status
              const statusProgress = {
                draft: 10,
                generating: 40,
                qa: 70,
                ready: 90,
                exported: 100,
                delivered: 100,
                error: 0,
              }[project.status] || 0;

              // Determine next action
              const nextAction = {
                draft: 'Start generation',
                generating: 'Wait for completion',
                qa: 'Review quality',
                ready: 'Deliver to client',
                exported: 'Mark as delivered',
                delivered: 'Complete',
                error: 'Investigate error',
              }[project.status] || 'Review status';

              return (
                <button
                  key={project.id}
                  onClick={() => navigate(`/dashboard/projects/${project.id}`)}
                  className="w-full rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 text-left transition-all hover:border-primary-500 hover:shadow-md"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="font-semibold text-neutral-900 dark:text-neutral-100 hover:text-primary-700 dark:hover:text-primary-300">
                        {project.name}
                      </div>
                      <div className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                        Client: {project.clientId}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize
                        ${project.status === 'qa' ? 'bg-amber-100 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300' : ''}
                        ${project.status === 'generating' ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300' : ''}
                        ${project.status === 'ready' ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300' : ''}
                      `}>
                        {project.status}
                      </span>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-neutral-600 dark:text-neutral-400 mb-1">
                      <span>Progress</span>
                      <span>{statusProgress}%</span>
                    </div>
                    <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
                      <div
                        className="bg-primary-600 dark:bg-primary-500 h-2 rounded-full transition-all"
                        style={{ width: `${statusProgress}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-4">
                      <span className="text-neutral-600 dark:text-neutral-400">
                        Next: <span className="font-medium text-neutral-900 dark:text-neutral-100">{nextAction}</span>
                      </span>
                    </div>
                    {project.lastRunAt && (
                      <span className="text-neutral-500 dark:text-neutral-400">
                        Updated {formatDistanceToNow(new Date(project.lastRunAt), { addSuffix: true })}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Pending Tasks - Sorted by priority */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Pending Tasks</h2>
          <span className="text-xs font-medium text-neutral-600 dark:text-neutral-400">
            Sorted by Priority
          </span>
        </div>

        {pendingTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8">
            <CheckCircle2 className="h-12 w-12 text-emerald-500 dark:text-emerald-400 mb-2" />
            <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">All caught up!</p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">No pending tasks</p>
          </div>
        ) : (
          <div className="space-y-2">
            {pendingTasks.map(task => (
              <button
                key={task.id}
                onClick={() => {
                  if (task.type === 'review' && task.projectId) {
                    navigate(`/dashboard/projects/${task.projectId}`);
                  } else if (task.type === 'approve' || task.type === 'deliver') {
                    navigate('/dashboard/deliverables');
                  }
                }}
                className="w-full flex items-center justify-between p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  {task.priority === 'high' ? (
                    <AlertTriangle className="h-4 w-4 text-red-500 dark:text-red-400" />
                  ) : (
                    <Clock className="h-4 w-4 text-amber-500 dark:text-amber-400" />
                  )}
                  <div>
                    <div className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {task.title}
                    </div>
                    <div className="text-xs text-neutral-600 dark:text-neutral-400">
                      Project: {task.project}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className={`text-xs font-semibold uppercase ${
                      task.priority === 'high'
                        ? 'text-red-600 dark:text-red-400'
                        : task.priority === 'medium'
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-neutral-600 dark:text-neutral-400'
                    }`}
                  >
                    {task.priority}
                  </div>
                  <div className="text-xs text-neutral-500 dark:text-neutral-400">
                    Due in {task.dueIn}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Recent Activity - Enhanced with 10 items */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-neutral-900 dark:text-neutral-100">Recent Activity</h2>
        {recentActivity.length === 0 ? (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">No recent activity</p>
        ) : (
          <div className="space-y-3">
            {recentActivity.map((item, idx) => (
              <div
                key={`${item.type}-${item.id}-${idx}`}
                className="flex items-center justify-between border-b border-neutral-100 dark:border-neutral-800 pb-3 last:border-0 last:pb-0"
              >
                <div className="flex items-center gap-3">
                  {item.type === 'project' ? (
                    <div className="rounded-lg bg-primary-50 dark:bg-primary-900/20 p-2">
                      <FolderKanban className="h-4 w-4 text-primary-700 dark:text-primary-300" />
                    </div>
                  ) : (
                    <div className="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 p-2">
                      <FileText className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    </div>
                  )}
                  <div>
                    <div className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {item.user} {item.action}
                    </div>
                    <div className="text-xs text-neutral-600 dark:text-neutral-400">{item.target}</div>
                  </div>
                </div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400">
                  {formatDistanceToNow(item.timestamp, { addSuffix: true })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
