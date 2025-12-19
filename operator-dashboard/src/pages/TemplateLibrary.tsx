import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FileText,
  TrendingUp,
  Clock,
  Award,
  Search,
  Filter,
  BarChart3,
  Eye,
  Edit,
  Copy,
  Star,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';

// Mock template data structure
interface Template {
  id: string;
  name: string;
  type: 'Problem Recognition' | 'Statistic + Insight' | 'Contrarian Take' | 'What Changed' | 'Question Post' | 'Personal Story' | 'Myth Busting' | 'Things I Got Wrong' | 'How-To' | 'Comparison' | 'What I Learned From' | 'Inside Look' | 'Future Thinking' | 'Reader Q Response' | 'Milestone';
  description: string;
  difficulty: 'Fast' | 'Medium' | 'Slow';
  fillTime: number; // minutes
  usageCount: number;
  avgQualityScore: number;
  avgReadability: number;
  avgEngagement: number; // mock metric
  lastUsed: string;
  bestFor: string[];
  structure: string;
  requiresStory: boolean;
  requiresData: boolean;
}

// Mock template statistics
interface TemplateStats {
  totalTemplates: number;
  avgFillTime: number;
  avgQualityScore: number;
  mostUsed: string;
}

// Mock data
const mockTemplates: Template[] = [
  {
    id: '1',
    name: 'Problem Recognition',
    type: 'Problem Recognition',
    description: 'Opening with a problem statement that resonates with the audience',
    difficulty: 'Fast',
    fillTime: 5,
    usageCount: 142,
    avgQualityScore: 88,
    avgReadability: 72,
    avgEngagement: 4.2,
    lastUsed: '2025-12-15',
    bestFor: ['B2B SaaS', 'Consulting', 'Agencies'],
    structure: '[AUDIENCE] face [PROBLEM]...',
    requiresStory: false,
    requiresData: false,
  },
  {
    id: '2',
    name: 'Statistic + Insight',
    type: 'Statistic + Insight',
    description: 'Lead with compelling data, follow with interpretation',
    difficulty: 'Fast',
    fillTime: 5,
    usageCount: 128,
    avgQualityScore: 91,
    avgReadability: 68,
    avgEngagement: 5.1,
    lastUsed: '2025-12-14',
    bestFor: ['B2B SaaS', 'Consulting', 'Research'],
    structure: '[STAT]% of [AUDIENCE]...',
    requiresStory: false,
    requiresData: true,
  },
  {
    id: '3',
    name: 'Contrarian Take',
    type: 'Contrarian Take',
    description: 'Challenge conventional wisdom in the industry',
    difficulty: 'Medium',
    fillTime: 7,
    usageCount: 95,
    avgQualityScore: 85,
    avgReadability: 74,
    avgEngagement: 6.3,
    lastUsed: '2025-12-13',
    bestFor: ['Thought Leaders', 'Startups', 'Innovators'],
    structure: 'Everyone says [COMMON BELIEF]...',
    requiresStory: false,
    requiresData: false,
  },
  {
    id: '4',
    name: 'Personal Story',
    type: 'Personal Story',
    description: 'Share personal experiences to build connection',
    difficulty: 'Slow',
    fillTime: 10,
    usageCount: 67,
    avgQualityScore: 92,
    avgReadability: 78,
    avgEngagement: 7.8,
    lastUsed: '2025-12-12',
    bestFor: ['Coaches', 'Creators', 'Community Leaders'],
    structure: '[TIME PERIOD] ago, I [STORY]...',
    requiresStory: true,
    requiresData: false,
  },
  {
    id: '5',
    name: 'How-To',
    type: 'How-To',
    description: 'Step-by-step actionable guidance',
    difficulty: 'Fast',
    fillTime: 5,
    usageCount: 134,
    avgQualityScore: 87,
    avgReadability: 71,
    avgEngagement: 5.9,
    lastUsed: '2025-12-16',
    bestFor: ['Education', 'Consulting', 'SaaS'],
    structure: 'How to [ACHIEVE OUTCOME]...',
    requiresStory: false,
    requiresData: false,
  },
  {
    id: '6',
    name: 'Myth Busting',
    type: 'Myth Busting',
    description: 'Correct common misconceptions',
    difficulty: 'Medium',
    fillTime: 7,
    usageCount: 89,
    avgQualityScore: 86,
    avgReadability: 73,
    avgEngagement: 5.4,
    lastUsed: '2025-12-11',
    bestFor: ['Education', 'Experts', 'Consultants'],
    structure: 'Myth: [MISCONCEPTION]...',
    requiresStory: false,
    requiresData: false,
  },
  {
    id: '7',
    name: 'Comparison',
    type: 'Comparison',
    description: 'Compare two approaches or solutions',
    difficulty: 'Fast',
    fillTime: 5,
    usageCount: 112,
    avgQualityScore: 84,
    avgReadability: 70,
    avgEngagement: 4.7,
    lastUsed: '2025-12-10',
    bestFor: ['SaaS', 'Consulting', 'Reviews'],
    structure: '[OPTION A] vs [OPTION B]...',
    requiresStory: false,
    requiresData: false,
  },
  {
    id: '8',
    name: 'Future Thinking',
    type: 'Future Thinking',
    description: 'Predict trends and upcoming changes',
    difficulty: 'Medium',
    fillTime: 8,
    usageCount: 73,
    avgQualityScore: 83,
    avgReadability: 69,
    avgEngagement: 5.2,
    lastUsed: '2025-12-09',
    bestFor: ['Thought Leaders', 'Innovators', 'Startups'],
    structure: 'The future of [INDUSTRY]...',
    requiresStory: false,
    requiresData: false,
  },
];

const mockStats: TemplateStats = {
  totalTemplates: 15,
  avgFillTime: 6.8,
  avgQualityScore: 87,
  mostUsed: 'Problem Recognition',
};

export default function TemplateLibrary() {
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);

  // Mock query - replace with actual API call
  const { data: templates = mockTemplates } = useQuery({
    queryKey: ['templates'],
    queryFn: async () => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockTemplates;
    },
  });

  const { data: stats = mockStats } = useQuery({
    queryKey: ['template-stats'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockStats;
    },
  });

  // Filter templates
  const filteredTemplates = useMemo(() => {
    let filtered = templates;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        t =>
          t.name.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query) ||
          t.type.toLowerCase().includes(query)
      );
    }

    if (difficultyFilter) {
      filtered = filtered.filter(t => t.difficulty === difficultyFilter);
    }

    if (categoryFilter) {
      filtered = filtered.filter(t => t.bestFor.includes(categoryFilter));
    }

    return filtered;
  }, [templates, searchQuery, difficultyFilter, categoryFilter]);

  // Calculate aggregate metrics
  const aggregateMetrics = useMemo(() => {
    if (filteredTemplates.length === 0) return null;

    const totalUsage = filteredTemplates.reduce((sum, t) => sum + t.usageCount, 0);
    const avgQuality = Math.round(
      filteredTemplates.reduce((sum, t) => sum + t.avgQualityScore, 0) / filteredTemplates.length
    );
    const avgTime = Math.round(
      filteredTemplates.reduce((sum, t) => sum + t.fillTime, 0) / filteredTemplates.length
    );

    return { totalUsage, avgQuality, avgTime };
  }, [filteredTemplates]);

  // Get difficulty badge styling
  const getDifficultyBadge = (difficulty: string) => {
    switch (difficulty) {
      case 'Fast':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'Slow':
        return 'bg-orange-100 text-orange-700 border-orange-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  // Get quality score color
  const getQualityColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 80) return 'text-blue-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-orange-600';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Template Library</h1>
        <p className="text-sm text-slate-600 mt-1">
          Manage and analyze your content templates
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Total Templates</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{stats.totalTemplates}</p>
            </div>
            <div className="rounded-lg bg-blue-100 p-3">
              <FileText className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Avg Fill Time</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{stats.avgFillTime}m</p>
            </div>
            <div className="rounded-lg bg-purple-100 p-3">
              <Clock className="h-6 w-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Avg Quality</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{stats.avgQualityScore}%</p>
            </div>
            <div className="rounded-lg bg-green-100 p-3">
              <Award className="h-6 w-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Most Used</p>
              <p className="text-lg font-bold text-slate-900 mt-1">{stats.mostUsed}</p>
            </div>
            <div className="rounded-lg bg-orange-100 p-3">
              <TrendingUp className="h-6 w-6 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search templates..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-slate-300 pl-10 pr-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Difficulty Filter */}
          <div className="sm:w-48">
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <select
                value={difficultyFilter}
                onChange={e => setDifficultyFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 pl-10 pr-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none"
              >
                <option value="">All Difficulties</option>
                <option value="Fast">Fast (3-5 min)</option>
                <option value="Medium">Medium (7-8 min)</option>
                <option value="Slow">Slow (10+ min)</option>
              </select>
            </div>
          </div>

          {/* Category Filter */}
          <div className="sm:w-48">
            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none"
            >
              <option value="">All Categories</option>
              <option value="B2B SaaS">B2B SaaS</option>
              <option value="Consulting">Consulting</option>
              <option value="Agencies">Agencies</option>
              <option value="Coaches">Coaches</option>
              <option value="Creators">Creators</option>
              <option value="Education">Education</option>
            </select>
          </div>

          {/* Clear Filters */}
          {(searchQuery || difficultyFilter || categoryFilter) && (
            <button
              onClick={() => {
                setSearchQuery('');
                setDifficultyFilter('');
                setCategoryFilter('');
              }}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium whitespace-nowrap"
            >
              Clear Filters
            </button>
          )}
        </div>

        {/* Active Filters Summary */}
        {aggregateMetrics && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <div className="flex items-center gap-6 text-sm text-slate-600">
              <span>
                <strong className="text-slate-900">{filteredTemplates.length}</strong> templates
              </span>
              <span>
                <strong className="text-slate-900">{aggregateMetrics.totalUsage}</strong> total uses
              </span>
              <span>
                Avg quality: <strong className="text-slate-900">{aggregateMetrics.avgQuality}%</strong>
              </span>
              <span>
                Avg time: <strong className="text-slate-900">{aggregateMetrics.avgTime}m</strong>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredTemplates.map(template => (
          <div
            key={template.id}
            className="rounded-lg border border-slate-200 bg-white p-5 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
            onClick={() => setSelectedTemplate(template)}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-slate-900">{template.name}</h3>
                <p className="text-sm text-slate-600 mt-1">{template.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                  <Eye className="h-4 w-4" />
                </button>
                <button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                  <Copy className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Tags */}
            <div className="flex flex-wrap gap-2 mb-4">
              <span
                className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium ${getDifficultyBadge(
                  template.difficulty
                )}`}
              >
                <Clock className="h-3 w-3" />
                {template.difficulty} ({template.fillTime}m)
              </span>
              {template.requiresStory && (
                <span className="inline-flex items-center gap-1 rounded-md border border-purple-200 bg-purple-100 px-2 py-1 text-xs font-medium text-purple-700">
                  <FileText className="h-3 w-3" />
                  Needs Story
                </span>
              )}
              {template.requiresData && (
                <span className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                  <BarChart3 className="h-3 w-3" />
                  Needs Data
                </span>
              )}
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-4 gap-4 pt-4 border-t border-slate-200">
              <div>
                <p className="text-xs text-slate-600">Usage</p>
                <p className="text-lg font-semibold text-slate-900 mt-0.5">{template.usageCount}</p>
              </div>
              <div>
                <p className="text-xs text-slate-600">Quality</p>
                <p className={`text-lg font-semibold mt-0.5 ${getQualityColor(template.avgQualityScore)}`}>
                  {template.avgQualityScore}%
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-600">Readability</p>
                <p className="text-lg font-semibold text-slate-900 mt-0.5">{template.avgReadability}</p>
              </div>
              <div>
                <p className="text-xs text-slate-600">Engagement</p>
                <p className="text-lg font-semibold text-slate-900 mt-0.5 flex items-center gap-0.5">
                  <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                  {template.avgEngagement.toFixed(1)}
                </p>
              </div>
            </div>

            {/* Best For */}
            <div className="mt-4 pt-4 border-t border-slate-200">
              <p className="text-xs font-medium text-slate-600 mb-2">Best for:</p>
              <div className="flex flex-wrap gap-1">
                {template.bestFor.map(category => (
                  <span
                    key={category}
                    className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
                  >
                    {category}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {filteredTemplates.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-12 text-center">
          <FileText className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No templates found</h3>
          <p className="text-sm text-slate-600 mb-6">
            Try adjusting your filters or search query
          </p>
          <button
            onClick={() => {
              setSearchQuery('');
              setDifficultyFilter('');
              setCategoryFilter('');
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
          >
            Clear All Filters
          </button>
        </div>
      )}

      {/* Template Detail Modal */}
      {selectedTemplate && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4"
          onClick={() => setSelectedTemplate(null)}
        >
          <div
            className="w-full max-w-3xl rounded-lg border border-slate-200 bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between mb-6">
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-slate-900">{selectedTemplate.name}</h2>
                <p className="text-sm text-slate-600 mt-2">{selectedTemplate.description}</p>
              </div>
              <button
                onClick={() => setSelectedTemplate(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Template Details */}
            <div className="space-y-6">
              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm text-slate-600">Usage Count</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{selectedTemplate.usageCount}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm text-slate-600">Quality Score</p>
                  <p className={`text-2xl font-bold mt-1 ${getQualityColor(selectedTemplate.avgQualityScore)}`}>
                    {selectedTemplate.avgQualityScore}%
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm text-slate-600">Fill Time</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{selectedTemplate.fillTime}m</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm text-slate-600">Engagement</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-1">
                    <Star className="h-5 w-5 text-yellow-500 fill-yellow-500" />
                    {selectedTemplate.avgEngagement.toFixed(1)}
                  </p>
                </div>
              </div>

              {/* Structure */}
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-2">Template Structure</h3>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <code className="text-sm text-slate-700 font-mono">{selectedTemplate.structure}</code>
                </div>
              </div>

              {/* Requirements */}
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-2">Requirements</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    {selectedTemplate.requiresStory ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-slate-400" />
                    )}
                    <span className="text-sm text-slate-700">
                      {selectedTemplate.requiresStory ? 'Requires' : 'Does not require'} personal story
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {selectedTemplate.requiresData ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-slate-400" />
                    )}
                    <span className="text-sm text-slate-700">
                      {selectedTemplate.requiresData ? 'Requires' : 'Does not require'} data/statistics
                    </span>
                  </div>
                </div>
              </div>

              {/* Best For */}
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-2">Best For</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedTemplate.bestFor.map(category => (
                    <span
                      key={category}
                      className="rounded-md bg-blue-100 border border-blue-200 px-3 py-1 text-sm font-medium text-blue-700"
                    >
                      {category}
                    </span>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button
                  onClick={() => setSelectedTemplate(null)}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Close
                </button>
                <button className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800">
                  <Edit className="h-4 w-4" />
                  Edit Template
                </button>
                <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700">
                  <Copy className="h-4 w-4" />
                  Use Template
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
