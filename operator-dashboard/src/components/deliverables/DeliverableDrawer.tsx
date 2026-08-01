import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Loader2, Download, FileText, CheckCircle } from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';
import { format } from 'date-fns';
import { deliverablesApi } from '@/api/deliverables';
import { downloadHint, isMediaDeliverable } from '@/utils/deliverableDownload';
import { formatFileSize } from '@/utils/formatters';
import type { Deliverable } from '@/types/domain';
import { OverviewTab } from './tabs/OverviewTab';
import { PreviewTab } from './tabs/PreviewTab';
import { PostsTab } from './tabs/PostsTab';
import { QATab } from './tabs/QATab';
import { HistoryTab } from './tabs/HistoryTab';
import { ResearchTab } from './tabs/ResearchTab';

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
  // Media deliverables (image/audio/video) are stored as asset keys, not export files —
  // getDetails() (file preview / posts / QA) is export-oriented and would show binary
  // garbage / empty tabs for them, so skip it and render a media panel instead.
  const isMedia = !!deliverable && isMediaDeliverable(deliverable.format);
  const { data: details, isLoading, error } = useQuery({
    queryKey: ['deliverable-details', deliverable?.id],
    queryFn: () => deliverable ? deliverablesApi.getDetails(deliverable.id) : null,
    enabled: !!deliverable && !isMedia,
    staleTime: 30000, // Cache for 30 seconds
  });

  if (!deliverable) return null;

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50 dark:bg-black/60">
      <div className="h-full w-full max-w-2xl bg-white dark:bg-neutral-900 shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 dark:border-neutral-700 px-6 py-4">
          <div>
            <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              {getDeliverableName(deliverable.path)}
            </p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 font-mono mt-0.5">{deliverable.id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200 transition-colors p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800"
            aria-label="Close drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {isMedia && <MediaDeliverablePanel deliverable={deliverable} />}

          {!isMedia && isLoading && (
            <div className="flex flex-col items-center justify-center h-full">
              <Loader2 className="h-8 w-8 text-blue-600 dark:text-blue-400 animate-spin mb-3" />
              <div className="text-sm text-neutral-500 dark:text-neutral-400">Loading details...</div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <p className="text-sm text-red-800 dark:text-red-300 font-medium mb-1">
                  Error loading deliverable details
                </p>
                <p className="text-xs text-red-600 dark:text-red-400">
                  {error instanceof Error ? error.message : 'Unknown error occurred'}
                </p>
              </div>
            </div>
          )}

          {details && (
            <Tabs.Root defaultValue="overview" className="flex flex-col h-full">
              <Tabs.List className="flex border-b border-neutral-200 dark:border-neutral-700 px-4 bg-neutral-50 dark:bg-neutral-800/50">
                <Tabs.Trigger
                  value="overview"
                  className="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 transition-colors"
                >
                  Overview
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="preview"
                  className="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 transition-colors"
                >
                  Preview
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="posts"
                  className="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 transition-colors"
                >
                  Posts ({details.posts.length})
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="qa"
                  className="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 transition-colors"
                >
                  Quality
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="history"
                  className="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 transition-colors"
                >
                  History
                </Tabs.Trigger>
                <Tabs.Trigger
                  value="research"
                  className="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 transition-colors"
                >
                  Research {details.researchResults && details.researchResults.length > 0 && `(${details.researchResults.length})`}
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

                <Tabs.Content value="research" className="h-full overflow-y-auto">
                  <ResearchTab deliverable={details} />
                </Tabs.Content>
              </div>
            </Tabs.Root>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Detail panel for a media-generation deliverable (image/audio/video). Media assets
 * aren't text/export files, so instead of the preview/posts/QA tabs this offers the
 * essentials: what it is and a download.
 */
function MediaDeliverablePanel({ deliverable }: { deliverable: Deliverable }) {
  const [downloading, setDownloading] = useState(false);
  const [failed, setFailed] = useState(false);
  const queryClient = useQueryClient();

  // Media deliverables are still deliverables — keep the metadata + delivery workflow.
  const markDelivered = useMutation({
    mutationFn: () =>
      deliverablesApi.markDelivered(deliverable.id, { deliveredAt: new Date().toISOString() }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deliverables'] }),
  });

  const handleDownload = async () => {
    setFailed(false);
    setDownloading(true);
    try {
      const { blob, filename } = await deliverablesApi.download(
        deliverable.id,
        downloadHint(deliverable.format, deliverable.path)
      );
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      setFailed(true);
    } finally {
      setDownloading(false);
    }
  };

  const meta: Array<[string, string]> = [
    ['Format', deliverable.format.toUpperCase()],
    ['Status', deliverable.status],
    ['Size', formatFileSize(deliverable.fileSizeBytes)],
    ['Created', format(new Date(deliverable.createdAt), 'PPp')],
    [
      'Delivered',
      deliverable.deliveredAt ? format(new Date(deliverable.deliveredAt), 'PPp') : 'Not yet',
    ],
  ];

  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <FileText className="h-12 w-12 text-neutral-400 dark:text-neutral-500" />
        <div>
          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            {deliverable.format.toUpperCase()} media deliverable
          </p>
          <p className="mt-1 max-w-sm text-xs text-neutral-500 dark:text-neutral-400">
            A generated media asset, not a text export — download it to view or play.
          </p>
        </div>
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          <Download className={`h-4 w-4 ${downloading ? 'animate-bounce' : ''}`} />
          {downloading ? 'Downloading…' : 'Download'}
        </button>
        {failed && (
          <p className="text-xs text-red-600 dark:text-red-400">Download failed. Please try again.</p>
        )}
      </div>

      {/* Metadata — media deliverables keep the same at-a-glance info as export ones. */}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 rounded-lg border border-neutral-200 p-4 dark:border-neutral-700">
        {meta.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-neutral-500 dark:text-neutral-400">{label}</dt>
            <dd className="mt-0.5 text-sm text-neutral-900 dark:text-neutral-100">{value}</dd>
          </div>
        ))}
        <div className="col-span-2">
          <dt className="text-xs text-neutral-500 dark:text-neutral-400">Path</dt>
          <dd className="mt-0.5 break-all font-mono text-xs text-neutral-400 dark:text-neutral-500">
            {deliverable.path}
          </dd>
        </div>
      </dl>

      {/* Delivery workflow — retained for media deliverables. Once the mutation
          succeeds the control is replaced by a confirmation (not just disabled), so it
          can't be re-fired in the window before the parent list refetch lands and passes
          a fresh `delivered` status prop — avoiding a duplicate mark-delivered PATCH. */}
      {markDelivered.isSuccess || deliverable.status === 'delivered' ? (
        <p className="inline-flex items-center justify-center gap-2 text-sm font-medium text-green-700 dark:text-green-400">
          <CheckCircle className="h-4 w-4" /> Delivered
        </p>
      ) : (
        <button
          type="button"
          onClick={() => markDelivered.mutate()}
          disabled={markDelivered.isPending}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-green-300 bg-green-50 px-4 py-2 text-sm font-medium text-green-800 hover:bg-green-100 disabled:opacity-50 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300 dark:hover:bg-green-900/30"
        >
          <CheckCircle className="h-4 w-4" />
          {markDelivered.isPending ? 'Marking Delivered…' : 'Mark Delivered'}
        </button>
      )}
      {markDelivered.isError && (
        <p className="text-center text-xs text-red-600 dark:text-red-400">
          Couldn't mark delivered. Please try again.
        </p>
      )}
    </div>
  );
}
