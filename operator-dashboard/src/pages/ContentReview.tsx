import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search,
  Filter,
  LayoutGrid,
  List,
  Maximize2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Download,
  Edit2,
  Save,
  X,
  ChevronDown,
  BarChart3,
  Eye,
} from 'lucide-react';
import { format } from 'date-fns';
import { postsApi } from '@/api/posts';
import { projectsApi } from '@/api/projects';
import { clientsApi } from '@/api/clients';
import type { PostDraft, Project, Client } from '@/types/domain';
import type { PaginatedResponse } from '@/types/pagination';

type ViewMode = 'grid' | 'list' | 'full';
type StatusFilter = 'all' | 'pending' | 'approved' | 'flagged' | 'archived';
type QualityFilter = 'all' | 'high' | 'medium' | 'low';

interface PostWithContext {
  id: string;
  content: string;
  projectId: string;
  projectName?: string;
  clientName?: string;
  platform?: string;
  templateId?: number;
  wordCount?: number;
  qualityScore?: number;
  status?: string;
  createdAt?: string;
  isEditing?: boolean;
}

export default function ContentReview() {
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [clientFilter, setClientFilter] = useState('all');
  const [projectFilter, setProjectFilter] = useState('all');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [qualityFilter, setQualityFilter] = useState<QualityFilter>('all');
  const [selectedPosts, setSelectedPosts] = useState<string[]>([]);
  const [editingPostId, setEditingPostId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  // Fetch data
  const { data: postsResponse } = useQuery<PaginatedResponse<PostDraft>>({
    queryKey: ['posts'],
    queryFn: () => postsApi.list(),
  });

  const { data: projectsResponse } = useQuery<PaginatedResponse<Project>>({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  });

  const { data: clients = [] } = useQuery<Client[]>({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  });

  const posts: PostDraft[] = postsResponse?.items ?? [];
  const projects: Project[] = projectsResponse?.items ?? [];

  // Mock update mutation (replace with actual API call)
  const updatePostMutation = useMutation({
    mutationFn: async ({ postId, content }: { postId: string; content: string }) => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500));
      return { id: postId, content };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['posts'] });
      setEditingPostId(null);
      setEditContent('');
    },
  });

  // Enrich posts with context
  const postsWithContext: PostWithContext[] = useMemo(() => {
    return posts.map(post => {
      const project = projects.find(p => p.id === post.projectId);
      const client = project ? clients.find(c => c.id === project.clientId) : undefined;

      // Mock quality score (would come from backend)
      const qualityScore = 70 + Math.floor(Math.random() * 30);

      return {
        ...post,
        projectName: project?.name,
        clientName: client?.name,
        wordCount: (post as { wordCount?: number }).wordCount ?? (post.content?.split(' ').length ?? 0),
        qualityScore,
        status: qualityScore > 85 ? 'approved' : qualityScore < 70 ? 'flagged' : 'pending',
      };
    });
  }, [posts, projects, clients]);

  // Apply filters
  const filteredPosts = useMemo(() => {
    let filtered = postsWithContext;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(post =>
        post.content.toLowerCase().includes(query) ||
        post.clientName?.toLowerCase().includes(query) ||
        post.projectName?.toLowerCase().includes(query)
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(post => post.status === statusFilter);
    }

    // Client filter
    if (clientFilter !== 'all') {
      filtered = filtered.filter(post => post.clientName === clientFilter);
    }

    // Project filter
    if (projectFilter !== 'all') {
      filtered = filtered.filter(post => post.projectName === projectFilter);
    }

    // Platform filter
    if (platformFilter !== 'all') {
      filtered = filtered.filter(post => post.platform === platformFilter);
    }

    // Quality filter
    if (qualityFilter !== 'all') {
      filtered = filtered.filter(post => {
        const score = post.qualityScore || 0;
        if (qualityFilter === 'high') return score > 85;
        if (qualityFilter === 'medium') return score >= 70 && score <= 85;
        if (qualityFilter === 'low') return score < 70;
        return true;
      });
    }

    return filtered;
  }, [postsWithContext, searchQuery, statusFilter, clientFilter, projectFilter, platformFilter, qualityFilter]);

  // Get unique values for filters
  const uniqueClients = useMemo(() =>
    Array.from(new Set(postsWithContext.map(p => p.clientName).filter(Boolean))),
    [postsWithContext]
  );

  const uniqueProjects = useMemo(() => {
    const filtered = clientFilter === 'all'
      ? postsWithContext
      : postsWithContext.filter(p => p.clientName === clientFilter);
    return Array.from(new Set(filtered.map(p => p.projectName).filter(Boolean)));
  }, [postsWithContext, clientFilter]);

  // Handle inline editing
  const handleStartEdit = (post: PostWithContext) => {
    setEditingPostId(post.id);
    setEditContent(post.content);
  };

  const handleSaveEdit = () => {
    if (editingPostId) {
      updatePostMutation.mutate({ postId: editingPostId, content: editContent });
    }
  };

  const handleCancelEdit = () => {
    setEditingPostId(null);
    setEditContent('');
  };

  // Handle selection
  const handleSelectPost = (postId: string) => {
    setSelectedPosts(prev =>
      prev.includes(postId) ? prev.filter(id => id !== postId) : [...prev, postId]
    );
  };

  const handleSelectAll = () => {
    if (selectedPosts.length === filteredPosts.length) {
      setSelectedPosts([]);
    } else {
      setSelectedPosts(filteredPosts.map(p => p.id));
    }
  };

  // Bulk actions
  const handleBulkApprove = () => {
    console.log('Approving posts:', selectedPosts);
    setSelectedPosts([]);
  };

  const handleBulkFlag = () => {
    console.log('Flagging posts:', selectedPosts);
    setSelectedPosts([]);
  };

  const handleBulkRegenerate = () => {
    console.log('Regenerating posts:', selectedPosts);
    setSelectedPosts([]);
  };

  const handleBulkExport = () => {
    console.log('Exporting posts:', selectedPosts);
  };

  // Get quality badge
  const getQualityBadge = (score?: number) => {
    if (!score) return null;

    if (score > 85) {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
          <CheckCircle2 className="h-3 w-3" />
          {score}%
        </span>
      );
    }
    if (score >= 70) {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
          <AlertCircle className="h-3 w-3" />
          {score}%
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
        <XCircle className="h-3 w-3" />
        {score}%
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Content Review</h1>
        <p className="text-sm text-slate-600">
          Review and approve content across all projects
        </p>
      </header>

      {/* Filters Bar */}
      <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
        {/* Search and View Toggle */}
        <div className="flex items-center justify-between">
          <div className="flex flex-1 items-center gap-4">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                placeholder="Search posts, clients, projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-slate-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Status Tabs */}
            <div className="flex items-center gap-2">
              {(['all', 'pending', 'approved', 'flagged'] as StatusFilter[]).map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`rounded-lg px-3 py-2 text-sm font-medium ${
                    statusFilter === status
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`rounded-lg p-2 ${
                viewMode === 'grid'
                  ? 'bg-blue-100 text-blue-600'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`rounded-lg p-2 ${
                viewMode === 'list'
                  ? 'bg-blue-100 text-blue-600'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <List className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('full')}
              className={`rounded-lg p-2 ${
                viewMode === 'full'
                  ? 'bg-blue-100 text-blue-600'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Maximize2 className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Advanced Filters */}
        <div className="flex items-center gap-3">
          <Filter className="h-4 w-4 text-slate-600" />

          {/* Client Filter */}
          <select
            value={clientFilter}
            onChange={(e) => {
              setClientFilter(e.target.value);
              setProjectFilter('all'); // Reset project filter when client changes
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All Clients</option>
            {uniqueClients.map(client => (
              <option key={client} value={client}>{client}</option>
            ))}
          </select>

          {/* Project Filter */}
          <select
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            disabled={clientFilter === 'all' && uniqueProjects.length === 0}
          >
            <option value="all">All Projects</option>
            {uniqueProjects.map(project => (
              <option key={project} value={project}>{project}</option>
            ))}
          </select>

          {/* Platform Filter */}
          <select
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All Platforms</option>
            <option value="linkedin">LinkedIn</option>
            <option value="twitter">Twitter</option>
            <option value="facebook">Facebook</option>
            <option value="blog">Blog</option>
          </select>

          {/* Quality Filter */}
          <select
            value={qualityFilter}
            onChange={(e) => setQualityFilter(e.target.value as QualityFilter)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All Quality</option>
            <option value="high">High (&gt;85%)</option>
            <option value="medium">Medium (70-85%)</option>
            <option value="low">Low (&lt;70%)</option>
          </select>
        </div>
      </div>

      {/* Bulk Actions Bar */}
      {selectedPosts.length > 0 && (
        <div className="flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-blue-900">
              {selectedPosts.length} post{selectedPosts.length !== 1 ? 's' : ''} selected
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleBulkApprove}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            >
              <CheckCircle2 className="h-4 w-4" />
              Approve
            </button>
            <button
              onClick={handleBulkFlag}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <AlertCircle className="h-4 w-4" />
              Flag
            </button>
            <button
              onClick={handleBulkRegenerate}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw className="h-4 w-4" />
              Regenerate
            </button>
            <button
              onClick={handleBulkExport}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <Download className="h-4 w-4" />
              Export
            </button>
          </div>
        </div>
      )}

      {/* Results Count */}
      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>
          Showing {filteredPosts.length} of {postsWithContext.length} posts
        </span>
        {viewMode === 'list' && (
          <button
            onClick={handleSelectAll}
            className="text-blue-600 hover:text-blue-700"
          >
            {selectedPosts.length === filteredPosts.length ? 'Deselect All' : 'Select All'}
          </button>
        )}
      </div>

      {/* Content Display */}
      {viewMode === 'grid' && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredPosts.map((post) => (
            <div
              key={post.id}
              className={`rounded-lg border bg-white p-4 transition-shadow hover:shadow-md ${
                selectedPosts.includes(post.id) ? 'border-blue-500 ring-2 ring-blue-200' : 'border-slate-200'
              }`}
            >
              {/* Header */}
              <div className="mb-3 flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedPosts.includes(post.id)}
                    onChange={() => handleSelectPost(post.id)}
                    className="rounded"
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                      {post.platform || 'LinkedIn'}
                    </span>
                    {post.templateId && (
                      <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-800">
                        T{post.templateId}
                      </span>
                    )}
                  </div>
                </div>
                {getQualityBadge(post.qualityScore)}
              </div>

              {/* Content */}
              {editingPostId === post.id ? (
                <div className="space-y-2">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 p-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    rows={8}
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleSaveEdit}
                      disabled={updatePostMutation.isPending}
                      className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      <Save className="h-3 w-3" />
                      {updatePostMutation.isPending ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      disabled={updatePostMutation.isPending}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      <X className="h-3 w-3" />
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <p className="line-clamp-6 text-sm text-slate-900">{post.content}</p>
              )}

              {/* Metadata */}
              <div className="mt-3 space-y-2 border-t border-slate-200 pt-3">
                <div className="flex items-center justify-between text-xs text-slate-600">
                  <span>{post.clientName}</span>
                  <span>{post.wordCount}w</span>
                </div>
                <div className="text-xs text-slate-500">{post.projectName}</div>
              </div>

              {/* Actions */}
              {editingPostId !== post.id && (
                <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleStartEdit(post)}
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                    >
                      <Edit2 className="h-3 w-3" />
                      Edit
                    </button>
                    <button className="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900">
                      <Eye className="h-3 w-3" />
                      View Full
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    {post.status === 'pending' && (
                      <button className="text-xs text-emerald-600 hover:text-emerald-700">
                        Approve
                      </button>
                    )}
                    {post.status === 'flagged' && (
                      <button className="inline-flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700">
                        <RefreshCw className="h-3 w-3" />
                        Regen
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {filteredPosts.length === 0 && (
            <div className="col-span-full rounded-lg border border-slate-200 bg-white p-12 text-center">
              <Search className="mx-auto h-12 w-12 text-slate-400" />
              <p className="mt-4 text-sm text-slate-600">No posts found</p>
              <p className="mt-1 text-xs text-slate-500">Try adjusting your filters</p>
            </div>
          )}
        </div>
      )}

      {viewMode === 'list' && (
        <div className="rounded-lg border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={selectedPosts.length === filteredPosts.length && filteredPosts.length > 0}
                      onChange={handleSelectAll}
                      className="rounded"
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                    Post Excerpt
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                    Client / Project
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                    Platform
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                    Words
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">
                    Quality
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
                {filteredPosts.map((post) => (
                  <tr
                    key={post.id}
                    className={`hover:bg-slate-50 ${
                      selectedPosts.includes(post.id) ? 'bg-blue-50' : ''
                    }`}
                  >
                    <td className="whitespace-nowrap px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedPosts.includes(post.id)}
                        onChange={() => handleSelectPost(post.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <p className="line-clamp-2 max-w-md text-sm text-slate-900">
                        {post.content.substring(0, 150)}...
                      </p>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <div className="text-sm">
                        <p className="font-medium text-slate-900">{post.clientName}</p>
                        <p className="text-slate-600">{post.projectName}</p>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                        {post.platform || 'LinkedIn'}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">
                      {post.wordCount}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      {getQualityBadge(post.qualityScore)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          post.status === 'approved'
                            ? 'bg-emerald-100 text-emerald-800'
                            : post.status === 'flagged'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {post.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleStartEdit(post)}
                          className="text-sm text-blue-600 hover:text-blue-700"
                        >
                          Edit
                        </button>
                        <button className="text-sm text-slate-600 hover:text-slate-900">
                          View
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredPosts.length === 0 && (
            <div className="p-12 text-center">
              <Search className="mx-auto h-12 w-12 text-slate-400" />
              <p className="mt-4 text-sm text-slate-600">No posts found</p>
            </div>
          )}
        </div>
      )}

      {viewMode === 'full' && (
        <div className="space-y-4">
          {filteredPosts.map((post) => (
            <div
              key={post.id}
              className={`rounded-lg border bg-white p-6 ${
                selectedPosts.includes(post.id) ? 'border-blue-500 ring-2 ring-blue-200' : 'border-slate-200'
              }`}
            >
              {/* Header */}
              <div className="mb-4 flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <input
                    type="checkbox"
                    checked={selectedPosts.includes(post.id)}
                    onChange={() => handleSelectPost(post.id)}
                    className="mt-1 rounded"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-slate-900">{post.clientName}</h3>
                      <span className="text-sm text-slate-600">→</span>
                      <span className="text-sm text-slate-600">{post.projectName}</span>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                        {post.platform || 'LinkedIn'}
                      </span>
                      {post.templateId && (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-800">
                          Template {post.templateId}
                        </span>
                      )}
                      <span className="text-xs text-slate-600">{post.wordCount} words</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {getQualityBadge(post.qualityScore)}
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      post.status === 'approved'
                        ? 'bg-emerald-100 text-emerald-800'
                        : post.status === 'flagged'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {post.status}
                  </span>
                </div>
              </div>

              {/* Content */}
              {editingPostId === post.id ? (
                <div className="space-y-3">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    rows={12}
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleSaveEdit}
                      disabled={updatePostMutation.isPending}
                      className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      <Save className="h-4 w-4" />
                      {updatePostMutation.isPending ? 'Saving...' : 'Save Changes'}
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      disabled={updatePostMutation.isPending}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      <X className="h-4 w-4" />
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="prose prose-sm max-w-none">
                  <p className="whitespace-pre-wrap text-slate-900">{post.content}</p>
                </div>
              )}

              {/* Actions */}
              {editingPostId !== post.id && (
                <div className="mt-4 flex items-center justify-between border-t border-slate-200 pt-4">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleStartEdit(post)}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      <Edit2 className="h-4 w-4" />
                      Edit Post
                    </button>
                    {post.status === 'flagged' && (
                      <button className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                        <RefreshCw className="h-4 w-4" />
                        Regenerate
                      </button>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {post.status !== 'approved' && (
                      <button className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700">
                        <CheckCircle2 className="h-4 w-4" />
                        Approve
                      </button>
                    )}
                    {post.status !== 'flagged' && (
                      <button className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50">
                        <AlertCircle className="h-4 w-4" />
                        Flag
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {filteredPosts.length === 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
              <Search className="mx-auto h-12 w-12 text-slate-400" />
              <p className="mt-4 text-sm text-slate-600">No posts found</p>
              <p className="mt-1 text-xs text-slate-500">Try adjusting your filters</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
