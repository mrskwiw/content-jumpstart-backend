import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Edit,
  Copy,
  Archive,
  FileText,
  LayoutGrid,
  List,
  Download,
  CheckCircle2,
  XCircle,
  AlertCircle,
  BarChart3,
  Clock,
  User,
  Calendar,
  TrendingUp,
  RefreshCw,
  Eye,
  Flag,
  ExternalLink,
  ChevronDown,
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { projectsApi } from '@/api/projects';
import { clientsApi } from '@/api/clients';
import { postsApi } from '@/api/posts';
import { deliverablesApi } from '@/api/deliverables';
import type { PostDraft, Project } from '@/types/domain';
import type { PaginatedResponse } from '@/types/pagination';

type PostWithMeta = PostDraft & { templateId?: string | number; wordCount?: number; createdAt?: string };

type TabType = 'overview' | 'content' | 'quality' | 'deliverables' | 'revisions' | 'activity';
type ContentView = 'grid' | 'list';

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [contentView, setContentView] = useState<ContentView>('grid');
  const [platformFilter, setPlatformFilter] = useState<string>('all');
  const [templateFilter, setTemplateFilter] = useState<string>('all');

  // Fetch project data
  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  // Fetch client data
  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  });

  // Fetch posts for this project
  const { data: postsResponse } = useQuery<PaginatedResponse<PostDraft>>({
    queryKey: ['posts'],
    queryFn: () => postsApi.list(),
  });

  const allPosts: PostWithMeta[] = (postsResponse?.items ?? []) as PostWithMeta[];

  // Fetch deliverables
  const { data: allDeliverables = [] } = useQuery({
    queryKey: ['deliverables'],
    queryFn: () => deliverablesApi.list(),
  });

  if (projectLoading || !project) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 dark:border-primary-500 border-r-transparent"></div>
          <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">Loading project...</p>
        </div>
      </div>
    );
  }

  const client = clients.find(c => c.id === project.clientId);
  const projectPosts = allPosts.filter((p) => p.projectId === project.id);
  const projectDeliverables = allDeliverables.filter(d => d.projectId === project.id);

  const safeFormatDate = (value?: string | null, fallback = 'Not available') =>
    value ? format(new Date(value), 'MMM d, yyyy') : fallback;

  // Filter posts
  const filteredPosts = useMemo<PostWithMeta[]>(() => {
    let filtered = projectPosts as PostWithMeta[];

    if (platformFilter !== 'all') {
      filtered = filtered.filter(p => p.platform === platformFilter);
    }

    if (templateFilter !== 'all') {
      filtered = filtered.filter(p => p.templateId?.toString() === templateFilter);
    }

    return filtered;
  }, [projectPosts, platformFilter, templateFilter]);

  // Calculate quality metrics (mock data)
  const qualityScore = 87;
  const hookScore = 92;
  const ctaScore = 85;
  const lengthScore = 88;
  const headlineScore = 84;

  // Mock data
  const mockTimeline = {
    created: project.createdAt,
    started: project.createdAt,
    completed: project.lastRunAt,
    delivered: project.status === 'delivered' ? project.lastRunAt : null,
  };

  const mockRevisions = [
    { id: '1', date: '2024-01-20', requestedBy: 'Client', changes: 'Adjusted tone to be more casual', posts: 3 },
    { id: '2', date: '2024-01-22', requestedBy: 'Operator', changes: 'Fixed CTA inconsistencies', posts: 5 },
  ];

  const mockActivityLog = [
    { id: '1', action: 'Project created', user: 'Sarah Martinez', timestamp: project.createdAt, details: '' },
    { id: '2', action: 'Content generated', user: 'System', timestamp: project.createdAt, details: '30 posts created' },
    { id: '3', action: 'QA completed', user: 'System', timestamp: project.lastRunAt || project.createdAt, details: 'Quality score: 87%' },
    { id: '4', action: 'Deliverable created', user: 'System', timestamp: project.lastRunAt || project.createdAt, details: 'TXT format' },
  ];

  const mockDeliverableFiles = [
    { name: 'Deliverable.md', status: 'generated', format: 'MD', size: '45 KB' },
    { name: 'Posts.txt', status: 'delivered', format: 'TXT', size: '28 KB' },
    { name: 'Posts.json', status: 'generated', format: 'JSON', size: '52 KB' },
    { name: 'Brand_Voice_Guide.md', status: 'delivered', format: 'MD', size: '12 KB' },
    { name: 'QA_Report.md', status: 'generated', format: 'MD', size: '8 KB' },
    { name: 'Posting_Schedule.csv', status: 'generated', format: 'CSV', size: '3 KB' },
  ];

  const statusColors: Record<Project['status'], string> = {
    draft: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-300',
    generating: 'bg-primary-100 dark:bg-primary-900/20 text-primary-800 dark:text-primary-300',
    qa: 'bg-amber-100 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300',
    ready: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300',
    exported: 'bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-300',
    delivered: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300',
    error: 'bg-rose-100 dark:bg-rose-900/20 text-rose-800 dark:text-rose-300',
  };

  const tabs: {
    id: TabType;
    label: string;
    icon: typeof FileText;
    count?: number;
  }[] = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'content', label: 'Content', icon: LayoutGrid, count: projectPosts.length },
    { id: 'quality', label: 'Quality Report', icon: BarChart3 },
    { id: 'deliverables', label: 'Deliverables', icon: Download, count: projectDeliverables.length },
    { id: 'revisions', label: 'Revisions', icon: RefreshCw, count: mockRevisions.length },
    { id: 'activity', label: 'Activity Log', icon: Clock },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/dashboard/projects')}
            className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Projects
          </button>
        </div>
      </div>

      {/* Project Header Card */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{project.name}</h1>
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  statusColors[project.status] || 'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-300'
                }`}
              >
                {project.status}
              </span>
              <div className="flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-900/20 px-2.5 py-0.5">
                <BarChart3 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs font-medium text-emerald-800 dark:text-emerald-300">{qualityScore}% Quality</span>
              </div>
            </div>
            <div className="mt-2 flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
              <button
                onClick={() => client && navigate(`/dashboard/clients/${client.id}`)}
                className="flex items-center gap-1 hover:text-primary-600 dark:hover:text-primary-400"
              >
                <User className="h-4 w-4" />
                {client?.name || 'Unknown Client'}
                <ExternalLink className="h-3 w-3" />
              </button>
              <span className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                Created {safeFormatDate(project.createdAt)}
              </span>
              <span className="flex items-center gap-1">
                <FileText className="h-4 w-4" />
              {projectPosts.length} posts
              </span>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <button className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
              <Edit className="h-4 w-4" />
              Edit
            </button>
            <button className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
              <Copy className="h-4 w-4" />
              Clone
            </button>
            <button className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600">
              <Download className="h-4 w-4" />
              Generate Report
            </button>
            <button className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
              <Archive className="h-4 w-4" />
              Archive
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-6 grid grid-cols-5 gap-6 border-t border-neutral-200 dark:border-neutral-700 pt-6">
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Posts Generated</p>
            <p className="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{projectPosts.length}</p>
          </div>
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Quality Score</p>
            <p className="mt-1 text-2xl font-semibold text-emerald-600 dark:text-emerald-400">{qualityScore}%</p>
          </div>
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Deliverables</p>
            <p className="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{projectDeliverables.length}</p>
          </div>
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Revisions</p>
            <p className="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{mockRevisions.length}</p>
          </div>
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Last Updated</p>
            <p className="mt-1 text-sm font-medium text-neutral-900 dark:text-neutral-100">
              {project.lastRunAt ? formatDistanceToNow(new Date(project.lastRunAt), { addSuffix: true }) : 'Never'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-neutral-200 dark:border-neutral-700">
        <nav className="flex gap-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 border-b-2 px-1 py-4 text-sm font-medium ${
                  activeTab === tab.id
                    ? 'border-primary-600 dark:border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-neutral-600 dark:text-neutral-400 hover:border-neutral-300 dark:hover:border-neutral-600 hover:text-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
                {tab.count !== undefined && (
                  <span
                    className={`ml-2 rounded-full px-2 py-0.5 text-xs ${
                      activeTab === tab.id
                        ? 'bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                        : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Project Details */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  <FileText className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                  Project Details
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Project Name</p>
                    <p className="mt-1 font-medium text-neutral-900 dark:text-neutral-100">{project.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Package Tier</p>
                    <span className="mt-1 inline-flex items-center rounded-full bg-primary-100 dark:bg-primary-900/20 px-3 py-1 text-sm font-medium text-primary-800 dark:text-primary-300">
                      Professional
                    </span>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Platforms</p>
                    <div className="mt-1 flex flex-wrap gap-2">
                      <span className="inline-flex items-center rounded-full bg-neutral-100 dark:bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-neutral-800 dark:text-neutral-300">
                        LinkedIn
                      </span>
                      <span className="inline-flex items-center rounded-full bg-neutral-100 dark:bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-neutral-800 dark:text-neutral-300">
                        Twitter
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Timeline */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  <Clock className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                  Timeline
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-neutral-600 dark:text-neutral-400">Created</span>
                    <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {safeFormatDate(mockTimeline.created)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-neutral-600 dark:text-neutral-400">Started</span>
                    <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {safeFormatDate(mockTimeline.started)}
                    </span>
                  </div>
                  {mockTimeline.completed && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-neutral-600 dark:text-neutral-400">Completed</span>
                      <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {safeFormatDate(mockTimeline.completed)}
                      </span>
                    </div>
                  )}
                  {mockTimeline.delivered && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-neutral-600 dark:text-neutral-400">Delivered</span>
                      <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                        {safeFormatDate(mockTimeline.delivered)}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Quality Metrics */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  <BarChart3 className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                  Quality Metrics
                </h3>
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-neutral-600 dark:text-neutral-400">Overall Score</span>
                      <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">{qualityScore}%</span>
                    </div>
                    <div className="mt-2 h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-700">
                      <div
                        className="h-2 rounded-full bg-emerald-600 dark:bg-emerald-500"
                        style={{ width: `${qualityScore}%` }}
                      />
                    </div>
                  </div>
                  <div className="space-y-2 border-t border-neutral-200 dark:border-neutral-700 pt-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-neutral-600 dark:text-neutral-400">Hook Uniqueness</span>
                      <span className="font-medium text-neutral-900 dark:text-neutral-100">{hookScore}%</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-neutral-600 dark:text-neutral-400">CTA Variety</span>
                      <span className="font-medium text-neutral-900 dark:text-neutral-100">{ctaScore}%</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-neutral-600 dark:text-neutral-400">Post Length</span>
                      <span className="font-medium text-neutral-900 dark:text-neutral-100">{lengthScore}%</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-neutral-600 dark:text-neutral-400">Headline Engagement</span>
                      <span className="font-medium text-neutral-900 dark:text-neutral-100">{headlineScore}%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Team Assignment */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  <User className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                  Team Assignment
                </h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Assigned To</p>
                    <div className="mt-2 flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-600 dark:bg-purple-500 text-sm font-semibold text-white">
                        SM
                      </div>
                      <div>
                        <p className="font-medium text-neutral-900 dark:text-neutral-100">Sarah Martinez</p>
                        <p className="text-sm text-neutral-600 dark:text-neutral-400">Content Operator</p>
                      </div>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Reviewed By</p>
                    <div className="mt-2 flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-600 dark:bg-primary-500 text-sm font-semibold text-white">
                        JD
                      </div>
                      <div>
                        <p className="font-medium text-neutral-900 dark:text-neutral-100">John Doe</p>
                        <p className="text-sm text-neutral-600 dark:text-neutral-400">QA Lead</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Brief Summary */}
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
              <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                <FileText className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                Brief Summary
              </h3>
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">Business Description</p>
                  <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                    B2B SaaS company providing marketing automation tools for small businesses.
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">Target Audience</p>
                  <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                    Small business owners, marketing managers, startup founders
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">Content Goals</p>
                  <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                    Build thought leadership, drive website traffic, generate qualified leads
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Content */}
        {activeTab === 'content' && (
          <div className="space-y-4">
            {/* Toolbar */}
            <div className="flex items-center justify-between rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
              <div className="flex items-center gap-4">
                {/* View Toggle */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setContentView('grid')}
                    className={`rounded-lg p-2 ${
                      contentView === 'grid'
                        ? 'bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                        : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                    }`}
                  >
                    <LayoutGrid className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setContentView('list')}
                    className={`rounded-lg p-2 ${
                      contentView === 'list'
                        ? 'bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                        : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                    }`}
                  >
                    <List className="h-4 w-4" />
                  </button>
                </div>

                {/* Filters */}
                <select
                  value={platformFilter}
                  onChange={(e) => setPlatformFilter(e.target.value)}
                  className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
                >
                  <option value="all">All Platforms</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="twitter">Twitter</option>
                  <option value="facebook">Facebook</option>
                </select>

                <select
                  value={templateFilter}
                  onChange={(e) => setTemplateFilter(e.target.value)}
                  className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
                >
                  <option value="all">All Templates</option>
                  {Array.from(new Set(projectPosts.map(p => p.templateId?.toString()))).filter(Boolean).map(id => (
                    <option key={id} value={id}>{`Template ${id}`}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-neutral-600 dark:text-neutral-400">{filteredPosts.length} posts</span>
                <button className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
                  Export Selected
                </button>
              </div>
            </div>

            {/* Content Display */}
            {contentView === 'grid' ? (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredPosts.length === 0 ? (
                  <div className="col-span-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-12 text-center">
                    <FileText className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-600" />
                    <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">No posts found</p>
                  </div>
                ) : (
                  filteredPosts.map((post) => (
                    <div key={post.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4 hover:shadow-md transition-shadow">
                      <div className="mb-3 flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center rounded-full bg-primary-100 dark:bg-primary-900/20 px-2 py-0.5 text-xs font-medium text-primary-800 dark:text-primary-300">
                            {post.platform || 'LinkedIn'}
                          </span>
                          {post.templateId && (
                            <span className="inline-flex items-center rounded-full bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-800 dark:text-neutral-300">
                              T{post.templateId}
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-neutral-500 dark:text-neutral-400">{post.wordCount}w</span>
                      </div>
                      <p className="line-clamp-6 text-sm text-neutral-900 dark:text-neutral-100">{post.content}</p>
                      <div className="mt-4 flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700 pt-3">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                          <span className="text-xs text-neutral-600 dark:text-neutral-400">Quality: 92%</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
                            <Eye className="inline h-3 w-3" /> View
                          </button>
                          <button className="text-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100">
                            <RefreshCw className="inline h-3 w-3" /> Regen
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
                    <thead className="bg-neutral-50 dark:bg-neutral-800">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                          <input type="checkbox" className="rounded" />
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                          Post Excerpt
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                          Platform
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                          Template
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                          Words
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                          Quality
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700 bg-white dark:bg-neutral-900">
                      {filteredPosts.map((post) => (
                        <tr key={post.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800">
                          <td className="whitespace-nowrap px-6 py-4">
                            <input type="checkbox" className="rounded" />
                          </td>
                          <td className="px-6 py-4">
                            <p className="line-clamp-2 max-w-md text-sm text-neutral-900 dark:text-neutral-100">
                              {post.content.substring(0, 150)}...
                            </p>
                          </td>
                          <td className="whitespace-nowrap px-6 py-4">
                            <span className="inline-flex items-center rounded-full bg-primary-100 dark:bg-primary-900/20 px-2.5 py-0.5 text-xs font-medium text-primary-800 dark:text-primary-300">
                              {post.platform || 'LinkedIn'}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-900 dark:text-neutral-100">
                            {post.templateId ? `T${post.templateId}` : '-'}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-900 dark:text-neutral-100">
                            {post.wordCount}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4">
                            <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400">92%</span>
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                            <button className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">View</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Quality Report */}
        {activeTab === 'quality' && (
          <div className="space-y-6">
            {/* Overall Score Card */}
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Overall Quality Score</h3>
                  <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">Aggregated score across all validators</p>
                </div>
                <div className="text-right">
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold text-emerald-600 dark:text-emerald-400">{qualityScore}%</span>
                    <TrendingUp className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <p className="mt-1 text-sm text-emerald-600 dark:text-emerald-400">+3% from last project</p>
                </div>
              </div>
            </div>

            {/* Validation Results */}
            <div className="grid gap-6 md:grid-cols-2">
              {/* Hook Uniqueness */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-neutral-900 dark:text-neutral-100">Hook Uniqueness</h4>
                  <span className="flex items-center gap-1 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                    Pass
                  </span>
                </div>
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-neutral-600 dark:text-neutral-400">Score</span>
                    <span className="font-semibold text-neutral-900 dark:text-neutral-100">{hookScore}%</span>
                  </div>
                  <div className="mt-2 h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-700">
                    <div
                      className="h-2 rounded-full bg-emerald-600 dark:bg-emerald-500"
                      style={{ width: `${hookScore}%` }}
                    />
                  </div>
                </div>
                <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-400">
                  28 of 30 posts have unique opening hooks (93% uniqueness)
                </p>
              </div>

              {/* CTA Variety */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-neutral-900 dark:text-neutral-100">CTA Variety</h4>
                  <span className="flex items-center gap-1 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                    Pass
                  </span>
                </div>
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-neutral-600 dark:text-neutral-400">Score</span>
                    <span className="font-semibold text-neutral-900 dark:text-neutral-100">{ctaScore}%</span>
                  </div>
                  <div className="mt-2 h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-700">
                    <div
                      className="h-2 rounded-full bg-emerald-600 dark:bg-emerald-500"
                      style={{ width: `${ctaScore}%` }}
                    />
                  </div>
                </div>
                <div className="mt-3 space-y-1 text-sm text-neutral-600 dark:text-neutral-400">
                  <div className="flex items-center justify-between">
                    <span>Questions</span>
                    <span className="font-medium">45%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Engagement</span>
                    <span className="font-medium">35%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Direct</span>
                    <span className="font-medium">20%</span>
                  </div>
                </div>
              </div>

              {/* Post Length */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-neutral-900 dark:text-neutral-100">Post Length</h4>
                  <span className="flex items-center gap-1 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                    Pass
                  </span>
                </div>
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-neutral-600 dark:text-neutral-400">Score</span>
                    <span className="font-semibold text-neutral-900 dark:text-neutral-100">{lengthScore}%</span>
                  </div>
                  <div className="mt-2 h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-700">
                    <div
                      className="h-2 rounded-full bg-emerald-600 dark:bg-emerald-500"
                      style={{ width: `${lengthScore}%` }}
                    />
                  </div>
                </div>
                <div className="mt-3 space-y-1 text-sm text-neutral-600 dark:text-neutral-400">
                  <div className="flex items-center justify-between">
                    <span>Average Length</span>
                    <span className="font-medium">215 words</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Optimal Range</span>
                    <span className="font-medium">26 of 30</span>
                  </div>
                </div>
              </div>

              {/* Headline Engagement */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-neutral-900 dark:text-neutral-100">Headline Engagement</h4>
                  <span className="flex items-center gap-1 text-sm font-medium text-amber-600 dark:text-amber-400">
                    <AlertCircle className="h-4 w-4" />
                    Review
                  </span>
                </div>
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-neutral-600 dark:text-neutral-400">Score</span>
                    <span className="font-semibold text-neutral-900 dark:text-neutral-100">{headlineScore}%</span>
                  </div>
                  <div className="mt-2 h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-700">
                    <div
                      className="h-2 rounded-full bg-amber-500 dark:bg-amber-600"
                      style={{ width: `${headlineScore}%` }}
                    />
                  </div>
                </div>
                <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-400">
                  4 posts have weak headlines (below 3 engagement elements)
                </p>
              </div>
            </div>

            {/* Flagged Posts */}
            <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-6">
              <h4 className="flex items-center gap-2 font-semibold text-amber-900 dark:text-amber-300">
                <Flag className="h-5 w-5" />
                Flagged Posts (4)
              </h4>
              <div className="mt-4 space-y-2">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 p-3">
                    <div>
                      <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Post #{i} - Weak headline</p>
                      <p className="text-xs text-neutral-600 dark:text-neutral-400">Only 2 engagement elements detected</p>
                    </div>
                    <button className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
                      View & Fix
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Export Button */}
            <div className="flex justify-end">
              <button className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600">
                <Download className="h-4 w-4" />
                Export QA Report
              </button>
            </div>
          </div>
        )}

        {/* Tab 4: Deliverables */}
        {activeTab === 'deliverables' && (
          <div className="space-y-4">
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
                  <thead className="bg-neutral-50 dark:bg-neutral-800">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        File Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Format
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Size
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Status
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700 bg-white dark:bg-neutral-900">
                    {mockDeliverableFiles.map((file, index) => (
                      <tr key={index} className="hover:bg-neutral-50 dark:hover:bg-neutral-800">
                        <td className="whitespace-nowrap px-6 py-4">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-neutral-400 dark:text-neutral-600" />
                            <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{file.name}</span>
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span className="inline-flex items-center rounded-full bg-neutral-100 dark:bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-neutral-800 dark:text-neutral-300">
                            {file.format}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-600 dark:text-neutral-400">
                          {file.size}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span
                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                              file.status === 'delivered'
                                ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300'
                                : 'bg-primary-100 dark:bg-primary-900/20 text-primary-800 dark:text-primary-300'
                            }`}
                          >
                            {file.status}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-3">
                            <button className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
                              <Download className="inline h-4 w-4" />
                            </button>
                            {file.status === 'generated' && (
                              <button className="text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100">
                                Send to Client
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Revisions */}
        {activeTab === 'revisions' && (
          <div className="space-y-6">
            {/* Revision Counter */}
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Revision Status</h3>
                  <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                    {mockRevisions.length} of 5 revisions used
                  </p>
                </div>
                <button className="rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600">
                  Request New Revision
                </button>
              </div>
              <div className="mt-4 h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-700">
                <div
                  className="h-2 rounded-full bg-primary-600 dark:bg-primary-500"
                  style={{ width: `${(mockRevisions.length / 5) * 100}%` }}
                />
              </div>
            </div>

            {/* Revision History */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Revision History</h3>
              {mockRevisions.map((revision, index) => (
                <div key={revision.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/20 text-sm font-semibold text-primary-600 dark:text-primary-400">
                        R{index + 1}
                      </div>
                      <div>
                        <h4 className="font-semibold text-neutral-900 dark:text-neutral-100">Revision {index + 1}</h4>
                        <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{revision.changes}</p>
                        <div className="mt-2 flex items-center gap-4 text-xs text-neutral-500 dark:text-neutral-400">
                          <span>Requested by: {revision.requestedBy}</span>
                          <span>•</span>
                          <span>{format(new Date(revision.date), 'MMM d, yyyy')}</span>
                          <span>•</span>
                          <span>{revision.posts} posts affected</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
                        View Changes
                      </button>
                      <button className="text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100">
                        Rollback
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 6: Activity Log */}
        {activeTab === 'activity' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Project Activity</h3>
              <button className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
                <Download className="h-4 w-4" />
                Export Log
              </button>
            </div>

            <div className="space-y-3">
              {mockActivityLog.map((activity) => {
                const activityTimestamp = activity.timestamp ?? project.createdAt ?? new Date().toISOString();
                return (
                <div key={activity.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
                  <div className="flex items-start gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/20">
                      <Clock className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-neutral-900 dark:text-neutral-100">{activity.action}</p>
                          {activity.details && (
                            <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{activity.details}</p>
                          )}
                        </div>
                        <span className="text-sm text-neutral-500 dark:text-neutral-400">
                          {formatDistanceToNow(new Date(activityTimestamp), { addSuffix: true })}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">By: {activity.user}</p>
                    </div>
                  </div>
                </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
