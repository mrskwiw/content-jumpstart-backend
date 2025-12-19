import type { DeliverableDetails } from '@/types/domain';
import { FileText, AlertCircle } from 'lucide-react';

interface Props {
  deliverable: DeliverableDetails;
}

export function PostsTab({ deliverable }: Props) {
  if (!deliverable.runId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-6">
        <AlertCircle className="h-12 w-12 text-slate-300 mb-3" />
        <p className="text-slate-500 text-sm text-center">
          No run information available
        </p>
        <p className="text-slate-400 text-xs text-center mt-1">
          This deliverable is not associated with a generation run
        </p>
      </div>
    );
  }

  if (deliverable.posts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-6">
        <FileText className="h-12 w-12 text-slate-300 mb-3" />
        <p className="text-slate-500 text-sm text-center">
          No posts found
        </p>
        <p className="text-slate-400 text-xs text-center mt-1">
          No posts were generated in this run
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-3 border-b border-slate-200 bg-slate-50">
        <div className="text-sm text-slate-600">
          {deliverable.posts.length} post{deliverable.posts.length !== 1 ? 's' : ''} in this deliverable
        </div>
      </div>

      {/* Posts list */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {deliverable.posts.map((post) => (
          <div
            key={post.id}
            className="border border-slate-200 rounded-lg p-4 hover:border-slate-300 transition-colors"
          >
            {/* Post header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                {post.templateName && (
                  <div className="text-sm font-medium text-slate-900 mb-1">
                    {post.templateName}
                  </div>
                )}
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  {post.wordCount && (
                    <span>{post.wordCount} words</span>
                  )}
                  {post.readabilityScore !== undefined && post.readabilityScore !== null && (
                    <span>Readability: {post.readabilityScore.toFixed(1)}</span>
                  )}
                </div>
              </div>
              <div>
                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                  post.status === 'approved' ? 'bg-green-100 text-green-800' :
                  post.status === 'flagged' ? 'bg-red-100 text-red-800' :
                  'bg-slate-100 text-slate-800'
                }`}>
                  {post.status}
                </span>
              </div>
            </div>

            {/* Content preview */}
            <div className="text-sm text-slate-700 bg-slate-50 p-3 rounded border border-slate-100">
              {post.contentPreview}
            </div>

            {/* Flags */}
            {post.flags && post.flags.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {post.flags.map((flag, index) => (
                  <span
                    key={index}
                    className="inline-flex px-2 py-0.5 text-xs bg-orange-100 text-orange-800 rounded"
                  >
                    {flag}
                  </span>
                ))}
              </div>
            )}

            {/* Post ID */}
            <div className="mt-2 pt-2 border-t border-slate-100">
              <div className="text-xs font-mono text-slate-400">{post.id}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
