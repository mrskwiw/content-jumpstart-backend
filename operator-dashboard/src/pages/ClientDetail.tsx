import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
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
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { postsApi } from '@/api/posts';
import { deliverablesApi } from '@/api/deliverables';
import type { Project, PostDraft, Deliverable } from '@/types/domain';
import type { PaginatedResponse } from '@/types/pagination';

type TabType = 'overview' | 'projects' | 'content' | 'deliverables' | 'billing' | 'communication';

export default function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [notes, setNotes] = useState('');

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

  if (clientLoading || !client) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-sm text-slate-600">Loading client...</p>
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
            className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Clients
          </button>
        </div>
      </div>

      {/* Client Header Card */}
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            {/* Avatar */}
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-600 text-2xl font-semibold text-white">
              {client.name.charAt(0).toUpperCase()}
            </div>

            {/* Client Info */}
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">{client.name}</h1>
              <div className="mt-2 flex items-center gap-3">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    client.status === 'active'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-slate-100 text-slate-800'
                  }`}
                >
                  {client.status || 'active'}
                </span>
                <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                  {packageTier}
                </span>
                <span className="text-sm text-slate-600">
                  ${totalRevenue.toLocaleString()} total revenue
                </span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <button className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              <Edit className="h-4 w-4" />
              Edit
            </button>
            <button className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              <Mail className="h-4 w-4" />
              Send Email
            </button>
            <button
              onClick={() => navigate('/dashboard/wizard', { state: { clientId: client.id, clientName: client.name } })}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              New Project
            </button>
            <button className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              <Archive className="h-4 w-4" />
              Archive
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-6 grid grid-cols-4 gap-6 border-t border-slate-200 pt-6">
          <div>
            <p className="text-sm text-slate-600">Total Projects</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{totalProjects}</p>
          </div>
          <div>
            <p className="text-sm text-slate-600">Active Projects</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{activeProjects}</p>
          </div>
          <div>
            <p className="text-sm text-slate-600">Posts Generated</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{clientPosts.length}</p>
          </div>
          <div>
            <p className="text-sm text-slate-600">Deliverables</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{clientDeliverables.length}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 border-b-2 px-1 py-4 text-sm font-medium ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-600 hover:border-slate-300 hover:text-slate-900'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
                {tab.count !== undefined && (
                  <span
                    className={`ml-2 rounded-full px-2 py-0.5 text-xs ${
                      activeTab === tab.id
                        ? 'bg-blue-100 text-blue-600'
                        : 'bg-slate-100 text-slate-600'
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
              <div className="rounded-lg border border-slate-200 bg-white p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                  <User className="h-5 w-5 text-slate-600" />
                  Contact Information
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-slate-600">Company Name</p>
                    <p className="mt-1 font-medium text-slate-900">{client.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600">Email</p>
                    <p className="mt-1 font-medium text-slate-900">
                      {client.tags?.find(t => t.includes('@')) || 'contact@example.com'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600">Phone</p>
                    <p className="mt-1 font-medium text-slate-900">+1 (555) 123-4567</p>
                  </div>
                </div>
              </div>

              {/* Business Details */}
              <div className="rounded-lg border border-slate-200 bg-white p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                  <Building2 className="h-5 w-5 text-slate-600" />
                  Business Details
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-slate-600">Industry</p>
                    <p className="mt-1 font-medium text-slate-900">Technology / SaaS</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600">Company Size</p>
                    <p className="mt-1 font-medium text-slate-900">50-100 employees</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600">Website</p>
                    <a
                      href={`https://${client.name.toLowerCase().replace(/\s+/g, '')}.com`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-flex items-center gap-1 font-medium text-blue-600 hover:text-blue-700"
                    >
                      <Globe className="h-4 w-4" />
                      Visit website
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
              </div>

              {/* Package Details */}
              <div className="rounded-lg border border-slate-200 bg-white p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                  <FileText className="h-5 w-5 text-slate-600" />
                  Package Details
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-slate-600">Current Tier</p>
                    <p className="mt-1">
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-800">
                        {packageTier}
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600">Pricing</p>
                    <p className="mt-1 font-medium text-slate-900">
                      ${packageTier === 'Premium' ? '2,500' : packageTier === 'Professional' ? '1,800' : '1,200'} per project
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600">Features</p>
                    <ul className="mt-1 space-y-1 text-sm text-slate-700">
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        30 posts per project
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        Multi-platform support
                      </li>
                      {packageTier !== 'Starter' && (
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                          Priority support
                        </li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Account Manager */}
              <div className="rounded-lg border border-slate-200 bg-white p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                  <User className="h-5 w-5 text-slate-600" />
                  Account Manager
                </h3>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-600 text-sm font-semibold text-white">
                    SM
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">Sarah Martinez</p>
                    <p className="text-sm text-slate-600">sarah@company.com</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Custom Notes */}
            <div className="rounded-lg border border-slate-200 bg-white p-6">
              <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
                <MessageSquare className="h-5 w-5 text-slate-600" />
                Custom Notes
              </h3>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes about this client..."
                className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                rows={6}
              />
              <div className="mt-3 flex justify-end">
                <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  Save Notes
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Projects */}
        {activeTab === 'projects' && (
          <div className="rounded-lg border border-slate-200 bg-white">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                      Project Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                      Posts
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                      Quality
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-600">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {clientProjects.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center">
                        <p className="text-sm text-slate-600">No projects yet</p>
                        <button
                          onClick={() => navigate('/dashboard/wizard', { state: { clientId: client.id, clientName: client.name } })}
                          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
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
                          draft: 'bg-slate-100 text-slate-800',
                          generating: 'bg-blue-100 text-blue-800',
                          qa: 'bg-amber-100 text-amber-800',
                          ready: 'bg-emerald-100 text-emerald-800',
                          exported: 'bg-purple-100 text-purple-800',
                          delivered: 'bg-emerald-100 text-emerald-800',
                          error: 'bg-rose-100 text-rose-800',
                        };

                        const projectPostCount = clientPosts.filter(
                          (post) => post.projectId === project.id
                        ).length;

                        return (
                          <tr key={project.id} className="hover:bg-slate-50">
                            <td className="whitespace-nowrap px-6 py-4">
                              <button
                                onClick={() => navigate(`/dashboard/projects/${project.id}`)}
                                className="font-medium text-blue-600 hover:text-blue-700"
                              >
                                {project.name}
                              </button>
                            </td>
                            <td className="whitespace-nowrap px-6 py-4">
                              <span
                                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                  statusColors[project.status] || 'bg-slate-100 text-slate-800'
                                }`}
                              >
                                {project.status}
                              </span>
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">
                              {projectPostCount}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">
                              {project.createdAt ? format(new Date(project.createdAt), 'MMM d, yyyy') : 'N/A'}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">
                              <span className="font-medium text-emerald-600">92%</span>
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                              <button
                                onClick={() => navigate(`/dashboard/projects/${project.id}`)}
                                className="text-blue-600 hover:text-blue-700"
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

        {/* Tab 3: Content */}
        {activeTab === 'content' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex items-center gap-4 rounded-lg border border-slate-200 bg-white p-4">
              <input
                type="search"
                placeholder="Search posts..."
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <select className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500">
                <option value="">All Projects</option>
                {clientProjects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <select className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500">
                <option value="">All Platforms</option>
                <option value="linkedin">LinkedIn</option>
                <option value="twitter">Twitter</option>
                <option value="facebook">Facebook</option>
              </select>
            </div>

            {/* Posts Grid */}
            <div className="grid gap-4 md:grid-cols-2">
              {clientPosts.length === 0 ? (
                <div className="col-span-2 rounded-lg border border-slate-200 bg-white p-12 text-center">
                  <MessageSquare className="mx-auto h-12 w-12 text-slate-400" />
                  <p className="mt-4 text-sm text-slate-600">No content generated yet</p>
                </div>
              ) : (
                clientPosts.slice(0, 20).map((post) => (
                  <div key={post.id} className="rounded-lg border border-slate-200 bg-white p-4 hover:shadow-md">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs text-slate-600">
                        {projects.find((p) => p.id === post.projectId)?.name}
                      </span>
                      <span className="text-xs text-slate-500">
                        {(post as { wordCount?: number }).wordCount ?? (post.content?.split(' ').length ?? 0)} words
                      </span>
                    </div>
                    <p className="line-clamp-4 text-sm text-slate-900">{post.content}</p>
                    <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-3">
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                        LinkedIn
                      </span>
                      <button className="text-xs text-blue-600 hover:text-blue-700">View Full</button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {clientPosts.length > 20 && (
              <div className="text-center">
                <button className="text-sm text-blue-600 hover:text-blue-700">
                  Load More ({clientPosts.length - 20} more posts)
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Deliverables */}
        {activeTab === 'deliverables' && (
          <div className="rounded-lg border border-slate-200 bg-white">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                      Project
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                      Format
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                      Delivered
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-600">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {clientDeliverables.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-12 text-center">
                        <Download className="mx-auto h-12 w-12 text-slate-400" />
                        <p className="mt-4 text-sm text-slate-600">No deliverables yet</p>
                      </td>
                    </tr>
                  ) : (
                    clientDeliverables.map((deliverable) => (
                      <tr key={deliverable.id} className="hover:bg-slate-50">
                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-slate-900">
                          {projects.find((p) => p.id === deliverable.projectId)?.name}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-800">
                            {deliverable.format?.toUpperCase() || 'TXT'}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span
                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                              deliverable.status === 'delivered'
                                ? 'bg-emerald-100 text-emerald-800'
                                : deliverable.status === 'ready'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-slate-100 text-slate-800'
                            }`}
                          >
                            {deliverable.status}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">
                          {deliverable.deliveredAt
                            ? format(new Date(deliverable.deliveredAt), 'MMM d, yyyy')
                            : '-'}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                          <button className="text-blue-600 hover:text-blue-700">
                            <Download className="inline h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 5: Billing & Payments */}
        {activeTab === 'billing' && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white p-6">
                <p className="text-sm text-slate-600">Total Revenue</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900">
                  ${totalRevenue.toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-6">
                <p className="text-sm text-slate-600">Outstanding</p>
                <p className="mt-2 text-3xl font-semibold text-amber-600">
                  ${mockInvoices.filter(i => i.status === 'pending').reduce((sum, i) => sum + i.amount, 0).toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-6">
                <p className="text-sm text-slate-600">Paid This Month</p>
                <p className="mt-2 text-3xl font-semibold text-emerald-600">
                  ${mockInvoices.filter(i => i.status === 'paid').reduce((sum, i) => sum + i.amount, 0).toLocaleString()}
                </p>
              </div>
            </div>

            {/* Invoices Table */}
            <div className="rounded-lg border border-slate-200 bg-white">
              <div className="border-b border-slate-200 px-6 py-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-slate-900">Invoices</h3>
                  <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                    Generate Invoice
                  </button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                        Invoice #
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                        Project
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                        Date
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                        Amount
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                        Status
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-600">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white">
                    {mockInvoices.map((invoice) => (
                      <tr key={invoice.id} className="hover:bg-slate-50">
                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-slate-900">
                          INV-{invoice.id.padStart(4, '0')}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">
                          {invoice.project}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">
                          {format(new Date(invoice.date), 'MMM d, yyyy')}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-slate-900">
                          ${invoice.amount.toLocaleString()}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <span
                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                              invoice.status === 'paid'
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-amber-100 text-amber-800'
                            }`}
                          >
                            {invoice.status}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                          <button className="text-blue-600 hover:text-blue-700">View PDF</button>
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
              <h3 className="text-lg font-semibold text-slate-900">Communication Log</h3>
              <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                New Communication
              </button>
            </div>

            {/* Communication Timeline */}
            <div className="space-y-4">
              {mockCommunications.map((comm, index) => (
                <div key={comm.id} className="rounded-lg border border-slate-200 bg-white p-6">
                  <div className="flex items-start gap-4">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-full ${
                        comm.type === 'email' ? 'bg-blue-100' : 'bg-emerald-100'
                      }`}
                    >
                      {comm.type === 'email' ? (
                        <Mail className="h-5 w-5 text-blue-600" />
                      ) : (
                        <Phone className="h-5 w-5 text-emerald-600" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-slate-900">{comm.subject}</p>
                          <p className="mt-1 text-sm text-slate-600">
                            {comm.type === 'email' ? `From: ${comm.from}` : `Duration: ${comm.duration}`}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-slate-600">
                          <Calendar className="h-4 w-4" />
                          {format(new Date(comm.date), 'MMM d, yyyy')}
                        </div>
                      </div>
                      {comm.type === 'email' && (
                        <button className="mt-3 text-sm text-blue-600 hover:text-blue-700">
                          View Email Thread →
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {mockCommunications.length === 0 && (
              <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
                <MessageSquare className="mx-auto h-12 w-12 text-slate-400" />
                <p className="mt-4 text-sm text-slate-600">No communication history</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
