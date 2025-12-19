import { useState, useMemo } from 'react';
import {
  BarChart3,
  TrendingUp,
  Clock,
  DollarSign,
  FileText,
  CheckCircle,
  AlertTriangle,
  Calendar,
  Users,
  Target,
  Award,
  Activity,
} from 'lucide-react';
import { format, subMonths, startOfMonth, endOfMonth, eachMonthOfInterval, isWithinInterval } from 'date-fns';

type TimeRange = 'month' | 'quarter' | 'year' | 'all';

interface MetricCard {
  label: string;
  value: string | number;
  change: number;
  trend: 'up' | 'down' | 'neutral';
  icon: React.ElementType;
  color: string;
}

interface MonthlyData {
  month: string;
  projects: number;
  posts: number;
  revenue: number;
  qualityScore: number;
}

interface TemplatePerformance {
  templateName: string;
  usageCount: number;
  avgQualityScore: number;
  avgTimeMinutes: number;
}

interface ClientPerformance {
  clientName: string;
  projectsCount: number;
  totalPosts: number;
  avgQualityScore: number;
  totalRevenue: number;
}

export default function Analytics() {
  const [timeRange, setTimeRange] = useState<TimeRange>('month');

  // Mock data - would come from API
  const mockMonthlyData: MonthlyData[] = [
    { month: '2024-07', projects: 8, posts: 240, revenue: 14400, qualityScore: 87 },
    { month: '2024-08', projects: 12, posts: 360, revenue: 21600, qualityScore: 89 },
    { month: '2024-09', projects: 10, posts: 300, revenue: 18000, qualityScore: 91 },
    { month: '2024-10', projects: 15, posts: 450, revenue: 27000, qualityScore: 88 },
    { month: '2024-11', projects: 14, posts: 420, revenue: 25200, qualityScore: 92 },
    { month: '2024-12', projects: 18, posts: 540, revenue: 32400, qualityScore: 90 },
  ];

  const mockTemplatePerformance: TemplatePerformance[] = [
    { templateName: 'Problem Recognition', usageCount: 124, avgQualityScore: 92, avgTimeMinutes: 5 },
    { templateName: 'Statistic + Insight', usageCount: 118, avgQualityScore: 90, avgTimeMinutes: 5 },
    { templateName: 'How-To', usageCount: 112, avgQualityScore: 88, avgTimeMinutes: 5 },
    { templateName: 'Question Post', usageCount: 98, avgQualityScore: 85, avgTimeMinutes: 3 },
    { templateName: 'Comparison', usageCount: 86, avgQualityScore: 87, avgTimeMinutes: 5 },
    { templateName: 'Personal Story', usageCount: 72, avgQualityScore: 94, avgTimeMinutes: 10 },
    { templateName: 'Myth Busting', usageCount: 68, avgQualityScore: 89, avgTimeMinutes: 7 },
    { templateName: 'Contrarian Take', usageCount: 64, avgQualityScore: 91, avgTimeMinutes: 7 },
  ];

  const mockClientPerformance: ClientPerformance[] = [
    { clientName: 'TechFlow Solutions', projectsCount: 8, totalPosts: 240, avgQualityScore: 92, totalRevenue: 14400 },
    { clientName: 'Creative Agency Pro', projectsCount: 6, totalPosts: 180, avgQualityScore: 88, totalRevenue: 10800 },
    { clientName: 'Marketing Masters', projectsCount: 5, totalPosts: 150, avgQualityScore: 90, totalRevenue: 9000 },
    { clientName: 'Content Kings', projectsCount: 4, totalPosts: 120, avgQualityScore: 87, totalRevenue: 7200 },
    { clientName: 'Digital Dynamics', projectsCount: 4, totalPosts: 120, avgQualityScore: 91, totalRevenue: 7200 },
  ];

  // Calculate filtered data based on time range
  const filteredData = useMemo(() => {
    const now = new Date();
    let startDate: Date;

    switch (timeRange) {
      case 'month':
        startDate = startOfMonth(now);
        break;
      case 'quarter':
        startDate = subMonths(now, 3);
        break;
      case 'year':
        startDate = subMonths(now, 12);
        break;
      case 'all':
        return mockMonthlyData;
    }

    return mockMonthlyData.filter((data) => {
      const dataDate = new Date(data.month);
      return isWithinInterval(dataDate, { start: startDate, end: now });
    });
  }, [timeRange, mockMonthlyData]);

  // Calculate aggregate metrics
  const metrics = useMemo(() => {
    const totalProjects = filteredData.reduce((sum, d) => sum + d.projects, 0);
    const totalPosts = filteredData.reduce((sum, d) => sum + d.posts, 0);
    const totalRevenue = filteredData.reduce((sum, d) => sum + d.revenue, 0);
    const avgQualityScore = filteredData.length > 0
      ? Math.round(filteredData.reduce((sum, d) => sum + d.qualityScore, 0) / filteredData.length)
      : 0;

    // Calculate previous period for comparison
    const currentPeriodMonths = filteredData.length;
    const previousPeriodData = mockMonthlyData.slice(
      Math.max(0, mockMonthlyData.length - currentPeriodMonths * 2),
      mockMonthlyData.length - currentPeriodMonths
    );

    const prevProjects = previousPeriodData.reduce((sum, d) => sum + d.projects, 0);
    const prevPosts = previousPeriodData.reduce((sum, d) => sum + d.posts, 0);
    const prevRevenue = previousPeriodData.reduce((sum, d) => sum + d.revenue, 0);
    const prevQuality = previousPeriodData.length > 0
      ? previousPeriodData.reduce((sum, d) => sum + d.qualityScore, 0) / previousPeriodData.length
      : 0;

    const projectsChange = prevProjects > 0 ? ((totalProjects - prevProjects) / prevProjects) * 100 : 0;
    const postsChange = prevPosts > 0 ? ((totalPosts - prevPosts) / prevPosts) * 100 : 0;
    const revenueChange = prevRevenue > 0 ? ((totalRevenue - prevRevenue) / prevRevenue) * 100 : 0;
    const qualityChange = prevQuality > 0 ? ((avgQualityScore - prevQuality) / prevQuality) * 100 : 0;

    return {
      projects: { value: totalProjects, change: projectsChange },
      posts: { value: totalPosts, change: postsChange },
      revenue: { value: totalRevenue, change: revenueChange },
      quality: { value: avgQualityScore, change: qualityChange },
    };
  }, [filteredData, mockMonthlyData]);

  // Calculate time efficiency metrics
  const timeMetrics = useMemo(() => {
    const totalPosts = filteredData.reduce((sum, d) => sum + d.posts, 0);
    const totalProjects = filteredData.reduce((sum, d) => sum + d.projects, 0);

    // Assuming average of 5-6 hours per 30-post project
    const avgHoursPerProject = 5.5;
    const totalHours = totalProjects * avgHoursPerProject;
    const avgMinutesPerPost = (totalHours * 60) / totalPosts;
    const revenuePerHour = totalProjects > 0 ? metrics.revenue.value / totalHours : 0;

    return {
      totalHours: Math.round(totalHours),
      avgMinutesPerPost: Math.round(avgMinutesPerPost),
      revenuePerHour: Math.round(revenuePerHour),
    };
  }, [filteredData, metrics.revenue.value]);

  const metricCards: MetricCard[] = [
    {
      label: 'Projects Completed',
      value: metrics.projects.value,
      change: metrics.projects.change,
      trend: metrics.projects.change > 0 ? 'up' : metrics.projects.change < 0 ? 'down' : 'neutral',
      icon: CheckCircle,
      color: 'emerald',
    },
    {
      label: 'Posts Generated',
      value: metrics.posts.value,
      change: metrics.posts.change,
      trend: metrics.posts.change > 0 ? 'up' : metrics.posts.change < 0 ? 'down' : 'neutral',
      icon: FileText,
      color: 'blue',
    },
    {
      label: 'Avg Quality Score',
      value: `${metrics.quality.value}%`,
      change: metrics.quality.change,
      trend: metrics.quality.change > 0 ? 'up' : metrics.quality.change < 0 ? 'down' : 'neutral',
      icon: Award,
      color: 'purple',
    },
    {
      label: 'Total Revenue',
      value: `$${metrics.revenue.value.toLocaleString()}`,
      change: metrics.revenue.change,
      trend: metrics.revenue.change > 0 ? 'up' : metrics.revenue.change < 0 ? 'down' : 'neutral',
      icon: DollarSign,
      color: 'amber',
    },
  ];

  // Quality breakdown
  const qualityBreakdown = useMemo(() => {
    // Mock quality validation scores
    return {
      hookUniqueness: 92,
      ctaVariety: 88,
      lengthOptimal: 85,
      headlineStrength: 90,
      keywordUsage: 87,
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Analytics</h1>
          <p className="text-sm text-slate-600">
            Performance metrics, quality trends, and revenue reporting
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Time Range Selector */}
          <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1">
            <button
              onClick={() => setTimeRange('month')}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                timeRange === 'month'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              This Month
            </button>
            <button
              onClick={() => setTimeRange('quarter')}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                timeRange === 'quarter'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              Last 3 Months
            </button>
            <button
              onClick={() => setTimeRange('year')}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                timeRange === 'year'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              This Year
            </button>
            <button
              onClick={() => setTimeRange('all')}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                timeRange === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              All Time
            </button>
          </div>
          <button className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <Calendar className="h-4 w-4" />
            Export Report
          </button>
        </div>
      </header>

      {/* Key Metrics Cards */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {metricCards.map((metric) => (
          <div key={metric.label} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div className={`rounded-lg bg-${metric.color}-100 p-3`}>
                <metric.icon className={`h-6 w-6 text-${metric.color}-600`} />
              </div>
              <div className={`flex items-center gap-1 text-sm font-medium ${
                metric.trend === 'up' ? 'text-emerald-600' :
                metric.trend === 'down' ? 'text-red-600' :
                'text-slate-500'
              }`}>
                {metric.trend === 'up' && <TrendingUp className="h-4 w-4" />}
                {metric.trend === 'down' && <TrendingUp className="h-4 w-4 rotate-180" />}
                <span>{metric.change > 0 ? '+' : ''}{metric.change.toFixed(1)}%</span>
              </div>
            </div>
            <div className="mt-4">
              <p className="text-sm text-slate-600">{metric.label}</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{metric.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row 1: Performance Trends */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Projects Over Time */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Projects Over Time</h3>
              <p className="text-sm text-slate-600">Monthly project completion trend</p>
            </div>
            <BarChart3 className="h-5 w-5 text-slate-400" />
          </div>
          <div className="space-y-3">
            {filteredData.map((data, index) => {
              const maxProjects = Math.max(...filteredData.map(d => d.projects));
              const percentage = (data.projects / maxProjects) * 100;
              return (
                <div key={data.month}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">
                      {format(new Date(data.month), 'MMM yyyy')}
                    </span>
                    <span className="text-slate-900">{data.projects} projects</span>
                  </div>
                  <div className="mt-1 h-2 w-full rounded-full bg-slate-200">
                    <div
                      className="h-2 rounded-full bg-blue-600 transition-all"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Revenue Over Time */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Revenue Trends</h3>
              <p className="text-sm text-slate-600">Monthly revenue breakdown</p>
            </div>
            <DollarSign className="h-5 w-5 text-slate-400" />
          </div>
          <div className="space-y-3">
            {filteredData.map((data) => {
              const maxRevenue = Math.max(...filteredData.map(d => d.revenue));
              const percentage = (data.revenue / maxRevenue) * 100;
              return (
                <div key={data.month}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">
                      {format(new Date(data.month), 'MMM yyyy')}
                    </span>
                    <span className="text-slate-900">${data.revenue.toLocaleString()}</span>
                  </div>
                  <div className="mt-1 h-2 w-full rounded-full bg-slate-200">
                    <div
                      className="h-2 rounded-full bg-emerald-600 transition-all"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Charts Row 2: Quality & Time */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Quality Metrics Breakdown */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Quality Metrics</h3>
              <p className="text-sm text-slate-600">Average validation scores</p>
            </div>
            <Award className="h-5 w-5 text-slate-400" />
          </div>
          <div className="space-y-4">
            {Object.entries(qualityBreakdown).map(([key, value]) => {
              const label = key
                .replace(/([A-Z])/g, ' $1')
                .replace(/^./, str => str.toUpperCase());
              const colorClass = value >= 90 ? 'bg-emerald-600' :
                               value >= 80 ? 'bg-blue-600' :
                               value >= 70 ? 'bg-amber-600' :
                               'bg-red-600';
              return (
                <div key={key}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">{label}</span>
                    <span className="text-slate-900">{value}%</span>
                  </div>
                  <div className="mt-1 h-2 w-full rounded-full bg-slate-200">
                    <div
                      className={`h-2 rounded-full transition-all ${colorClass}`}
                      style={{ width: `${value}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Time Efficiency Metrics */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Time Efficiency</h3>
              <p className="text-sm text-slate-600">Productivity and speed metrics</p>
            </div>
            <Clock className="h-5 w-5 text-slate-400" />
          </div>
          <div className="space-y-6">
            <div className="rounded-lg bg-blue-50 p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-blue-600 p-2">
                  <Clock className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="text-sm text-blue-600">Total Hours</p>
                  <p className="text-2xl font-semibold text-blue-900">{timeMetrics.totalHours}h</p>
                </div>
              </div>
            </div>
            <div className="rounded-lg bg-purple-50 p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-purple-600 p-2">
                  <Activity className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="text-sm text-purple-600">Avg Time Per Post</p>
                  <p className="text-2xl font-semibold text-purple-900">{timeMetrics.avgMinutesPerPost} min</p>
                </div>
              </div>
            </div>
            <div className="rounded-lg bg-emerald-50 p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-emerald-600 p-2">
                  <DollarSign className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="text-sm text-emerald-600">Revenue Per Hour</p>
                  <p className="text-2xl font-semibold text-emerald-900">${timeMetrics.revenuePerHour}/h</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Template Performance */}
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Template Performance</h3>
            <p className="text-sm text-slate-600">Most used templates with quality and time metrics</p>
          </div>
          <Target className="h-5 w-5 text-slate-400" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="pb-3 text-left text-sm font-medium text-slate-600">Template</th>
                <th className="pb-3 text-right text-sm font-medium text-slate-600">Usage Count</th>
                <th className="pb-3 text-right text-sm font-medium text-slate-600">Avg Quality</th>
                <th className="pb-3 text-right text-sm font-medium text-slate-600">Avg Time</th>
                <th className="pb-3 text-right text-sm font-medium text-slate-600">Performance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {mockTemplatePerformance.map((template) => (
                <tr key={template.templateName} className="hover:bg-slate-50">
                  <td className="py-3 text-sm font-medium text-slate-900">{template.templateName}</td>
                  <td className="py-3 text-right text-sm text-slate-700">{template.usageCount}</td>
                  <td className="py-3 text-right">
                    <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                      template.avgQualityScore >= 90 ? 'bg-emerald-100 text-emerald-700' :
                      template.avgQualityScore >= 85 ? 'bg-blue-100 text-blue-700' :
                      'bg-amber-100 text-amber-700'
                    }`}>
                      {template.avgQualityScore}%
                    </span>
                  </td>
                  <td className="py-3 text-right text-sm text-slate-700">{template.avgTimeMinutes} min</td>
                  <td className="py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="h-2 w-24 rounded-full bg-slate-200">
                        <div
                          className="h-2 rounded-full bg-blue-600"
                          style={{ width: `${(template.avgQualityScore / 100) * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Client Performance Comparison */}
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Top Clients</h3>
            <p className="text-sm text-slate-600">Client performance ranked by projects and revenue</p>
          </div>
          <Users className="h-5 w-5 text-slate-400" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="pb-3 text-left text-sm font-medium text-slate-600">Client</th>
                <th className="pb-3 text-right text-sm font-medium text-slate-600">Projects</th>
                <th className="pb-3 text-right text-sm font-medium text-slate-600">Total Posts</th>
                <th className="pb-3 text-right text-sm font-medium text-slate-600">Avg Quality</th>
                <th className="pb-3 text-right text-sm font-medium text-slate-600">Total Revenue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {mockClientPerformance.map((client, index) => (
                <tr key={client.clientName} className="hover:bg-slate-50">
                  <td className="py-3">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-8 w-8 items-center justify-center rounded-full ${
                        index === 0 ? 'bg-amber-100 text-amber-700' :
                        index === 1 ? 'bg-slate-100 text-slate-700' :
                        index === 2 ? 'bg-orange-100 text-orange-700' :
                        'bg-blue-100 text-blue-700'
                      } text-sm font-semibold`}>
                        {index + 1}
                      </div>
                      <span className="text-sm font-medium text-slate-900">{client.clientName}</span>
                    </div>
                  </td>
                  <td className="py-3 text-right text-sm text-slate-700">{client.projectsCount}</td>
                  <td className="py-3 text-right text-sm text-slate-700">{client.totalPosts}</td>
                  <td className="py-3 text-right">
                    <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                      client.avgQualityScore >= 90 ? 'bg-emerald-100 text-emerald-700' :
                      client.avgQualityScore >= 85 ? 'bg-blue-100 text-blue-700' :
                      'bg-amber-100 text-amber-700'
                    }`}>
                      {client.avgQualityScore}%
                    </span>
                  </td>
                  <td className="py-3 text-right text-sm font-semibold text-slate-900">
                    ${client.totalRevenue.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
