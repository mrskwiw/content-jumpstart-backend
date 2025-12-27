import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ArrowLeft,
  Mail,
  Plus,
  Archive,
  Edit,
  Building2,
  Phone,
  Globe,
  User,
  FileText,
  DollarSign,
  MessageSquare,
  CheckCircle2,
  Clock,
  Download,
  ExternalLink,
  Calendar,
  Eye,
  FlaskConical,
  Loader2,
  X,
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { postsApi } from '@/api/posts';
import { deliverablesApi } from '@/api/deliverables';
import { researchApi } from '@/api/research';
import { CopyButton } from '@/components/ui/CopyButton';
import type { Project, PostDraft, Deliverable } from '@/types/domain';
import type { PaginatedResponse } from '@/types/pagination';

type TabType = 'overview' | 'projects' | 'research' | 'content' | 'deliverables' | 'billing' | 'communication';

export default function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [notes, setNotes] = useState('');

  // Research tool state
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [showDataDialog, setShowDataDialog] = useState(false);
  const [researchResults, setResearchResults] = useState<Map<string, any>>(new Map());

  // Fetch client data
  const { data: client, isLoading: clientLoading } = useQuery({
    queryKey: ['client', clientId],
    queryFn: () => clientsApi.get(clientId!),
    enabled: !!clientId,
  });

  // Fetch client projects
  const { data: projectsResponse } = useQuery<PaginatedResponse<Project>>({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  });

  // Fetch all posts
  const { data: postsResponse } = useQuery<PaginatedResponse<PostDraft>>({
    queryKey: ['posts'],
    queryFn: () => postsApi.list(),
  });

  // Fetch deliverables
  const { data: deliverablesResponse } = useQuery<Deliverable[]>({
    queryKey: ['deliverables'],
    queryFn: () => deliverablesApi.list(),
  });

  const projects: Project[] = projectsResponse?.items ?? [];
  const posts: PostDraft[] = postsResponse?.items ?? [];
  const deliverables: Deliverable[] = deliverablesResponse ?? [];

  // Research tool mutation
  const runResearchMutation = useMutation({
    mutationFn: ({ tool, params }: { tool: string; params?: Record<string, any> }) => {
      // Create a dummy project for client research (research not tied to specific project)
      const dummyProjectId = `client-research-${clientId}`;
      return researchApi.run({
        projectId: dummyProjectId,
        clientId: clientId!,
        tool,
        params: params || {},
      });
    },
    onSuccess: (data, variables) => {
      setResearchResults(new Map(researchResults).set(variables.tool, data));
      setSelectedTool(null);
      setShowDataDialog(false);
    },
    onError: (error, variables) => {
      console.error(`Research tool "${variables.tool}" failed:`, error);
      alert(`Failed to run research tool "${variables.tool}": ${error instanceof Error ? error.message : 'Unknown error'}`);
    },
  });

  // Handler for clicking a research tool button
  const handleRunResearchTool = (toolName: string) => {
    setSelectedTool(toolName);

    // For now, run tools without additional data collection
    // TODO: Add data collection dialog for tools that need it (voice_analysis, competitive_analysis, etc.)
    runResearchMutation.mutate({ tool: toolName, params: {} });
  };

  if (clientLoading || !client) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 dark:border-primary-500 border-r-transparent"></div>
          <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">Loading client...</p>
        </div>
      </div>
    );
  }

  // Filter data for this client
  const clientProjects = projects.filter((p) => p.clientId === client.id);
  const clientPosts = posts.filter((post) =>
    clientProjects.some((project) => project.id === post.projectId)
  );
  const clientDeliverables = deliverables.filter((d) =>
    clientProjects.some((project) => project.id === d.projectId)
  );

  // Calculate metrics
  const totalProjects = clientProjects.length;
  const activeProjects = clientProjects.filter(
    (p) => p.status !== 'delivered' && p.status !== 'exported'
  ).length;
  const completedProjects = clientProjects.filter(
    (p) => p.status === 'delivered' || p.status === 'exported'
  ).length;
  const totalRevenue = completedProjects * 1800; // Mock calculation
  const packageTier = completedProjects > 5 ? 'Premium' : completedProjects > 2 ? 'Professional' : 'Starter';

  // Mock data for tabs (would come from API)
  const mockInvoices = [
    { id: '1', date: '2024-01-15', amount: 1800, status: 'paid', project: clientProjects[0]?.name || 'Project 1' },
    { id: '2', date: '2024-02-01', amount: 1800, status: 'pending', project: clientProjects[1]?.name || 'Project 2' },
  ];

  const mockCommunications = [
    { id: '1', type: 'email', subject: 'Project kickoff meeting', date: '2024-01-10', from: 'operator@company.com' },
    { id: '2', type: 'call', subject: 'Revision discussion', date: '2024-01-20', duration: '15 min' },
    { id: '3', type: 'email', subject: 'Deliverable sent', date: '2024-02-05', from: 'operator@company.com' },
  ];

  const tabs: {
    id: TabType;
    label: string;
    icon: typeof User;
    count?: number;
  }[] = [
    { id: 'overview', label: 'Overview', icon: User },
    { id: 'projects', label: 'Projects', icon: FileText, count: totalProjects },
    { id: 'research', label: 'Research', icon: FlaskConical },
    { id: 'content', label: 'Content', icon: MessageSquare, count: clientPosts.length },
    { id: 'deliverables', label: 'Deliverables', icon: Download, count: clientDeliverables.length },
    { id: 'billing', label: 'Billing', icon: DollarSign },
    { id: 'communication', label: 'Communication', icon: Mail },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/dashboard/clients')}
            className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Clients
          </button>
        </div>
      </div>

      {/* Client Header Card */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            {/* Avatar */}
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-600 dark:bg-primary-500 text-2xl font-semibold text-white">
              {client.name.charAt(0).toUpperCase()}
            </div>

            {/* Client Info */}
            <div>
              <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{client.name}</h1>
              <div className="mt-2 flex items-center gap-3">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    client.status === 'active'
                      ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300'
                      : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-300'
                  }`}
                >
                  {client.status || 'active'}
                </span>
                <span className="inline-flex items-center rounded-full bg-primary-100 dark:bg-primary-900/20 px-2.5 py-0.5 text-xs font-medium text-primary-800 dark:text-primary-300">
                  {packageTier}
                </span>
                <span className="text-sm text-neutral-600 dark:text-neutral-400">
                  ${totalRevenue.toLocaleString()} total revenue
                </span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <button className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
              <Edit className="h-4 w-4" />
              Edit
            </button>
            <button className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
              <Mail className="h-4 w-4" />
              Send Email
            </button>
            <button
              onClick={() => navigate('/dashboard/wizard', { state: { clientId: client.id, clientName: client.name } })}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
            >
              <Plus className="h-4 w-4" />
              New Project
            </button>
            <button className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
              <Archive className="h-4 w-4" />
              Archive
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-6 grid grid-cols-4 gap-6 border-t border-neutral-200 dark:border-neutral-700 pt-6">
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Total Projects</p>
            <p className="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{totalProjects}</p>
          </div>
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Active Projects</p>
            <p className="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{activeProjects}</p>
          </div>
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Posts Generated</p>
            <p className="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{clientPosts.length}</p>
          </div>
          <div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Deliverables</p>
            <p className="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{clientDeliverables.length}</p>
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
                        ? 'bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-300'
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
              {/* Contact Information */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  <User className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                  Contact Information
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Company Name</p>
                    <p className="mt-1 font-medium text-neutral-900 dark:text-neutral-100">{client.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Email</p>
                    <p className="mt-1 font-medium text-neutral-900 dark:text-neutral-100">
                      {client.tags?.find(t => t.includes('@')) || 'contact@example.com'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Phone</p>
                    <p className="mt-1 font-medium text-neutral-900 dark:text-neutral-100">+1 (555) 123-4567</p>
                  </div>
                </div>
              </div>

              {/* Business Details */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  <Building2 className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                  Business Details
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Industry</p>
                    <p className="mt-1 font-medium text-neutral-900 dark:text-neutral-100">Technology / SaaS</p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Company Size</p>
                    <p className="mt-1 font-medium text-neutral-900 dark:text-neutral-100">50-100 employees</p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Website</p>
                    <a
                      href={`https://${client.name.toLowerCase().replace(/\s+/g, '')}.com`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-flex items-center gap-1 font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                    >
                      <Globe className="h-4 w-4" />
                      Visit website
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
              </div>

              {/* Package Details */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  <FileText className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                  Package Details
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Current Tier</p>
                    <p className="mt-1">
                      <span className="inline-flex items-center rounded-full bg-primary-100 dark:bg-primary-900/20 px-3 py-1 text-sm font-medium text-primary-800 dark:text-primary-300">
                        {packageTier}
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Pricing</p>
                    <p className="mt-1 font-medium text-neutral-900 dark:text-neutral-100">
                      ${packageTier === 'Premium' ? '2,500' : packageTier === 'Professional' ? '1,800' : '1,200'} per project
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Features</p>
                    <ul className="mt-1 space-y-1 text-sm text-neutral-700 dark:text-neutral-300">
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                        30 posts per project
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                        Multi-platform support
                      </li>
                      {packageTier !== 'Starter' && (
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                          Priority support
                        </li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Account Manager */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  <User className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                  Account Manager
                </h3>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-600 dark:bg-purple-500 text-sm font-semibold text-white">
                    SM
                  </div>
                  <div>
                    <p className="font-medium text-neutral-900 dark:text-neutral-100">Sarah Martinez</p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">sarah@company.com</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Custom Notes */}
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
              <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                <MessageSquare className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                Custom Notes
              </h3>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes about this client..."
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 p-3 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
                rows={6}
              />
              <div className="mt-3 flex justify-end">
                <button className="rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600">
                  Save Notes
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Projects */}
        {activeTab === 'projects' && (
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
                <thead className="bg-neutral-50 dark:bg-neutral-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                      Project Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                      Posts
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                      Created
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
                  {clientProjects.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center">
                        <p className="text-sm text-neutral-600 dark:text-neutral-400">No projects yet</p>
                        <button
                          onClick={() => navigate('/dashboard/wizard', { state: { clientId: client.id, clientName: client.name } })}
                          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
                        >
                          <Plus className="h-4 w-4" />
                          Create First Project
                        </button>
                      </td>
                    </tr>
                  ) : (
                    clientProjects
                      .sort(
                        (a, b) =>
                          new Date(b.createdAt ?? 0).getTime() - new Date(a.createdAt ?? 0).getTime()
                      )
                      .map((project) => {
                        const statusColors: Record<Project['status'], string> = {
                          draft: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-300',
                          generating: 'bg-primary-100 dark:bg-primary-900/20 text-primary-800 dark:text-primary-300',
                          qa: 'bg-amber-100 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300',
                          ready: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300',
                          exported: 'bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-300',
                          delivered: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300',
                          error: 'bg-rose-100 dark:bg-rose-900/20 text-rose-800 dark:text-rose-300',
                        };

                        const projectPostCount = clientPosts.filter(
                          (post) => post.projectId === project.id
                        ).length;

                        return (
                          <tr key={project.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800">
                            <td className="whitespace-nowrap px-6 py-4">
                              <button
                                onClick={() => navigate(`/dashboard/projects/${project.id}`)}
                                className="font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                              >
                                {project.name}
                              </button>
                            </td>
                            <td className="whitespace-nowrap px-6 py-4">
                              <span
                                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                  statusColors[project.status] || 'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-300'
                                }`}
                              >
                                {project.status}
                              </span>
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-900 dark:text-neutral-100">
                              {projectPostCount}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-600 dark:text-neutral-400">
                              {project.createdAt ? format(new Date(project.createdAt), 'MMM d, yyyy') : 'N/A'}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-900 dark:text-neutral-100">
                              <span className="font-medium text-emerald-600 dark:text-emerald-400">92%</span>
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                              <button
                                onClick={() => navigate(`/dashboard/projects/${project.id}`)}
                                className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                              >
                                View
                              </button>
                            </td>
                          </tr>
                        );
                      })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Research Tools */}
        {activeTab === 'research' && (
          <div className="space-y-6">
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Client Research Tools</h3>
                <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                  Gather intelligence about this client before starting projects. Research results are stored with the client profile.
                </p>
              </div>

              {/* Research Tools Grid */}
              <div className="grid gap-4 md:grid-cols-2">
                {/* Voice Analysis */}
                <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-4">
                  <h4 className="flex items-center gap-2 font-medium text-neutral-900 dark:text-neutral-100">
                    <MessageSquare className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                    Voice Analysis
                  </h4>
                  <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                    Analyze brand voice from existing content samples. Determines tone, readability, and voice dimensions.
                  </p>
                  <button
                    onClick={() => handleRunResearchTool('voice_analysis')}
                    disabled={runResearchMutation.isPending && selectedTool === 'voice_analysis'}
                    className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {runResearchMutation.isPending && selectedTool === 'voice_analysis' ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Running...
                      </>
                    ) : (
                      'Run Voice Analysis'
                    )}
                  </button>
                </div>

                {/* Brand Archetype */}
                <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-4">
                  <h4 className="flex items-center gap-2 font-medium text-neutral-900 dark:text-neutral-100">
                    <User className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                    Brand Archetype
                  </h4>
                  <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                    Identify brand personality type (Expert, Friend, Innovator, etc.) to guide content creation.
                  </p>
                  <button
                    onClick={() => handleRunResearchTool('brand_archetype')}
                    disabled={runResearchMutation.isPending && selectedTool === 'brand_archetype'}
                    className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {runResearchMutation.isPending && selectedTool === 'brand_archetype' ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Running...
                      </>
                    ) : (
                      'Identify Archetype'
                    )}
                  </button>
                </div>

                {/* Competitive Analysis */}
                <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-4">
                  <h4 className="flex items-center gap-2 font-medium text-neutral-900 dark:text-neutral-100">
                    <Building2 className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                    Competitive Analysis
                  </h4>
                  <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                    Analyze competitors' content strategies and positioning to find differentiation opportunities.
                  </p>
                  <button
                    onClick={() => handleRunResearchTool('competitive_analysis')}
                    disabled={runResearchMutation.isPending && selectedTool === 'competitive_analysis'}
                    className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {runResearchMutation.isPending && selectedTool === 'competitive_analysis' ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Running...
                      </>
                    ) : (
                      'Analyze Competitors'
                    )}
                  </button>
                </div>

                {/* Market Trends */}
                <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-4">
                  <h4 className="flex items-center gap-2 font-medium text-neutral-900 dark:text-neutral-100">
                    <Globe className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                    Market Trends
                  </h4>
                  <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                    Research current industry trends and topics to inform content strategy.
                  </p>
                  <button
                    onClick={() => handleRunResearchTool('market_trends_research')}
                    disabled={runResearchMutation.isPending && selectedTool === 'market_trends_research'}
                    className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {runResearchMutation.isPending && selectedTool === 'market_trends_research' ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Running...
                      </>
                    ) : (
                      'Research Trends'
                    )}
                  </button>
                </div>
              </div>

              {/* Research History */}
              <div className="mt-6 border-t border-neutral-200 dark:border-neutral-700 pt-6">
                <h4 className="mb-4 font-medium text-neutral-900 dark:text-neutral-100">Research History</h4>
                {researchResults.size === 0 ? (
                  <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-8 text-center">
                    <FlaskConical className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-500" />
                    <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">
                      No research has been run for this client yet.
                    </p>
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                      Run a tool above to start gathering client intelligence.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Array.from(researchResults.entries()).map(([toolName, result]) => (
                      <div
                        key={toolName}
                        className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <FlaskConical className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                              <h5 className="font-medium text-neutral-900 dark:text-neutral-100">
                                {toolName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                              </h5>
                              <span className="inline-flex items-center rounded-full bg-emerald-100 dark:bg-emerald-900/20 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:text-emerald-300">
                                <CheckCircle2 className="mr-1 h-3 w-3" />
                                Completed
                              </span>
                            </div>
                            {result.metadata && (
                              <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400">
                                {new Date(result.metadata.executed_at).toLocaleString()}
                              </p>
                            )}
                            {result.outputs && Object.keys(result.outputs).length > 0 && (
                              <div className="mt-3 space-y-1">
                                <p className="text-xs font-medium text-neutral-700 dark:text-neutral-300">Outputs:</p>
                                {Object.entries(result.outputs).map(([format, path]) => (
                                  <div key={format} className="flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-400">
                                    <span className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded">
                                      {format.toUpperCase()}
                                    </span>
                                    <span className="flex-1 truncate">{path as string}</span>
                                    <CopyButton
                                      text={path as string}
                                      size="sm"
                                    />
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Content */}
        {activeTab === 'content' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex items-center gap-4 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
              <input
                type="search"
                placeholder="Search posts..."
                className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
              />
              <select className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400">
                <option value="">All Projects</option>
                {clientProjects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <select className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400">
                <option value="">All Platforms</option>
                <option value="linkedin">LinkedIn</option>
                <option value="twitter">Twitter</option>
                <option value="facebook">Facebook</option>
              </select>
            </div>

            {/* Posts Grid */}
            <div className="grid gap-4 md:grid-cols-2">
              {clientPosts.length === 0 ? (
                <div className="col-span-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-12 text-center">
                  <MessageSquare className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-500" />
                  <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">No content generated yet</p>
                </div>
              ) : (
                clientPosts.slice(0, 20).map((post) => (
                  <div key={post.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4 hover:shadow-md">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs text-neutral-600 dark:text-neutral-400">
                        {projects.find((p) => p.id === post.projectId)?.name}
                      </span>
                      <span className="text-xs text-neutral-500 dark:text-neutral-400">
                        {(post as { wordCount?: number }).wordCount ?? (post.content?.split(' ').length ?? 0)} words
                      </span>
                    </div>
                    <p className="line-clamp-4 text-sm text-neutral-900 dark:text-neutral-100">{post.content}</p>
                    <div className="mt-3 flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700 pt-3">
                      <span className="inline-flex items-center rounded-full bg-primary-100 dark:bg-primary-900/20 px-2 py-0.5 text-xs font-medium text-primary-800 dark:text-primary-300">
                        LinkedIn
                      </span>
                      <button className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">View Full</button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {clientPosts.length > 20 && (
              <div className="text-center">
                <button className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
                  Load More ({clientPosts.length - 20} more posts)
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Deliverables */}
        {activeTab === 'deliverables' && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <button
                onClick={() => navigate(`/dashboard/deliverables?clientId=${client.id}`)}
                className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700"
              >
                <ExternalLink className="h-4 w-4" />
                View All Deliverables
              </button>
            </div>
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
                  <thead className="bg-neutral-50 dark:bg-neutral-800">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Project
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Format
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Delivered
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Actions
                      </th>
                    </tr>
                  </thead>
                <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700 bg-white dark:bg-neutral-900">
                  {clientDeliverables.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-12 text-center">
                        <Download className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-500" />
                        <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">No deliverables yet</p>
                      </td>
                    </tr>
                  ) : (
                    clientDeliverables.map((deliverable) => (
                      <tr key={deliverable.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800">
                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                          {projects.find((p) => p.id === deliverable.projectId)?.name}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span className="inline-flex items-center rounded-full bg-neutral-100 dark:bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-neutral-800 dark:text-neutral-300">
                            {deliverable.format?.toUpperCase() || 'TXT'}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span
                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                              deliverable.status === 'delivered'
                                ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300'
                                : deliverable.status === 'ready'
                                ? 'bg-primary-100 dark:bg-primary-900/20 text-primary-800 dark:text-primary-300'
                                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-300'
                            }`}
                          >
                            {deliverable.status}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-600 dark:text-neutral-400">
                          {deliverable.deliveredAt
                            ? format(new Date(deliverable.deliveredAt), 'MMM d, yyyy')
                            : '-'}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                          <div className="flex items-center justify-end gap-3">
                            <button
                              onClick={() => navigate(`/dashboard/content-review?projectId=${deliverable.projectId}`)}
                              className="inline-flex items-center gap-1 text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                              title="Review in QA"
                            >
                              <Eye className="h-4 w-4" />
                              <span className="text-xs">Review</span>
                            </button>
                            <button
                              className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                              title="Download deliverable"
                            >
                              <Download className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        )}

        {/* Tab 5: Billing & Payments */}
        {activeTab === 'billing' && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <p className="text-sm text-neutral-600 dark:text-neutral-400">Total Revenue</p>
                <p className="mt-2 text-3xl font-semibold text-neutral-900 dark:text-neutral-100">
                  ${totalRevenue.toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <p className="text-sm text-neutral-600 dark:text-neutral-400">Outstanding</p>
                <p className="mt-2 text-3xl font-semibold text-amber-600 dark:text-amber-400">
                  ${mockInvoices.filter(i => i.status === 'pending').reduce((sum, i) => sum + i.amount, 0).toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <p className="text-sm text-neutral-600 dark:text-neutral-400">Paid This Month</p>
                <p className="mt-2 text-3xl font-semibold text-emerald-600 dark:text-emerald-400">
                  ${mockInvoices.filter(i => i.status === 'paid').reduce((sum, i) => sum + i.amount, 0).toLocaleString()}
                </p>
              </div>
            </div>

            {/* Invoices Table */}
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
              <div className="border-b border-neutral-200 dark:border-neutral-700 px-6 py-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Invoices</h3>
                  <button className="rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600">
                    Generate Invoice
                  </button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
                  <thead className="bg-neutral-50 dark:bg-neutral-800">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Invoice #
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Project
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Date
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                        Amount
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
                    {mockInvoices.map((invoice) => (
                      <tr key={invoice.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800">
                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                          INV-{invoice.id.padStart(4, '0')}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-900 dark:text-neutral-100">
                          {invoice.project}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-600 dark:text-neutral-400">
                          {format(new Date(invoice.date), 'MMM d, yyyy')}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                          ${invoice.amount.toLocaleString()}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span
                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                              invoice.status === 'paid'
                                ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300'
                                : 'bg-amber-100 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300'
                            }`}
                          >
                            {invoice.status}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                          <button className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">View PDF</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab 6: Communication History */}
        {activeTab === 'communication' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Communication Log</h3>
              <button className="rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600">
                New Communication
              </button>
            </div>

            {/* Communication Timeline */}
            <div className="space-y-4">
              {mockCommunications.map((comm, index) => (
                <div key={comm.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                  <div className="flex items-start gap-4">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-full ${
                        comm.type === 'email' ? 'bg-primary-100 dark:bg-primary-900/20' : 'bg-emerald-100 dark:bg-emerald-900/20'
                      }`}
                    >
                      {comm.type === 'email' ? (
                        <Mail className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                      ) : (
                        <Phone className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-neutral-900 dark:text-neutral-100">{comm.subject}</p>
                          <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                            {comm.type === 'email' ? `From: ${comm.from}` : `Duration: ${comm.duration}`}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
                          <Calendar className="h-4 w-4" />
                          {format(new Date(comm.date), 'MMM d, yyyy')}
                        </div>
                      </div>
                      {comm.type === 'email' && (
                        <button className="mt-3 text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
                          View Email Thread →
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {mockCommunications.length === 0 && (
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-12 text-center">
                <MessageSquare className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-500" />
                <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">No communication history</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
