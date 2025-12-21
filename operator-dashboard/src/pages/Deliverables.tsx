import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deliverablesApi } from '@/api/deliverables';
import type { Deliverable, DeliverableStatus, MarkDeliveredInput } from '@/types/domain';
import {
  Filter,
  Link as LinkIcon,
  RefreshCw,
  CheckCircle,
  X,
  Download,
  Mail,
  Search,
  FileText,
  Clock,
  Send,
  Eye,
  MoreVertical,
  Calendar,
  Package,
} from 'lucide-react';
import { format, isAfter, isBefore, parseISO } from 'date-fns';
import { DeliverableDrawer } from '@/components/deliverables/DeliverableDrawer';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { formatFileSize } from '@/utils/formatters';
import { Button, Badge, Card, CardContent, Input, Textarea } from '@/components/ui';

interface MarkDialogProps {
  deliverable: Deliverable | null;
  onClose: () => void;
  onSubmit: (input: MarkDeliveredInput) => void;
  isSubmitting: boolean;
}

function MarkDeliveredDialog({ deliverable, onClose, onSubmit, isSubmitting }: MarkDialogProps) {
  const [proofUrl, setProofUrl] = useState('');
  const [proofNotes, setProofNotes] = useState('');
  if (!deliverable) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
      <div className="w-full max-w-lg rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Mark Delivered</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Deliverable ID: {deliverable.id}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="space-y-4">
          <Input
            type="url"
            label="Proof URL (optional)"
            value={proofUrl}
            onChange={(e) => setProofUrl(e.target.value)}
            placeholder="https://example.com/proof"
            helperText="Link to email confirmation, screenshot, or other proof"
          />
          <Textarea
            label="Delivery Notes (optional)"
            value={proofNotes}
            onChange={(e) => setProofNotes(e.target.value)}
            rows={3}
            placeholder="Add any relevant notes about the delivery..."
          />
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="success"
            disabled={isSubmitting}
            onClick={() =>
              onSubmit({
                deliveredAt: new Date().toISOString(),
                proofUrl: proofUrl || undefined,
                proofNotes: proofNotes || undefined,
              })
            }
          >
            <CheckCircle className="h-4 w-4" />
            {isSubmitting ? 'Marking Delivered...' : 'Mark Delivered'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function Deliverables() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const projectId = searchParams.get('projectId') || undefined;
  const clientId = searchParams.get('clientId') || undefined;

  const [status, setStatus] = useState<DeliverableStatus | ''>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [formatFilter, setFormatFilter] = useState<string>('');
  const [viewMode, setViewMode] = useState<'grouped' | 'list'>('grouped');
  const [selected, setSelected] = useState<Deliverable | null>(null);
  const [selectedForEmail, setSelectedForEmail] = useState<Deliverable | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['deliverables', { status, projectId, clientId }],
    queryFn: () => deliverablesApi.list({
      status: status || undefined,
      projectId,
      clientId,
    }),
  });

  const deliverables = data ?? [];

  // Calculate stats
  const stats = useMemo(() => {
    return {
      total: deliverables.length,
      draft: deliverables.filter(d => d.status === 'draft').length,
      ready: deliverables.filter(d => d.status === 'ready').length,
      delivered: deliverables.filter(d => d.status === 'delivered').length,
    };
  }, [deliverables]);

  // Filter deliverables
  const filteredDeliverables = useMemo(() => {
    let filtered = deliverables;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(d =>
        d.path.toLowerCase().includes(query) ||
        d.id.toLowerCase().includes(query) ||
        d.clientId.toLowerCase().includes(query) ||
        d.projectId.toLowerCase().includes(query)
      );
    }

    // Format filter
    if (formatFilter) {
      filtered = filtered.filter(d => d.format === formatFilter);
    }

    return filtered;
  }, [deliverables, searchQuery, formatFilter]);

  const clearFilters = () => {
    setStatus('');
    setSearchQuery('');
    setFormatFilter('');
    setSearchParams({});
  };

  const groups = useMemo(() => {
    const map = new Map<string, Deliverable[]>();
    filteredDeliverables.forEach((d) => {
      const key = `${d.clientId}::${d.projectId}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(d);
    });
    return Array.from(map.entries()).map(([key, items]) => {
      const [clientId, projectId] = key.split('::');
      return { clientId, projectId, items };
    });
  }, [filteredDeliverables]);

  const markDelivered = useMutation({
    mutationFn: (input: MarkDeliveredInput) => {
      if (!selected) throw new Error('No deliverable selected');
      return deliverablesApi.markDelivered(selected.id, input);
    },
    onSuccess: async () => {
      setSelected(null);
      await qc.invalidateQueries({ queryKey: ['deliverables'] });
    },
  });

  // Download handler
  const handleDownload = async (deliverable: Deliverable) => {
    try {
      setDownloadingId(deliverable.id);
      const { blob, filename } = await deliverablesApi.download(deliverable.id);

      // Create download link and trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
      // Could add toast notification here
      alert('Failed to download file. Please try again.');
    } finally {
      setDownloadingId(null);
    }
  };


  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
            Deliverables
            {projectId && <span className="text-base font-normal text-neutral-600 dark:text-neutral-400"> • Project {projectId}</span>}
            {clientId && <span className="text-base font-normal text-neutral-600 dark:text-neutral-400"> • Client {clientId}</span>}
          </h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Track export outputs, delivery status, and proof documentation</p>
        </div>
        <div className="flex items-center gap-2">
          {(projectId || clientId || status || searchQuery || formatFilter) && (
            <Button variant="secondary" onClick={clearFilters}>
              <X className="h-4 w-4" />
              Clear Filters
            </Button>
          )}
          <Button variant="secondary" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </header>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="rounded-lg bg-primary-100 dark:bg-primary-900/20 p-2">
                <Package className="h-5 w-5 text-primary-600 dark:text-primary-400" />
              </div>
              <span className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{stats.total}</span>
            </div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">Total Deliverables</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="rounded-lg bg-neutral-100 dark:bg-neutral-800 p-2">
                <FileText className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
              </div>
              <span className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{stats.draft}</span>
            </div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">Draft</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="rounded-lg bg-indigo-100 dark:bg-indigo-900/20 p-2">
                <Clock className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <span className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{stats.ready}</span>
            </div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">Ready to Send</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="rounded-lg bg-green-100 dark:bg-green-900/20 p-2">
                <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <span className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{stats.delivered}</span>
            </div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">Delivered</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          {/* Search */}
          <div className="relative flex-1 lg:max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400 dark:text-neutral-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by path, ID, client, or project..."
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 pl-10 pr-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 placeholder:text-neutral-400 dark:placeholder:text-neutral-500"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2">
              <Filter className="h-4 w-4 text-neutral-500 dark:text-neutral-400" />
              <select
                className="bg-transparent text-sm text-neutral-800 dark:text-neutral-200 outline-none"
                value={status}
                onChange={(e) => setStatus(e.target.value as DeliverableStatus | '')}
              >
                <option value="">All statuses</option>
                <option value="draft">Draft</option>
                <option value="ready">Ready</option>
                <option value="delivered">Delivered</option>
              </select>
            </div>

            <div className="flex items-center gap-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2">
              <FileText className="h-4 w-4 text-neutral-500 dark:text-neutral-400" />
              <select
                className="bg-transparent text-sm text-neutral-800 dark:text-neutral-200 outline-none"
                value={formatFilter}
                onChange={(e) => setFormatFilter(e.target.value)}
              >
                <option value="">All formats</option>
                <option value="txt">TXT</option>
                <option value="docx">DOCX</option>
                <option value="pdf">PDF</option>
                <option value="md">Markdown</option>
              </select>
            </div>

            {/* View Toggle */}
            <div className="flex items-center gap-1 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-1">
              <button
                onClick={() => setViewMode('grouped')}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  viewMode === 'grouped'
                    ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                Grouped
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  viewMode === 'list'
                    ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100'
                    : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                List
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Deliverables Content */}
      <div>
        {isLoading && (
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-12 text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 dark:border-primary-500 border-r-transparent"></div>
            <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">Loading deliverables...</p>
          </div>
        )}

        {isError && (
          <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4">
            <p className="text-sm text-red-600 dark:text-red-400">Failed to load deliverables. Please try again.</p>
          </div>
        )}

        {!isLoading && !isError && filteredDeliverables.length === 0 && (
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-12 text-center">
            <Package className="mx-auto h-12 w-12 text-neutral-300 dark:text-neutral-600" />
            <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-400">No deliverables found.</p>
            {(searchQuery || formatFilter || status) && (
              <button
                onClick={clearFilters}
                className="mt-4 text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
              >
                Clear filters
              </button>
            )}
          </div>
        )}

        {/* Grouped View */}
        {!isLoading && !isError && viewMode === 'grouped' && groups.length > 0 && (
          <div className="space-y-4">
            {groups.map((group) => (
              <div key={`${group.clientId}-${group.projectId}`} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-sm">
                <div className="flex items-center justify-between border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 px-4 py-3">
                  <div>
                    <button
                      onClick={() => navigate(`/dashboard/clients/${group.clientId}`)}
                      className="text-sm font-semibold text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 hover:underline"
                      title={`View client ${group.clientId}`}
                    >
                      Client: {group.clientId}
                    </button>
                    <button
                      onClick={() => navigate(`/dashboard/projects/${group.projectId}`)}
                      className="ml-4 text-xs text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:underline"
                      title={`View project ${group.projectId}`}
                    >
                      Project: {group.projectId}
                    </button>
                  </div>
                  <span className="text-xs text-neutral-500 dark:text-neutral-400">{group.items.length} deliverable{group.items.length !== 1 ? 's' : ''}</span>
                </div>
                <div className="divide-y divide-neutral-200 dark:divide-neutral-700">
                  {group.items.map((d) => (
                    <div key={d.id} className="flex items-center justify-between px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-800">
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                            {d.format.toUpperCase()}
                          </span>
                          <Badge variant={d.status === 'draft' ? 'default' : d.status === 'ready' ? 'info' : 'success'}>{d.status}</Badge>
                          <span className="text-xs text-neutral-500 dark:text-neutral-400">{formatFileSize(d.fileSizeBytes)}</span>
                        </div>
                        <p className="text-sm text-neutral-600 dark:text-neutral-400">{d.path}</p>
                        <div className="flex items-center gap-4 text-xs text-neutral-500 dark:text-neutral-400">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            Created {format(new Date(d.createdAt), 'MMM d, yyyy')}
                          </span>
                          {d.runId && <span>Run #{d.runId}</span>}
                          {d.deliveredAt && (
                            <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                              <CheckCircle className="h-3 w-3" />
                              Delivered {format(new Date(d.deliveredAt), 'MMM d, yyyy')}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setSelected(d)}
                          className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
                        >
                          <Eye className="h-3 w-3" />
                          View
                        </button>
                        <button
                          onClick={() => handleDownload(d)}
                          disabled={downloadingId === d.id}
                          className="inline-flex items-center gap-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <Download className={`h-3 w-3 ${downloadingId === d.id ? 'animate-bounce' : ''}`} />
                          {downloadingId === d.id ? 'Downloading...' : 'Download'}
                        </button>
                        {d.status !== 'delivered' && (
                          <button
                            onClick={() => setSelected(d)}
                            className="inline-flex items-center gap-1 rounded-lg bg-green-600 dark:bg-green-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 dark:hover:bg-green-600"
                          >
                            <CheckCircle className="h-3 w-3" />
                            Mark Delivered
                          </button>
                        )}
                        {d.proofUrl && (
                          <a
                            href={d.proofUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded-lg border border-primary-300 dark:border-primary-600 bg-primary-50 dark:bg-primary-900/20 px-3 py-1.5 text-xs font-medium text-primary-700 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/30"
                          >
                            <LinkIcon className="h-3 w-3" />
                            Proof
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* List View */}
        {!isLoading && !isError && viewMode === 'list' && filteredDeliverables.length > 0 && (
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-600 dark:text-neutral-400">File</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-600 dark:text-neutral-400">Client/Project</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-600 dark:text-neutral-400">Format</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-600 dark:text-neutral-400">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-600 dark:text-neutral-400">Created</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-600 dark:text-neutral-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
                {filteredDeliverables.map((d) => (
                  <tr key={d.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
                        <div>
                          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{d.path}</p>
                          <p className="text-xs text-neutral-500 dark:text-neutral-400">{formatFileSize(d.fileSizeBytes)}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => navigate(`/dashboard/clients/${d.clientId}`)}
                        className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
                      >
                        {d.clientId}
                      </button>
                      <p className="text-xs text-neutral-500 dark:text-neutral-400">{d.projectId}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-neutral-100 dark:bg-neutral-800 px-2 py-1 text-xs font-medium text-neutral-700 dark:text-neutral-300">
                        {d.format.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={d.status === 'draft' ? 'default' : d.status === 'ready' ? 'info' : 'success'}>{d.status}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-neutral-900 dark:text-neutral-100">{format(new Date(d.createdAt), 'MMM d, yyyy')}</p>
                      {d.deliveredAt && (
                        <p className="text-xs text-green-600 dark:text-green-400">Delivered {format(new Date(d.deliveredAt), 'MMM d')}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setSelected(d)}
                          className="rounded-lg p-1 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300"
                          title="View details"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDownload(d)}
                          disabled={downloadingId === d.id}
                          className="rounded-lg p-1 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300 disabled:opacity-50 disabled:cursor-not-allowed"
                          title={downloadingId === d.id ? 'Downloading...' : 'Download'}
                        >
                          <Download className={`h-4 w-4 ${downloadingId === d.id ? 'animate-bounce' : ''}`} />
                        </button>
                        {d.status !== 'delivered' && (
                          <button
                            onClick={() => setSelected(d)}
                            className="rounded-lg bg-green-600 dark:bg-green-700 p-1 text-white hover:bg-green-700 dark:hover:bg-green-600"
                            title="Mark delivered"
                          >
                            <CheckCircle className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <MarkDeliveredDialog
        deliverable={selected}
        onClose={() => setSelected(null)}
        onSubmit={(input) => markDelivered.mutate(input)}
        isSubmitting={markDelivered.isPending}
      />
      <DeliverableDrawer deliverable={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
