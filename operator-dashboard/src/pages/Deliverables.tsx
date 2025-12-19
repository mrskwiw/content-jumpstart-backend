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

function StatusChip({ status }: { status: DeliverableStatus }) {
  const map: Record<DeliverableStatus, string> = {
    draft: 'bg-slate-100 text-slate-700',
    ready: 'bg-indigo-100 text-indigo-700',
    delivered: 'bg-green-100 text-green-700',
  };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${map[status]}`}>{status}</span>;
}

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
      <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Mark Delivered</h3>
            <p className="text-sm text-slate-600 mt-1">Deliverable ID: {deliverable.id}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Proof URL <span className="text-slate-400">(optional)</span>
            </label>
            <input
              type="url"
              value={proofUrl}
              onChange={(e) => setProofUrl(e.target.value)}
              placeholder="https://example.com/proof"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="text-xs text-slate-500 mt-1">Link to email confirmation, screenshot, or other proof</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Delivery Notes <span className="text-slate-400">(optional)</span>
            </label>
            <textarea
              value={proofNotes}
              onChange={(e) => setProofNotes(e.target.value)}
              rows={3}
              placeholder="Add any relevant notes about the delivery..."
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            disabled={isSubmitting}
            onClick={() =>
              onSubmit({
                deliveredAt: new Date().toISOString(),
                proofUrl: proofUrl || undefined,
                proofNotes: proofNotes || undefined,
              })
            }
            className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700 disabled:opacity-50"
          >
            <CheckCircle className="h-4 w-4" />
            {isSubmitting ? 'Marking Delivered...' : 'Mark Delivered'}
          </button>
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

  // Mock file sizes (would come from backend)
  const getFileSize = (deliverable: Deliverable) => {
    const sizes: Record<string, string> = {
      'txt': '24 KB',
      'docx': '156 KB',
      'pdf': '432 KB',
      'md': '18 KB',
    };
    return sizes[deliverable.format] || '0 KB';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            Deliverables
            {projectId && <span className="text-base font-normal text-slate-600"> • Project {projectId}</span>}
            {clientId && <span className="text-base font-normal text-slate-600"> • Client {clientId}</span>}
          </h1>
          <p className="text-sm text-slate-600 mt-1">Track export outputs, delivery status, and proof documentation</p>
        </div>
        <div className="flex items-center gap-2">
          {(projectId || clientId || status || searchQuery || formatFilter) && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <X className="h-4 w-4" />
              Clear Filters
            </button>
          )}
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </header>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="rounded-lg bg-blue-100 p-2">
              <Package className="h-5 w-5 text-blue-600" />
            </div>
            <span className="text-2xl font-semibold text-slate-900">{stats.total}</span>
          </div>
          <p className="text-sm text-slate-600 mt-2">Total Deliverables</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="rounded-lg bg-slate-100 p-2">
              <FileText className="h-5 w-5 text-slate-600" />
            </div>
            <span className="text-2xl font-semibold text-slate-900">{stats.draft}</span>
          </div>
          <p className="text-sm text-slate-600 mt-2">Draft</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="rounded-lg bg-indigo-100 p-2">
              <Clock className="h-5 w-5 text-indigo-600" />
            </div>
            <span className="text-2xl font-semibold text-slate-900">{stats.ready}</span>
          </div>
          <p className="text-sm text-slate-600 mt-2">Ready to Send</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="rounded-lg bg-green-100 p-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
            <span className="text-2xl font-semibold text-slate-900">{stats.delivered}</span>
          </div>
          <p className="text-sm text-slate-600 mt-2">Delivered</p>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          {/* Search */}
          <div className="relative flex-1 lg:max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by path, ID, client, or project..."
              className="w-full rounded-lg border border-slate-300 pl-10 pr-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
              <Filter className="h-4 w-4 text-slate-500" />
              <select
                className="bg-transparent text-sm text-slate-800 outline-none"
                value={status}
                onChange={(e) => setStatus(e.target.value as DeliverableStatus | '')}
              >
                <option value="">All statuses</option>
                <option value="draft">Draft</option>
                <option value="ready">Ready</option>
                <option value="delivered">Delivered</option>
              </select>
            </div>

            <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
              <FileText className="h-4 w-4 text-slate-500" />
              <select
                className="bg-transparent text-sm text-slate-800 outline-none"
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
            <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1">
              <button
                onClick={() => setViewMode('grouped')}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  viewMode === 'grouped'
                    ? 'bg-slate-100 text-slate-900'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Grouped
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  viewMode === 'list'
                    ? 'bg-slate-100 text-slate-900'
                    : 'text-slate-600 hover:text-slate-900'
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
          <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
            <p className="mt-4 text-sm text-slate-600">Loading deliverables...</p>
          </div>
        )}

        {isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-600">Failed to load deliverables. Please try again.</p>
          </div>
        )}

        {!isLoading && !isError && filteredDeliverables.length === 0 && (
          <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
            <Package className="mx-auto h-12 w-12 text-slate-300" />
            <p className="mt-4 text-sm text-slate-600">No deliverables found.</p>
            {(searchQuery || formatFilter || status) && (
              <button
                onClick={clearFilters}
                className="mt-4 text-sm text-blue-600 hover:text-blue-700"
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
              <div key={`${group.clientId}-${group.projectId}`} className="rounded-lg border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
                  <div>
                    <button
                      onClick={() => navigate(`/dashboard/clients/${group.clientId}`)}
                      className="text-sm font-semibold text-blue-600 hover:text-blue-700 hover:underline"
                      title={`View client ${group.clientId}`}
                    >
                      Client: {group.clientId}
                    </button>
                    <button
                      onClick={() => navigate(`/dashboard/projects/${group.projectId}`)}
                      className="ml-4 text-xs text-slate-600 hover:text-slate-900 hover:underline"
                      title={`View project ${group.projectId}`}
                    >
                      Project: {group.projectId}
                    </button>
                  </div>
                  <span className="text-xs text-slate-500">{group.items.length} deliverable{group.items.length !== 1 ? 's' : ''}</span>
                </div>
                <div className="divide-y divide-slate-200">
                  {group.items.map((d) => (
                    <div key={d.id} className="flex items-center justify-between px-4 py-3 hover:bg-slate-50">
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold text-slate-900">
                            {d.format.toUpperCase()}
                          </span>
                          <StatusChip status={d.status} />
                          <span className="text-xs text-slate-500">{getFileSize(d)}</span>
                        </div>
                        <p className="text-sm text-slate-600">{d.path}</p>
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            Created {format(new Date(d.createdAt), 'MMM d, yyyy')}
                          </span>
                          {d.runId && <span>Run #{d.runId}</span>}
                          {d.deliveredAt && (
                            <span className="flex items-center gap-1 text-green-600">
                              <CheckCircle className="h-3 w-3" />
                              Delivered {format(new Date(d.deliveredAt), 'MMM d, yyyy')}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setSelected(d)}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                        >
                          <Eye className="h-3 w-3" />
                          View
                        </button>
                        <button
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                        >
                          <Download className="h-3 w-3" />
                          Download
                        </button>
                        {d.status !== 'delivered' && (
                          <button
                            onClick={() => setSelected(d)}
                            className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
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
                            className="inline-flex items-center gap-1 rounded-lg border border-blue-300 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100"
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
          <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">File</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Client/Project</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Format</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600">Created</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredDeliverables.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-slate-400" />
                        <div>
                          <p className="text-sm font-medium text-slate-900">{d.path}</p>
                          <p className="text-xs text-slate-500">{getFileSize(d)}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => navigate(`/dashboard/clients/${d.clientId}`)}
                        className="text-sm text-blue-600 hover:underline"
                      >
                        {d.clientId}
                      </button>
                      <p className="text-xs text-slate-500">{d.projectId}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                        {d.format.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusChip status={d.status} />
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-slate-900">{format(new Date(d.createdAt), 'MMM d, yyyy')}</p>
                      {d.deliveredAt && (
                        <p className="text-xs text-green-600">Delivered {format(new Date(d.deliveredAt), 'MMM d')}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setSelected(d)}
                          className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                          title="View details"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button
                          className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        {d.status !== 'delivered' && (
                          <button
                            onClick={() => setSelected(d)}
                            className="rounded-lg bg-green-600 p-1 text-white hover:bg-green-700"
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
