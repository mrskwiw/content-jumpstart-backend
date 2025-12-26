import { useQuery } from '@tanstack/react-query';
import { X, Loader2 } from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';
import { deliverablesApi } from '@/api/deliverables';
import type { Deliverable } from '@/types/domain';
import { OverviewTab } from './tabs/OverviewTab';
import { PreviewTab } from './tabs/PreviewTab';
import { PostsTab } from './tabs/PostsTab';
import { QATab } from './tabs/QATab';
import { HistoryTab } from './tabs/HistoryTab';

interface Props {
  deliverable: Deliverable | null;
  onClose: () => void;
}

// Extract readable name from deliverable path
function getDeliverableName(path: string): string {
  // Get filename from path (handles both / and \ separators)
  const filename = path.split(/[/\\]/).pop() || path;

  // Remove file extension
  const nameWithoutExt = filename.replace(/\.(txt|docx|pdf|md)$/i, '');

  // Remove timestamp pattern (e.g., _20231224_143022)
  const nameWithoutTimestamp = nameWithoutExt.replace(/_\d{8}_\d{6}/, '');

  // Replace underscores with spaces and capitalize words
  return nameWithoutTimestamp
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function DeliverableDrawer({ deliverable, onClose }: Props) {
  const { data: details, isLoading, error } = useQuery({
    queryKey: ['deliverable-details', deliverable?.id],
    queryFn: () => deliverable ? deliverablesApi.getDetails(deliverable.id) : null,
    enabled: !!deliverable,
    staleTime: 30000, // Cache for 30 seconds
  });

  if (!deliverable) return null;

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/30">
      <div className="h-full w-full max-w-2xl bg-white shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <p className="text-lg font-semibold text-slate-900">
              {getDeliverableName(deliverable.path)}
            </p>
            <p className="text-xs text-slate-500 font-mono mt-0.5">{deliverable.id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-800 transition-colors p-1 rounded hover:bg-slate-100"
            aria-label="Close drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {isLoading && (
            <div className="flex flex-col items-center justify-center h-full">
              <Loader2 className="h-8 w-8 text-blue-600 animate-spin mb-3" />
              <div className="text-sm text-slate-500">Loading details...</div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-800 font-medium mb-1">
                  Error loading deliverable details
                </p>
                <p className="text-xs text-red-600">
                  {error instanceof Error ? error.message : 'Unknown error occurred'}
                </p>
              </div>
            </div>
          )}

          {details && (
            <Tabs.Root defaultValue="overview" className="flex flex-col h-full">
              <Tabs.List className="flex border-b border-slate-200 px-4 bg-slate-50">
                <Tabs.Trigger
                  value="overview"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  Overview
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="preview"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  Preview
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="posts"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  Posts ({details.posts.length})
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="qa"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  Quality
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="history"
                  className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 transition-colors"
                >
                  History
                </Tabs.Trigger>
              </Tabs.List>

              <div className="flex-1 overflow-hidden">
                <Tabs.Content value="overview" className="h-full overflow-y-auto">
                  <OverviewTab deliverable={details} />
                </Tabs.Content>

                <Tabs.Content value="preview" className="h-full overflow-y-auto">
                  <PreviewTab deliverable={details} />
                </Tabs.Content>

                <Tabs.Content value="posts" className="h-full overflow-y-auto">
                  <PostsTab deliverable={details} />
                </Tabs.Content>

                <Tabs.Content value="qa" className="h-full overflow-y-auto">
                  <QATab deliverable={details} />
                </Tabs.Content>

                <Tabs.Content value="history" className="h-full overflow-y-auto">
                  <HistoryTab deliverable={details} />
                </Tabs.Content>
              </div>
            </Tabs.Root>
          )}
        </div>
      </div>
    </div>
  );
}
