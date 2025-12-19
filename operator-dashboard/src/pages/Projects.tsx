import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '@/api/projects';
import { generatorApi } from '@/api/generator';
import type { Project } from '@/types/domain';
import { format } from 'date-fns';
import { RefreshCw, Filter, Play, Sparkles, FileText, X } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { NewProjectDialog } from '@/components/projects/NewProjectDialog';
import { Pagination } from '@/components/ui/Pagination';

function StatusBadge({ status }: { status: Project['status'] }) {
  const styles: Record<Project['status'], string> = {
    draft: 'bg-slate-100 text-slate-700',
    ready: 'bg-emerald-100 text-emerald-700',
    generating: 'bg-blue-100 text-blue-700',
    qa: 'bg-amber-100 text-amber-700',
    exported: 'bg-indigo-100 text-indigo-700',
    delivered: 'bg-green-100 text-green-700',
    error: 'bg-rose-100 text-rose-700',
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${styles[status]}`}>
      {status}
    </span>
  );
}

export default function Projects() {
  const [searchParams, setSearchParams] = useSearchParams();
  const clientId = searchParams.get('clientId') || undefined;

  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<Project['status'] | ''>('');
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data, isLoading, refetch, isError } = useQuery({
    queryKey: ['projects', { search, status, clientId, page: currentPage, cursor, pageSize }],
    queryFn: () => projectsApi.list({
      search: search || undefined,
      status: status || undefined,
      clientId,
      page: cursor ? undefined : currentPage,
      cursor,
      page_size: pageSize,
    }),
  });

  // Extract projects from paginated response (Week 3 optimization)
  const projects = data?.items ?? [];
  const paginationMeta = data?.metadata;

  const clearClientFilter = () => {
    setSearchParams({});
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    setCursor(undefined); // Reset cursor when using page numbers
  };

  const handleCursorChange = (newCursor: string) => {
    setCursor(newCursor);
    if (paginationMeta?.strategy === 'cursor') {
      setCurrentPage((prev) => (newCursor === paginationMeta.next_cursor ? prev + 1 : prev - 1));
    }
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize);
    setCurrentPage(1); // Reset to first page when changing page size
    setCursor(undefined);
  };

  const generateMutation = useMutation({
    mutationFn: (project: Project) =>
      generatorApi.generateAll({
        projectId: project.id,
        clientId: project.clientId,
        isBatch: true,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] });
      qc.invalidateQueries({ queryKey: ['runs'] });
    },
  });

  return (
    <div className="space-y-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            Projects
            {clientId && <span className="text-base font-normal text-slate-600"> • Client {clientId}</span>}
          </h1>
          <p className="text-sm text-slate-600">Search, filter, and manage active content generation projects.</p>
        </div>
        <div className="flex items-center gap-2">
          {clientId && (
            <button
              onClick={clearClientFilter}
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            >
              <X className="h-4 w-4" />
              Clear Client Filter
            </button>
          )}
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </header>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-1 flex-col gap-2 sm:flex-row">
            <div className="flex flex-1 items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search projects or ids"
                className="w-full bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
              />
            </div>
            <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2">
              <Filter className="h-4 w-4 text-slate-500" />
              <select
                className="bg-transparent text-sm text-slate-800 outline-none"
                value={status}
                onChange={(e) => setStatus(e.target.value as Project['status'] | '')}
              >
                <option value="">All statuses</option>
                {['draft', 'ready', 'generating', 'qa', 'exported', 'delivered', 'error'].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setNewProjectOpen(true)}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              New Project
            </button>
          </div>
        </div>

        <div className="mt-4 overflow-hidden rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Project</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Client</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Templates</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Last Run</th>
                <th className="px-4 py-3 text-right font-semibold text-slate-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {isLoading && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                    Loading projects...
                  </td>
                </tr>
              )}
              {isError && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-rose-600">
                    Failed to load projects.
                  </td>
                </tr>
              )}
              {!isLoading && !isError && projects.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                    No projects found.
                  </td>
                </tr>
              )}
              {projects.map((project) => (
                <tr key={project.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-900">{project.name}</div>
                    <div className="text-xs text-slate-500">ID: {project.id}</div>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => navigate(`/dashboard/projects?clientId=${project.clientId}`)}
                      className="text-sm text-blue-600 hover:text-blue-700 hover:underline"
                      title={`View all projects for client ${project.clientId}`}
                    >
                      {project.clientId}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={project.status} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-xs text-slate-600">
                      {project.templates.slice(0, 2).join(', ')}
                      {project.templates.length > 2 ? ` +${project.templates.length - 2}` : ''}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-slate-700">
                      {project.lastRunAt ? format(new Date(project.lastRunAt), 'PP p') : '—'}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
                        onClick={() => navigate(`/dashboard/deliverables?projectId=${project.id}`)}
                        title="View deliverables for this project"
                      >
                        <FileText className="h-4 w-4" />
                        Deliverables
                      </button>
                      <button
                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
                        onClick={() => navigate('/dashboard/wizard', { state: { projectId: project.id } })}
                      >
                        <Sparkles className="h-4 w-4" />
                        Wizard
                      </button>
                      <button
                        onClick={() => generateMutation.mutate(project)}
                        disabled={generateMutation.isPending}
                        className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
                      >
                        <Play className="h-4 w-4" />
                        {generateMutation.isPending ? 'Generating...' : 'Generate'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination controls (Week 3 optimization) */}
        <Pagination
          metadata={paginationMeta}
          currentPage={currentPage}
          onPageChange={handlePageChange}
          onCursorChange={handleCursorChange}
          showPageSize
          pageSize={pageSize}
          onPageSizeChange={handlePageSizeChange}
        />
      </div>

      <NewProjectDialog
        open={newProjectOpen}
        onOpenChange={setNewProjectOpen}
        onSuccess={(project) => navigate('/dashboard/wizard', { state: { projectId: project.id } })}
      />
    </div>
  );
}
