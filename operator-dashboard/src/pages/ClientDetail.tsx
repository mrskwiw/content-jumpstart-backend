import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ROUTES } from '@/config/routes';
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
  Download,
  ExternalLink,
  Calendar,
  Eye,
  FlaskConical,
  Loader2,
  X,
  BookOpen,
  Trash2,
  TrendingUp,
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { clientsApi, type UpdateClientInput } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { postsApi } from '@/api/posts';
import { deliverablesApi } from '@/api/deliverables';
import { researchApi } from '@/api/research';
import { storiesApi, type Story } from '@/api/stories';
import { communicationsApi, type Communication, type CreateCommunicationInput } from '@/api/communications';
import { ResearchResultsDrawer } from '@/components/research/ResearchResultsDrawer';
import { StoryDetailsDrawer } from '@/components/stories/StoryDetailsDrawer';
import { AddStoryDialog } from '@/components/stories/AddStoryDialog';
import { EditClientDialog } from '@/components/clients/EditClientDialog';
import { DeleteClientDialog } from '@/components/DeleteClientDialog';
import { SendEmailDialog } from '@/components/clients/SendEmailDialog';
import { NewCommunicationDialog } from '@/components/clients/NewCommunicationDialog';
import type { Project, PostDraft, Deliverable, ResearchResult } from '@/types/domain';
import type { PaginatedResponse } from '@/types/pagination';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { getApiErrorMessage } from '@/utils/apiError';

type TabType = 'overview' | 'projects' | 'research' | 'stories' | 'content' | 'deliverables' | 'billing' | 'communication';

export default function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [notes, setNotes] = useState('');

  // Research tool state
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [showDataDialog, setShowDataDialog] = useState(false);
  const [researchResults, setResearchResults] = useState<Map<string, unknown>>(new Map());
  const [isExporting, setIsExporting] = useState(false);
  const [visiblePostCount, setVisiblePostCount] = useState(20);

  // Research results drawer state
  const [selectedResult, setSelectedResult] = useState<ResearchResult | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Story drawer state
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [storyDrawerOpen, setStoryDrawerOpen] = useState(false);

  // Add story dialog state
  const [addStoryDialogOpen, setAddStoryDialogOpen] = useState(false);
  // Edit client dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  // Delete client dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  // Send email dialog state
  const [sendEmailDialogOpen, setSendEmailDialogOpen] = useState(false);
  // New communication dialog state
  const [newCommDialogOpen, setNewCommDialogOpen] = useState(false);
  // Communication type filter
  const [commTypeFilter, setCommTypeFilter] = useState<string>('all');

  // Data collection dialog state
  const [dialogInputValue, setDialogInputValue] = useState('');
  const [dialogInputLabel, setDialogInputLabel] = useState('');
  const [dialogInputPlaceholder, setDialogInputPlaceholder] = useState('');

  // Tools that require input data
  const toolsNeedingInput: Record<string, { label: string; placeholder: string; paramKey: string }> = {
    voice_analysis: {
      label: 'Content Samples',
      placeholder: 'Paste 2-3 existing content samples (blog posts, LinkedIn posts, etc.) separated by ---',
      paramKey: 'content_samples',
    },
    competitive_analysis: {
      label: 'Competitor Names/URLs',
      placeholder: 'Enter competitor company names or website URLs (one per line)',
      paramKey: 'competitors',
    },
  };

  // Fetch client data
  const { data: client, isLoading: clientLoading, isError: clientError, refetch: refetchClient } = useQuery({
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
    queryFn: () => postsApi.list({ page_size: 500 }),
    staleTime: 0,
    gcTime: 0, // Disable caching entirely
  });

  // Fetch deliverables
  const { data: deliverablesResponse } = useQuery<Deliverable[]>({
    queryKey: ['deliverables'],
    queryFn: () => deliverablesApi.list(),
  });

  // Fetch research history
  const {
    data: researchData,
    isLoading: isLoadingResearch,
    refetch: refetchResearch
  } = useQuery({
    queryKey: ['research-results', clientId],
    queryFn: () => researchApi.getClientResearchResults(clientId!),
    enabled: !!clientId,
  });

  // Fetch client stories
  const {
    data: storiesData,
    isLoading: isLoadingStories,
    refetch: refetchStories
  } = useQuery({
    queryKey: ['client-stories', clientId],
    queryFn: () => storiesApi.listClientStories(clientId!),
    enabled: !!clientId,
  });

  // Story deletion mutation
  const deleteStoryMutation = useMutation({
    mutationFn: (storyId: string) => storiesApi.delete(storyId),
    onSuccess: () => {
      refetchStories();
    },
    onError: (error) => {
      alert(`Failed to delete story: ${getApiErrorMessage(error)}`);
    },
  });

  // Story creation mutation
  const createStoryMutation = useMutation({
    mutationFn: storiesApi.create,
    onSuccess: () => {
      refetchStories();
      setAddStoryDialogOpen(false);
    },
    onError: (error) => {
      alert(`Failed to create story: ${getApiErrorMessage(error)}`);
    },
  });

  // Update client mutation
  const updateClientMutation = useMutation({
    mutationFn: (updates: UpdateClientInput) => clientsApi.update(clientId!, updates),
    onSuccess: () => {
      refetchClient();
      setEditDialogOpen(false);
    },
    onError: (error) => {
      alert(`Failed to update client: ${getApiErrorMessage(error)}`);
    },
  });

  // Delete client mutation (kept for backward compat — dialog now uses archive for soft delete)
  const deleteClientMutation = useMutation({
    mutationFn: () => clientsApi.delete(clientId!),
    onSuccess: () => {
      navigate(ROUTES.CLIENTS);
    },
    onError: (error) => {
      alert(`Failed to delete client: ${getApiErrorMessage(error)}`);
    },
  });

  // Permanent (hard) delete — GDPR right-to-erasure, force=true cascades all child records
  const permanentDeleteMutation = useMutation({
    mutationFn: () => clientsApi.permanentDelete(clientId!),
    onSuccess: () => {
      navigate(ROUTES.CLIENTS);
    },
    onError: (error) => {
      alert(`Permanent deletion failed: ${getApiErrorMessage(error)}`);
    },
  });

  // Archive client mutation
  const archiveClientMutation = useMutation({
    mutationFn: () => clientsApi.archive(clientId!),
    onSuccess: () => {
      navigate(ROUTES.CLIENTS);
    },
    onError: (error) => {
      alert(`Failed to archive client: ${getApiErrorMessage(error)}`);
    },
  });

  // Fetch client communications
  const {
    data: communicationsData,
    isLoading: isLoadingCommunications,
    refetch: refetchCommunications,
  } = useQuery<Communication[]>({
    queryKey: ['client-communications', clientId],
    queryFn: () => communicationsApi.listClientCommunications(clientId!),
    enabled: !!clientId,
  });

  // Create communication mutation
  const createCommunicationMutation = useMutation({
    mutationFn: (input: CreateCommunicationInput) => communicationsApi.create(input),
    onSuccess: () => {
      refetchCommunications();
      setNewCommDialogOpen(false);
    },
    onError: (error) => {
      alert(`Failed to log communication: ${getApiErrorMessage(error)}`);
    },
  });

  // Delete communication mutation
  const deleteCommunicationMutation = useMutation({
    mutationFn: (commId: number) => communicationsApi.delete(commId),
    onSuccess: () => {
      refetchCommunications();
    },
    onError: (error) => {
      alert(`Failed to delete communication: ${getApiErrorMessage(error)}`);
    },
  });

  const projects: Project[] = projectsResponse?.items ?? [];
  const posts: PostDraft[] = postsResponse?.items ?? [];
  const deliverables: Deliverable[] = deliverablesResponse ?? [];
  const researchHistory = researchData?.results ?? [];

  // Research tool mutation
  const runResearchMutation = useMutation({
    mutationFn: ({ tool, params }: { tool: string; params?: Record<string, unknown> }) => {
      // Use the most recent active project for this client
      const activeProject = clientProjects.find(p => p.status !== 'delivered' && p.status !== 'exported') ?? clientProjects[0];
      if (!activeProject) {
        return Promise.reject(new Error('No project found for this client. Create a project using the Wizard first.'));
      }
      return researchApi.run({
        projectId: activeProject.id,
        clientId: clientId!,
        tool,
        params: params || {},
      });
    },
    onSuccess: (data, variables) => {
      setResearchResults(new Map(researchResults).set(variables.tool, data));
      setSelectedTool(null);
      setShowDataDialog(false);
      refetchResearch(); // Refetch research history to show new result
    },
    onError: (error, variables) => {
      alert(`Failed to run research tool "${variables.tool}": ${getApiErrorMessage(error)}`);
    },
  });

  // Handler for clicking a research tool button
  const handleRunResearchTool = (toolName: string) => {
    setSelectedTool(toolName);

    // Check if this tool needs input data
    const inputConfig = toolsNeedingInput[toolName];
    if (inputConfig) {
      // Show data collection dialog
      setDialogInputLabel(inputConfig.label);
      setDialogInputPlaceholder(inputConfig.placeholder);
      setDialogInputValue('');
      setShowDataDialog(true);
    } else {
      // Run immediately without data collection
      runResearchMutation.mutate({ tool: toolName, params: {} });
    }
  };

  // Handler for submitting the data collection dialog
  const handleDialogSubmit = () => {
    if (!selectedTool) return;

    const inputConfig = toolsNeedingInput[selectedTool];
    if (!inputConfig) return;

    // Build params with the collected data
    const params: Record<string, unknown> = {};
    if (dialogInputValue.trim()) {
      params[inputConfig.paramKey] = dialogInputValue.trim();
    }

    runResearchMutation.mutate({ tool: selectedTool, params });
  };

  // Handler for canceling the dialog
  const handleDialogCancel = () => {
    setShowDataDialog(false);
    setSelectedTool(null);
    setDialogInputValue('');
  };

  // Handler for exporting client profile
  const handleExportProfile = async () => {
    if (!client) return;

    setIsExporting(true);
    try {
      const { blob, filename } = await clientsApi.exportProfile(client.id);

      // Create blob URL and trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export client profile:', error);
      alert(`Failed to export client profile: ${getApiErrorMessage(error)}`);
    } finally {
      setIsExporting(false);
    }
  };

  if (clientLoading) {
    return <LoadingSpinner message="Loading client..." />;
  }

  if (clientError || !client) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <p className="text-lg font-medium text-neutral-700 dark:text-neutral-300">
          Client not found
        </p>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          This client may have been deleted or you don&apos;t have access.
        </p>
        <button
          className="mt-4 text-sm text-blue-600 hover:underline dark:text-blue-400"
          onClick={() => navigate(ROUTES.CLIENTS)}
        >
          Back to Clients
        </button>
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


  const communications: Communication[] = communicationsData ?? [];

  const tabs: {
    id: TabType;
    label: string;
    icon: typeof User;
    count?: number;
  }[] = [
    { id: 'overview', label: 'Overview', icon: User },
    { id: 'projects', label: 'Projects', icon: FileText, count: totalProjects },
    { id: 'research', label: 'Research', icon: FlaskConical },
    { id: 'stories', label: 'Stories', icon: BookOpen, count: storiesData?.total ?? 0 },
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
            onClick={() => navigate(ROUTES.CLIENTS)}
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
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setEditDialogOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            >
              <Edit className="h-4 w-4" />
              Edit
            </button>
            <button
              onClick={() => setSendEmailDialogOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            >
              <Mail className="h-4 w-4" />
              Send Email
            </button>
            <button
              onClick={handleExportProfile}
              disabled={isExporting}
              className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Export client profile as standalone document"
            >
              {isExporting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  Export Profile
                </>
              )}
            </button>
            <button
              onClick={() => navigate(ROUTES.WIZARD, { state: { clientId: client.id, clientName: client.name } })}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
            >
              <Plus className="h-4 w-4" />
              New Project
            </button>
            <button
              onClick={() => {
                if (client && confirm(`Are you sure you want to archive ${client.name}? You can restore it later.`)) {
                  archiveClientMutation.mutate();
                }
              }}
              disabled={archiveClientMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Archive className="h-4 w-4" />
              {archiveClientMutation.isPending ? 'Archiving...' : 'Archive'}
            </button>
            <button
              onClick={() => setDeleteDialogOpen(true)}
              disabled={deleteClientMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-red-300 dark:border-red-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 className="h-4 w-4" />
              {deleteClientMutation.isPending ? 'Deleting...' : 'Delete'}
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
                      {client.email || 'No email provided'}
                    </p>
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
                    <p className="mt-1 font-medium text-neutral-900 dark:text-neutral-100">
                      {client.industry || <span className="text-neutral-500 dark:text-neutral-400 italic">Not specified</span>}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Location</p>
                    <p className="mt-1 font-medium text-neutral-900 dark:text-neutral-100">
                      {client.location || <span className="text-neutral-500 dark:text-neutral-400 italic">Not specified</span>}
                    </p>
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
                          onClick={() => navigate(ROUTES.WIZARD, { state: { clientId: client.id, clientName: client.name } })}
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
                                onClick={() => navigate(ROUTES.PROJECT_DETAIL(project.id))}
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
                                onClick={() => navigate(ROUTES.PROJECT_DETAIL(project.id))}
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

                {isLoadingResearch ? (
                  <div className="flex justify-center p-8">
                    <Loader2 className="h-8 w-8 animate-spin text-primary-600 dark:text-primary-400" />
                  </div>
                ) : researchHistory.length === 0 ? (
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
                  <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
                        <thead className="bg-neutral-50 dark:bg-neutral-800">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                              Tool Name
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                              Date Performed
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                              Status
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                              Summary
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-neutral-600 dark:text-neutral-400">
                              Actions
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700 bg-white dark:bg-neutral-900">
                          {researchHistory.map((result) => (
                            <tr key={result.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800">
                              <td className="whitespace-nowrap px-6 py-4">
                                <div className="flex items-center gap-2">
                                  <FlaskConical className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                                  <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                                    {result.toolLabel || result.toolName.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                                  </span>
                                </div>
                              </td>
                              <td className="whitespace-nowrap px-6 py-4 text-sm text-neutral-600 dark:text-neutral-400">
                                {format(new Date(result.createdAt), 'MMM d, yyyy')}
                                <div className="text-xs text-neutral-500 dark:text-neutral-500">
                                  {format(new Date(result.createdAt), 'h:mm a')}
                                </div>
                              </td>
                              <td className="whitespace-nowrap px-6 py-4">
                                <span
                                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                    result.status === 'completed'
                                      ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300'
                                      : result.status === 'failed'
                                      ? 'bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300'
                                      : 'bg-amber-100 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300'
                                  }`}
                                >
                                  {result.status === 'completed' && <CheckCircle2 className="mr-1 h-3 w-3" />}
                                  {result.status.charAt(0).toUpperCase() + result.status.slice(1)}
                                </span>
                              </td>
                              <td className="px-6 py-4 max-w-md">
                                <p className="line-clamp-2 text-sm text-neutral-700 dark:text-neutral-300">
                                  {(result.data?.summary as string) || 'Research completed successfully'}
                                </p>
                              </td>
                              <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                                <button
                                  onClick={() => {
                                    setSelectedResult(result);
                                    setDrawerOpen(true);
                                  }}
                                  className="inline-flex items-center gap-1 text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                                >
                                  <Eye className="h-4 w-4" />
                                  View Results
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Stories */}
        {activeTab === 'stories' && (
          <div className="space-y-6">
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Client Success Stories</h3>
                  <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                    Mined customer stories for content generation. Stories are automatically saved from Story Mining research.
                  </p>
                </div>
                <button
                  onClick={() => setAddStoryDialogOpen(true)}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
                >
                  <Plus className="h-4 w-4" />
                  Add Story Manually
                </button>
              </div>

              {/* Stories List */}
              {isLoadingStories ? (
                <div className="flex justify-center p-8">
                  <Loader2 className="h-8 w-8 animate-spin text-primary-600 dark:text-primary-400" />
                </div>
              ) : !storiesData || storiesData.stories.length === 0 ? (
                <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-12 text-center">
                  <BookOpen className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-500" />
                  <p className="mt-4 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                    No stories yet
                  </p>
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                    Run the Story Mining research tool to automatically extract customer success stories.
                  </p>
                  <button
                    onClick={() => setActiveTab('research')}
                    className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
                  >
                    <FlaskConical className="h-4 w-4" />
                    Go to Research Tools
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {storiesData.stories.map((story) => (
                    <div
                      key={story.id}
                      className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3">
                            <h4 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
                              {story.title || 'Untitled Story'}
                            </h4>
                            {story.storyType && (
                              <span className="inline-flex items-center rounded-full bg-primary-100 dark:bg-primary-900/20 px-2.5 py-0.5 text-xs font-medium text-primary-800 dark:text-primary-300">
                                {story.storyType.replace(/_/g, ' ')}
                              </span>
                            )}
                          </div>

                          {story.summary && (
                            <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-300 line-clamp-2">
                              {story.summary}
                            </p>
                          )}

                          {story.emotionalHook && (
                            <div className="mt-3 rounded-md bg-neutral-50 dark:bg-neutral-800 p-3 border-l-2 border-primary-500">
                              <p className="text-sm italic text-neutral-700 dark:text-neutral-300">
                                "{story.emotionalHook}"
                              </p>
                            </div>
                          )}

                          {/* Metrics */}
                          {story.keyMetrics && Object.keys(story.keyMetrics).length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {Object.entries(story.keyMetrics).slice(0, 3).map(([key, value]) => (
                                <div
                                  key={key}
                                  className="inline-flex items-center gap-1 rounded-md bg-emerald-100 dark:bg-emerald-900/20 px-2 py-1 text-xs font-medium text-emerald-800 dark:text-emerald-300"
                                >
                                  <TrendingUp className="h-3 w-3" />
                                  {String(value)}
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Usage Stats */}
                          <div className="mt-4 flex items-center gap-4 text-xs text-neutral-600 dark:text-neutral-400">
                            <div className="flex items-center gap-1">
                              <Eye className="h-3 w-3" />
                              Used {story.usageCount} {story.usageCount === 1 ? 'time' : 'times'}
                            </div>
                            {story.platformsUsed.length > 0 && (
                              <div className="flex items-center gap-1">
                                <span>Platforms:</span>
                                <div className="flex gap-1">
                                  {story.platformsUsed.map((platform) => (
                                    <span
                                      key={platform}
                                      className="inline-flex items-center rounded bg-neutral-100 dark:bg-neutral-700 px-1.5 py-0.5 text-xs font-medium text-neutral-700 dark:text-neutral-300"
                                    >
                                      {platform}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {story.source && (
                              <div className="flex items-center gap-1">
                                <span>Source: {story.source.replace(/_/g, ' ')}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2 ml-4">
                          <button
                            onClick={() => {
                              setSelectedStory(story);
                              setStoryDrawerOpen(true);
                            }}
                            className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700"
                            title="View full story details"
                          >
                            <Eye className="h-4 w-4" />
                            View
                          </button>
                          <button
                            onClick={() => {
                              if (confirm(`Are you sure you want to delete "${story.title || 'this story'}"?`)) {
                                deleteStoryMutation.mutate(story.id);
                              }
                            }}
                            disabled={deleteStoryMutation.isPending}
                            className="inline-flex items-center gap-1 rounded-lg border border-red-300 dark:border-red-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm font-medium text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Delete story"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 5: Content */}
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
                <option value="twitter">Microblog</option>
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
                clientPosts.slice(0, visiblePostCount).map((post) => (
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

            {clientPosts.length > visiblePostCount && (
              <div className="text-center">
                <button
                  onClick={() => setVisiblePostCount(clientPosts.length)}
                  className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                >
                  Load More ({clientPosts.length - visiblePostCount} more posts)
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tab 6: Deliverables */}
        {activeTab === 'deliverables' && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <button
                onClick={() => navigate(`${ROUTES.DELIVERABLES}?clientId=${client.id}`)}
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
                              onClick={() => navigate(`${ROUTES.CONTENT_REVIEW}?projectId=${deliverable.projectId}`)}
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

        {/* Tab 7: Billing & Payments */}
        {activeTab === 'billing' && (
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-12 text-center">
            <DollarSign className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-500" />
            <p className="mt-4 font-medium text-neutral-700 dark:text-neutral-300">Billing not yet available</p>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">Invoice tracking will be available in a future update.</p>
          </div>
        )}

        {/* Tab 8: Communication History */}
        {activeTab === 'communication' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Communication Log</h3>
              <button
                onClick={() => setNewCommDialogOpen(true)}
                className="rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
              >
                New Communication
              </button>
            </div>

            {/* Type filter */}
            <div className="flex gap-2">
              {['all', 'email', 'call', 'meeting', 'note'].map((type) => (
                <button
                  key={type}
                  onClick={() => setCommTypeFilter(type)}
                  className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${
                    commTypeFilter === type
                      ? 'bg-primary-600 dark:bg-primary-500 text-white'
                      : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                  }`}
                >
                  {type === 'all' ? `All (${communications.length})` : type}
                </button>
              ))}
            </div>

            {isLoadingCommunications ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
              </div>
            ) : (
              <div className="space-y-3">
                {communications.filter(c => commTypeFilter === 'all' || c.type === commTypeFilter).map((comm) => {
                  const bgColors: Record<string, string> = {
                    email: 'bg-primary-100 dark:bg-primary-900/20',
                    call: 'bg-emerald-100 dark:bg-emerald-900/20',
                    meeting: 'bg-violet-100 dark:bg-violet-900/20',
                    note: 'bg-amber-100 dark:bg-amber-900/20',
                  };
                  const iconColors: Record<string, string> = {
                    email: 'text-primary-600 dark:text-primary-400',
                    call: 'text-emerald-600 dark:text-emerald-400',
                    meeting: 'text-violet-600 dark:text-violet-400',
                    note: 'text-amber-600 dark:text-amber-400',
                  };
                  const TypeIcon =
                    comm.type === 'email' ? Mail
                    : comm.type === 'call' ? Phone
                    : comm.type === 'meeting' ? Calendar
                    : MessageSquare;

                  return (
                    <div key={comm.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-5">
                      <div className="flex items-start gap-4">
                        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${bgColors[comm.type] ?? 'bg-neutral-100 dark:bg-neutral-800'}`}>
                          <TypeIcon className={`h-4 w-4 ${iconColors[comm.type] ?? 'text-neutral-600 dark:text-neutral-400'}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="font-medium text-neutral-900 dark:text-neutral-100">{comm.subject}</p>
                              <div className="mt-1 flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
                                <span className="capitalize">{comm.type}</span>
                                <span>&middot;</span>
                                <span className="capitalize">{comm.direction}</span>
                                {comm.duration && (
                                  <>
                                    <span>&middot;</span>
                                    <span>{comm.duration}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-3 shrink-0">
                              <span className="text-xs text-neutral-500 dark:text-neutral-400">
                                {formatDistanceToNow(new Date(comm.created_at), { addSuffix: true })}
                              </span>
                              <button
                                onClick={() => {
                                  if (confirm('Delete this communication record?')) {
                                    deleteCommunicationMutation.mutate(comm.id);
                                  }
                                }}
                                className="text-neutral-400 hover:text-red-500 dark:hover:text-red-400"
                                title="Delete"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </div>
                          {comm.content && (
                            <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400 whitespace-pre-wrap">{comm.content}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {!isLoadingCommunications && communications.filter(c => commTypeFilter === 'all' || c.type === commTypeFilter).length === 0 && (
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-12 text-center">
                <MessageSquare className="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-500" />
                <p className="mt-4 font-medium text-neutral-700 dark:text-neutral-300">No communication history</p>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">Log calls, emails, and meetings to track your client interactions.</p>
                <button
                  onClick={() => setNewCommDialogOpen(true)}
                  className="mt-4 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
                >
                  Log First Communication
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Research Tool Data Collection Dialog */}
      {showDataDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-lg rounded-lg bg-white dark:bg-neutral-900 p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                {selectedTool?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
              </h3>
              <button
                onClick={handleDialogCancel}
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                {dialogInputLabel}
              </label>
              <textarea
                value={dialogInputValue}
                onChange={(e) => setDialogInputValue(e.target.value)}
                placeholder={dialogInputPlaceholder}
                rows={6}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 p-3 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
              />
              <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
                Optional: Providing input data improves analysis quality. Leave empty to use client profile data.
              </p>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={handleDialogCancel}
                className="px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100"
              >
                Cancel
              </button>
              <button
                onClick={handleDialogSubmit}
                disabled={runResearchMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {runResearchMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Running...
                  </>
                ) : (
                  'Run Analysis'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Research Results Drawer */}
      <ResearchResultsDrawer
        result={selectedResult}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedResult(null);
        }}
      />

      {/* Story Details Drawer */}
      <StoryDetailsDrawer
        story={selectedStory}
        open={storyDrawerOpen}
        onClose={() => {
          setStoryDrawerOpen(false);
          setSelectedStory(null);
        }}
      />

      {/* Add Story Dialog */}
      <AddStoryDialog
        clientId={clientId!}
        projectId={projects.length > 0 ? projects[0].id : undefined}
        open={addStoryDialogOpen}
        onClose={() => setAddStoryDialogOpen(false)}
        onSubmit={(story) => createStoryMutation.mutate(story)}
        isSubmitting={createStoryMutation.isPending}
      />

      {/* Edit Client Dialog */}
      {client && (
        <EditClientDialog
          client={client}
          open={editDialogOpen}
          onClose={() => setEditDialogOpen(false)}
          onSubmit={(updates) => updateClientMutation.mutate(updates)}
          isSubmitting={updateClientMutation.isPending}
        />
      )}

      {newCommDialogOpen && clientId && (
        <NewCommunicationDialog
          clientId={clientId}
          onClose={() => setNewCommDialogOpen(false)}
          onSubmit={(input) => createCommunicationMutation.mutate(input)}
          isSubmitting={createCommunicationMutation.isPending}
        />
      )}

      {/* Send Email Dialog */}
      {sendEmailDialogOpen && client && (
        <SendEmailDialog
          client={client}
          onClose={() => setSendEmailDialogOpen(false)}
          onSuccess={() => {
            refetchCommunications();
            setSendEmailDialogOpen(false);
          }}
        />
      )}

      {/* Delete Client Dialog */}
      {client && (
        <DeleteClientDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          clientId={client.id}
          clientName={client.name}
          onConfirmDelete={() => archiveClientMutation.mutateAsync()}
          onConfirmPermanentDelete={() => permanentDeleteMutation.mutateAsync()}
          onExportData={handleExportProfile}
        />
      )}
    </div>
  );
}
