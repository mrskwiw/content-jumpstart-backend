import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { deliverablesApi } from '@/api/deliverables';
import {
  Users,
  Search,
  Filter,
  Plus,
  ArrowUpDown,
  Mail,
  Briefcase,
  DollarSign,
  TrendingUp,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ClientWithMetrics {
  id: string;
  name: string;
  email?: string;
  status?: string;
  tags?: string[];
  totalProjects: number;
  activeProjects: number;
  completedProjects: number;
  totalRevenue: number;
  lastActivity?: Date;
  packageTier?: string;
}

export default function Clients() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [packageFilter, setPackageFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'name' | 'projects' | 'revenue' | 'activity'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Fetch data
  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  });

  const { data: projectsResponse } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list({}),
  });

  const projects = projectsResponse?.items ?? [];

  const { data: deliverables = [] } = useQuery({
    queryKey: ['deliverables'],
    queryFn: () => deliverablesApi.list({}),
  });

  // Calculate metrics for each client
  const clientsWithMetrics: ClientWithMetrics[] = useMemo(() => {
    return clients.map(client => {
      const clientProjects = projects.filter(p => p.clientId === client.id);
      const activeProjects = clientProjects.filter(p =>
        p.status !== 'delivered' && p.status !== 'exported'
      ).length;
      const completedProjects = clientProjects.filter(p =>
        p.status === 'delivered' || p.status === 'exported'
      ).length;

      // Mock revenue calculation (would come from billing API)
      const totalRevenue = completedProjects * 1800; // Avg $1,800/project

      // Last activity from most recent project update
      const lastActivity = clientProjects
        .filter(p => p.lastRunAt)
        .sort((a, b) => new Date(b.lastRunAt!).getTime() - new Date(a.lastRunAt!).getTime())[0]
        ?.lastRunAt
        ? new Date(clientProjects[0].lastRunAt!)
        : undefined;

      // Mock package tier (would come from client data)
      const packageTier = completedProjects > 5 ? 'Premium' :
                         completedProjects > 2 ? 'Professional' :
                         'Starter';

      return {
        id: client.id,
        name: client.name,
        email: client.tags?.find(t => t.includes('@')) || undefined,
        status: client.status || 'active',
        tags: client.tags,
        totalProjects: clientProjects.length,
        activeProjects,
        completedProjects,
        totalRevenue,
        lastActivity,
        packageTier
      };
    });
  }, [clients, projects]);

  // Apply filters and search
  const filteredClients = useMemo(() => {
    let filtered = clientsWithMetrics;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(client =>
        client.name.toLowerCase().includes(query) ||
        client.email?.toLowerCase().includes(query)
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(client => client.status === statusFilter);
    }

    // Package tier filter
    if (packageFilter !== 'all') {
      filtered = filtered.filter(client => client.packageTier === packageFilter);
    }

    // Sort
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'projects':
          comparison = a.totalProjects - b.totalProjects;
          break;
        case 'revenue':
          comparison = a.totalRevenue - b.totalRevenue;
          break;
        case 'activity':
          comparison = (a.lastActivity?.getTime() || 0) - (b.lastActivity?.getTime() || 0);
          break;
      }

      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [clientsWithMetrics, searchQuery, statusFilter, packageFilter, sortBy, sortOrder]);

  const toggleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  // Calculate summary stats
  const totalClients = filteredClients.length;
  const activeClients = filteredClients.filter(c => c.activeProjects > 0).length;
  const totalRevenue = filteredClients.reduce((sum, c) => sum + c.totalRevenue, 0);
  const avgProjectsPerClient = totalClients > 0
    ? Math.round(filteredClients.reduce((sum, c) => sum + c.totalProjects, 0) / totalClients * 10) / 10
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Clients</h1>
          <p className="text-sm text-slate-600">
            Manage client relationships and project history
          </p>
        </div>
        <button
          onClick={() => {/* TODO: Open add client modal */}}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          Add Client
        </button>
      </header>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-100 p-2">
              <Users className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <div className="text-sm font-medium text-slate-600">Total Clients</div>
              <div className="text-2xl font-semibold text-slate-900">{totalClients}</div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-100 p-2">
              <TrendingUp className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <div className="text-sm font-medium text-slate-600">Active Clients</div>
              <div className="text-2xl font-semibold text-slate-900">{activeClients}</div>
              <div className="text-xs text-slate-500">with ongoing work</div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-purple-100 p-2">
              <DollarSign className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <div className="text-sm font-medium text-slate-600">Total Revenue</div>
              <div className="text-2xl font-semibold text-slate-900">
                ${totalRevenue.toLocaleString()}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-indigo-100 p-2">
              <Briefcase className="h-5 w-5 text-indigo-600" />
            </div>
            <div>
              <div className="text-sm font-medium text-slate-600">Avg Projects</div>
              <div className="text-2xl font-semibold text-slate-900">{avgProjectsPerClient}</div>
              <div className="text-xs text-slate-500">per client</div>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search clients by name or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-slate-300 pl-10 pr-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        >
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>

        <select
          value={packageFilter}
          onChange={(e) => setPackageFilter(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        >
          <option value="all">All Packages</option>
          <option value="Starter">Starter</option>
          <option value="Professional">Professional</option>
          <option value="Premium">Premium</option>
        </select>
      </div>

      {/* Clients Table */}
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th
                onClick={() => toggleSort('name')}
                className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-100"
              >
                <div className="flex items-center gap-2">
                  Client Name
                  <ArrowUpDown className="h-3 w-3" />
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                Contact
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                Package
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                Status
              </th>
              <th
                onClick={() => toggleSort('projects')}
                className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-100"
              >
                <div className="flex items-center gap-2">
                  Projects
                  <ArrowUpDown className="h-3 w-3" />
                </div>
              </th>
              <th
                onClick={() => toggleSort('revenue')}
                className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-100"
              >
                <div className="flex items-center gap-2">
                  Revenue
                  <ArrowUpDown className="h-3 w-3" />
                </div>
              </th>
              <th
                onClick={() => toggleSort('activity')}
                className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-100"
              >
                <div className="flex items-center gap-2">
                  Last Activity
                  <ArrowUpDown className="h-3 w-3" />
                </div>
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-700 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {filteredClients.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center">
                  <div className="flex flex-col items-center">
                    <Users className="h-12 w-12 text-slate-300 mb-2" />
                    <p className="text-sm font-medium text-slate-900">No clients found</p>
                    <p className="text-xs text-slate-500">
                      {searchQuery || statusFilter !== 'all' || packageFilter !== 'all'
                        ? 'Try adjusting your filters'
                        : 'Add your first client to get started'}
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredClients.map((client) => (
                <tr
                  key={client.id}
                  onClick={() => navigate(`/dashboard/clients/${client.id}`)}
                  className="hover:bg-slate-50 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                        <span className="text-sm font-semibold text-blue-600">
                          {client.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-slate-900 hover:text-blue-600">
                          {client.name}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {client.email ? (
                      <div className="flex items-center gap-2 text-sm text-slate-600">
                        <Mail className="h-4 w-4" />
                        {client.email}
                      </div>
                    ) : (
                      <span className="text-sm text-slate-400">No email</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                      ${client.packageTier === 'Premium' ? 'bg-purple-100 text-purple-800' : ''}
                      ${client.packageTier === 'Professional' ? 'bg-blue-100 text-blue-800' : ''}
                      ${client.packageTier === 'Starter' ? 'bg-slate-100 text-slate-800' : ''}
                    `}>
                      {client.packageTier}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center gap-1 text-xs font-semibold
                      ${client.status === 'active' ? 'text-emerald-700' : 'text-slate-500'}
                    `}>
                      {client.status === 'active' ? (
                        <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                      ) : (
                        <span className="h-2 w-2 rounded-full bg-slate-400"></span>
                      )}
                      {client.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-slate-900">
                      <span className="font-semibold">{client.totalProjects}</span> total
                    </div>
                    {client.activeProjects > 0 && (
                      <div className="text-xs text-amber-600">
                        {client.activeProjects} active
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-900">
                    ${client.totalRevenue.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                    {client.lastActivity ? (
                      formatDistanceToNow(client.lastActivity, { addSuffix: true })
                    ) : (
                      <span className="text-slate-400">No activity</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/dashboard/clients/${client.id}`);
                      }}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Results Count */}
      {filteredClients.length > 0 && (
        <div className="text-sm text-slate-600 text-center">
          Showing {filteredClients.length} of {clientsWithMetrics.length} client{clientsWithMetrics.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
