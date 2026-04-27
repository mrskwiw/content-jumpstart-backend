import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { researchApi } from '@/api';
import { ResultCard } from '../../components/research/ResultCard';
import { ResultDetailModal } from '../../components/research/ResultDetailModal';
import { Filter, FileSearch } from 'lucide-react';
import { ResearchResult } from '../../types/domain';

export default function ResearchResults() {
  const [filters, setFilters] = useState({
    toolType: 'all',
    clientId: 'all',
    dateRange: '30'
  });
  const [selectedResult, setSelectedResult] = useState<ResearchResult | null>(null);

  const { data: results, isLoading } = useQuery({
    queryKey: ['research-results', filters],
    queryFn: () =>
      researchApi.getAllResults({
        toolName: filters.toolType,
        clientId: filters.clientId,
        days: parseInt(filters.dateRange, 10),
      }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Research Results
        </h1>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Browse and manage past research outputs
        </p>
      </div>

      {/* Filter Bar */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700 p-4">
        <div className="flex items-center gap-4">
          <Filter className="h-4 w-4 text-gray-400" />

          <select
            value={filters.toolType}
            onChange={(e) => setFilters({ ...filters, toolType: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Tools</option>
            <option value="voice_analysis">Voice Analysis</option>
            <option value="brand_archetype">Brand Archetype</option>
            <option value="seo_keyword_research">SEO Keywords</option>
            <option value="competitive_analysis">Competitive Analysis</option>
          </select>

          <select
            value={filters.dateRange}
            onChange={(e) => setFilters({ ...filters, dateRange: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="365">Last year</option>
          </select>
        </div>
      </div>

      {/* Results Stats */}
      {results && results.results.length > 0 && (
        <div className="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700 p-4">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {results.total} result{results.total !== 1 ? 's' : ''} found
          </div>
        </div>
      )}

      {/* Results List */}
      <div className="space-y-3">
        {results && results.results.length > 0 ? (
          results.results.map((result: ResearchResult) => (
            <ResultCard
              key={result.id}
              result={result}
              onView={() => setSelectedResult(result)}
            />
          ))
        ) : (
          <div className="text-center py-16 bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700">
            <FileSearch className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400 mb-1">
              No research results found
            </p>
            <p className="text-sm text-gray-400 dark:text-gray-500">
              Run research tools from the Library to see results here
            </p>
          </div>
        )}
      </div>

      {/* Result Detail Modal */}
      {selectedResult && (
        <ResultDetailModal
          result={selectedResult}
          onClose={() => setSelectedResult(null)}
        />
      )}
    </div>
  );
}
