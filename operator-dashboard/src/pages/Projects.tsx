import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '@/api/projects';
import { generatorApi } from '@/api/generator';
import { Project } from '@/types/domain';
import { format } from 'date-fns';
import { RefreshCw, Filter, Play, Sparkles, FileText, X, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { NewProjectDialog } from '@/components/projects/NewProjectDialog';
import { Pagination } from '@/components/ui/Pagination';
import { Button, Badge, Card, CardContent, Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui';
import { StatusProgressBar } from '@/components/ui/StatusProgressBar';
import { QuickActionsDropdown } from '@/components/ui/QuickActionsDropdown';

export default function Projects() {
  const [searchParams, setSearchParams] = useSearchParams();
  const clientId = searchParams.get('clientId') || undefined;

  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<Project['status'] | ''>('');
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [sortField, setSortField] = useState<keyof Project | ''>('');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
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

  // Fetch clients to map client IDs to names
  const { data: clientsData } = useQuery({
    queryKey: ['clients'],
    queryFn: () => import('@/api/clients').then(m => m.clientsApi.list()),
  });

  // Extract projects from paginated response (Week 3 optimization)
  const projects = data?.items ?? [];
  const paginationMeta = data?.metadata;

  // Helper to get client name from client ID
  const getClientName = (clientId: string): string => {
    const client = clientsData?.find(c => c.id === clientId);
    return client?.name || clientId; // Fallback to ID if name not found
  };

  // Sort projects based on current sort field and direction
  const sortedProjects = useMemo(() => {
    if (!sortField) return projects;

    return [...projects].sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];

      // Handle null/undefined values
      if (aValue == null && bValue == null) return 0;
      if (aValue == null) return sortDirection === 'asc' ? 1 : -1;
      if (bValue == null) return sortDirection === 'asc' ? -1 : 1;

      // Special handling for status field - use workflow order
      if (sortField === 'status') {
        const statusOrder = {
          'draft': 0,
          'processing': 1,
          'qa_review': 2,
          'ready': 3,
          'delivered': 4
        };
        const aOrder = statusOrder[aValue as keyof typeof statusOrder] ?? 999;
        const bOrder = statusOrder[bValue as keyof typeof statusOrder] ?? 999;
        const comparison = aOrder - bOrder;
        return sortDirection === 'asc' ? comparison : -comparison;
      }

      // Compare values
      let comparison = 0;
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        // Use localeCompare with options for proper alphabetical sorting
        comparison = aValue.localeCompare(bValue, undefined, { sensitivity: 'base' });
      } else if (typeof aValue === 'number' && typeof bValue === 'number') {
        comparison = aValue - bValue;
      } else if (aValue instanceof Date && bValue instanceof Date) {
        comparison = aValue.getTime() - bValue.getTime();
      } else {
        // For arrays or other types, convert to string
        comparison = String(aValue).localeCompare(String(bValue), undefined, { sensitivity: 'base' });
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [projects, sortField, sortDirection]);

  // Handle sort toggling
  const handleSort = (field: keyof Project) => {
    if (sortField === field) {
      // Toggle direction if clicking same field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new field with ascending direction
      setSortField(field);
      setSortDirection('asc');
    }
  };

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
    onSuccess: (run) => {
      console.log('Generation started:', run);
      qc.invalidateQueries({ queryKey: ['projects'] });
      qc.invalidateQueries({ queryKey: ['runs'] });
      // Show success message
      alert(`Content generation started! Run ID: ${run.id}`);
    },
    onError: (error) => {
      console.error('Generation error:', error);
      alert(`Failed to start generation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    },
  });

  return (
    <div className="space-y-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
            Projects
            {clientId && <span className="text-base font-normal text-neutral-600 dark:text-neutral-400"> • {getClientName(clientId)}</span>}
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
                <TableHead>
                  <button
                    onClick={() => handleSort('name')}
                    className="flex items-center gap-1 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors"
                  >
                    Project
                    {sortField === 'name' ? (
                      sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                    ) : (
                      <ArrowUpDown className="h-3 w-3 opacity-30" />
                    )}
                  </button>
                </TableHead>
                <TableHead>
                  <button
                    onClick={() => handleSort('clientId')}
                    className="flex items-center gap-1 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors"
                  >
                    Client
                    {sortField === 'clientId' ? (
                      sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                    ) : (
                      <ArrowUpDown className="h-3 w-3 opacity-30" />
                    )}
                  </button>
                </TableHead>
                <TableHead>
                  <button
                    onClick={() => handleSort('status')}
                    className="flex items-center gap-1 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors"
                  >
                    Status
                    {sortField === 'status' ? (
                      sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                    ) : (
                      <ArrowUpDown className="h-3 w-3 opacity-30" />
                    )}
                  </button>
                </TableHead>
                <TableHead>Templates</TableHead>
                <TableHead>
                  <button
                    onClick={() => handleSort('lastRunAt')}
                    className="flex items-center gap-1 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors"
                  >
                    Last Run
                    {sortField === 'lastRunAt' ? (
                      sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                    ) : (
                      <ArrowUpDown className="h-3 w-3 opacity-30" />
                    )}
                  </button>
                </TableHead>
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
              {!isLoading && !isError && sortedProjects.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-neutral-500 dark:text-neutral-400 py-6">
                    No projects found.
                  </TableCell>
                </TableRow>
              )}
              {sortedProjects.map((project) => (
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
                      title={`View all projects for ${getClientName(project.clientId)}`}
                      className="p-0 h-auto"
                    >
                      {getClientName(project.clientId)}
                    </Button>
                  </TableCell>
                  <TableCell>
                    <StatusProgressBar status={project.status} size="sm" />
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
                        variant="primary"
                        size="xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          generateMutation.mutate(project);
                        }}
                        disabled={generateMutation.isPending}
                      >
                        <Play className="h-4 w-4" />
                        {generateMutation.isPending ? 'Generating...' : 'Generate'}
                      </Button>
                      <QuickActionsDropdown
                        size="sm"
                        actions={[
                          {
                            label: 'View Details',
                            icon: 'view',
                            onClick: () => navigate(`/dashboard/projects/${project.id}`),
                          },
                          {
                            label: 'Open Wizard',
                            icon: 'edit',
                            onClick: () => navigate('/dashboard/wizard', { state: { projectId: project.id } }),
                          },
                          {
                            label: 'View Deliverables',
                            icon: 'download',
                            onClick: () => navigate(`/dashboard/deliverables?projectId=${project.id}`),
                            dividerAfter: true,
                          },
                          {
                            label: 'Duplicate Project',
                            icon: 'copy',
                            onClick: () => {
                              // TODO: Implement duplicate functionality
                              alert('Duplicate functionality coming soon');
                            },
                          },
                          {
                            label: 'Export Project',
                            icon: 'external',
                            onClick: () => {
                              // TODO: Implement export functionality
                              alert('Export functionality coming soon');
                            },
                            dividerAfter: true,
                          },
                          {
                            label: 'Archive Project',
                            icon: 'archive',
                            onClick: () => {
                              if (confirm(`Archive project "${project.name}"?`)) {
                                // TODO: Implement archive functionality
                                alert('Archive functionality coming soon');
                              }
                            },
                          },
                        ]}
                      />
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
