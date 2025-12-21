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
import { Button, Badge, Card, CardContent, Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui';

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
          <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
            Projects
            {clientId && <span className="text-base font-normal text-neutral-600 dark:text-neutral-400"> • Client {clientId}</span>}
          </h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">Search, filter, and manage active content generation projects.</p>
        </div>
        <div className="flex items-center gap-2">
          {clientId && (
            <Button variant="secondary" size="sm" onClick={clearClientFilter}>
              <X className="h-4 w-4" />
              Clear Client Filter
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </header>

      <Card>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 flex-col gap-2 sm:flex-row">
              <div className="flex flex-1 items-center gap-2 rounded-md border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 px-3 py-2">
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search projects or ids"
                  className="w-full bg-transparent text-sm text-neutral-800 dark:text-neutral-200 outline-none placeholder:text-neutral-400 dark:placeholder:text-neutral-500"
                />
              </div>
              <div className="flex items-center gap-2 rounded-md border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2">
                <Filter className="h-4 w-4 text-neutral-500 dark:text-neutral-400" />
                <select
                  className="bg-transparent text-sm text-neutral-800 dark:text-neutral-200 outline-none"
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
              <Button variant="primary" size="sm" onClick={() => setNewProjectOpen(true)}>
                New Project
              </Button>
            </div>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Project</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Templates</TableHead>
                <TableHead>Last Run</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-neutral-500 dark:text-neutral-400 py-6">
                    Loading projects...
                  </TableCell>
                </TableRow>
              )}
              {isError && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-rose-600 dark:text-rose-400 py-6">
                    Failed to load projects.
                  </TableCell>
                </TableRow>
              )}
              {!isLoading && !isError && projects.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-neutral-500 dark:text-neutral-400 py-6">
                    No projects found.
                  </TableCell>
                </TableRow>
              )}
              {projects.map((project) => (
                <TableRow key={project.id}>
                  <TableCell>
                    <div className="font-semibold text-neutral-900 dark:text-neutral-100">{project.name}</div>
                    <div className="text-xs text-neutral-500 dark:text-neutral-400">ID: {project.id}</div>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => navigate(`/dashboard/projects?clientId=${project.clientId}`)}
                      title={`View all projects for client ${project.clientId}`}
                      className="p-0 h-auto"
                    >
                      {project.clientId}
                    </Button>
                  </TableCell>
                  <TableCell>
                    <Badge variant={project.status}>{project.status}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="text-xs text-neutral-600 dark:text-neutral-400">
                      {project.templates.slice(0, 2).join(', ')}
                      {project.templates.length > 2 ? ` +${project.templates.length - 2}` : ''}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm text-neutral-700 dark:text-neutral-300">
                      {project.lastRunAt ? format(new Date(project.lastRunAt), 'PP p') : '—'}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => navigate(`/dashboard/deliverables?projectId=${project.id}`)}
                        title="View deliverables for this project"
                      >
                        <FileText className="h-4 w-4" />
                        Deliverables
                      </Button>
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => navigate('/dashboard/wizard', { state: { projectId: project.id } })}
                      >
                        <Sparkles className="h-4 w-4" />
                        Wizard
                      </Button>
                      <Button
                        variant="primary"
                        size="xs"
                        onClick={() => generateMutation.mutate(project)}
                        disabled={generateMutation.isPending}
                      >
                        <Play className="h-4 w-4" />
                        {generateMutation.isPending ? 'Generating...' : 'Generate'}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

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
        </CardContent>
      </Card>

      <NewProjectDialog
        open={newProjectOpen}
        onOpenChange={setNewProjectOpen}
        onSuccess={(project) => navigate('/dashboard/wizard', { state: { projectId: project.id } })}
      />
    </div>
  );
}
