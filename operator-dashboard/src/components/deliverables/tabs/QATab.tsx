import type { DeliverableDetails } from '@/types/domain';
import { CheckCircle2, AlertCircle, BarChart3 } from 'lucide-react';

interface Props {
  deliverable: DeliverableDetails;
}

export function QATab({ deliverable }: Props) {
  if (!deliverable.qaSummary) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-6">
        <AlertCircle className="h-12 w-12 text-slate-300 mb-3" />
        <p className="text-slate-500 text-sm text-center">
          No quality metrics available
        </p>
        <p className="text-slate-400 text-xs text-center mt-1">
          Quality analysis requires posts from a generation run
        </p>
      </div>
    );
  }

  const qa = deliverable.qaSummary;
  const approvalRate = qa.totalPosts > 0
    ? (qa.approvedCount / qa.totalPosts * 100).toFixed(1)
    : '0';

  return (
    <div className="p-6 space-y-6">
      {/* Summary stats */}
      <div>
        <h3 className="text-sm font-medium text-slate-900 mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Quality Summary
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-50 p-4 rounded-lg">
            <div className="text-xs text-slate-500 uppercase">Total Posts</div>
            <div className="text-2xl font-semibold text-slate-900 mt-1">
              {qa.totalPosts}
            </div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-xs text-green-600 uppercase">Approved</div>
            <div className="text-2xl font-semibold text-green-700 mt-1">
              {qa.approvedCount}
              <span className="text-sm text-green-600 ml-2">({approvalRate}%)</span>
            </div>
          </div>
          {qa.flaggedCount > 0 && (
            <div className="bg-red-50 p-4 rounded-lg">
              <div className="text-xs text-red-600 uppercase">Flagged</div>
              <div className="text-2xl font-semibold text-red-700 mt-1">
                {qa.flaggedCount}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Metrics */}
      <div>
        <h3 className="text-sm font-medium text-slate-900 mb-3">Content Metrics</h3>
        <div className="space-y-3">
          {qa.avgReadability !== null && qa.avgReadability !== undefined && (
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-sm text-slate-600">Average Readability</span>
              <span className="text-sm font-medium text-slate-900">
                {qa.avgReadability.toFixed(1)}
              </span>
            </div>
          )}
          {qa.avgWordCount !== null && qa.avgWordCount !== undefined && (
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-sm text-slate-600">Average Word Count</span>
              <span className="text-sm font-medium text-slate-900">
                {Math.round(qa.avgWordCount)} words
              </span>
            </div>
          )}
          {qa.ctaPercentage !== null && qa.ctaPercentage !== undefined && (
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-sm text-slate-600">Posts with CTA</span>
              <span className="text-sm font-medium text-slate-900">
                {qa.ctaPercentage.toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Common flags */}
      {qa.commonFlags && qa.commonFlags.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-900 mb-3">Common Issues</h3>
          <div className="space-y-2">
            {qa.commonFlags.map((flag, index) => (
              <div
                key={index}
                className="flex items-center gap-2 text-sm text-slate-600 bg-orange-50 p-2 rounded"
              >
                <AlertCircle className="h-4 w-4 text-orange-600 flex-shrink-0" />
                <span>{flag}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quality indicator */}
      <div className="pt-4 border-t border-slate-200">
        {parseFloat(approvalRate) >= 90 ? (
          <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 p-3 rounded">
            <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
            <span className="font-medium">
              Excellent quality - {approvalRate}% approval rate
            </span>
          </div>
        ) : parseFloat(approvalRate) >= 70 ? (
          <div className="flex items-center gap-2 text-sm text-blue-700 bg-blue-50 p-3 rounded">
            <BarChart3 className="h-5 w-5 flex-shrink-0" />
            <span className="font-medium">
              Good quality - {approvalRate}% approval rate
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-orange-700 bg-orange-50 p-3 rounded">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span className="font-medium">
              Needs review - {approvalRate}% approval rate
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
