import type { DeliverableDetails } from '@/types/domain';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FileText, AlertCircle } from 'lucide-react';

interface Props {
  deliverable: DeliverableDetails;
}

export function PreviewTab({ deliverable }: Props) {
  if (!deliverable.filePreview) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-6">
        <AlertCircle className="h-12 w-12 text-slate-300 mb-3" />
        <p className="text-slate-500 text-sm text-center">
          File preview not available
        </p>
        <p className="text-slate-400 text-xs text-center mt-1">
          The file may not exist or cannot be previewed
        </p>
      </div>
    );
  }

  const isMarkdown = deliverable.format === 'txt' || deliverable.path.endsWith('.md');
  const charCount = deliverable.filePreview.length;

  return (
    <div className="flex flex-col h-full">
      {/* Header with info */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <FileText className="h-4 w-4" />
          <span>
            {charCount.toLocaleString()} characters
            {deliverable.filePreviewTruncated && ' (truncated)'}
          </span>
        </div>
        {deliverable.filePreviewTruncated && (
          <div className="text-xs text-orange-600">
            Preview limited to first 5,000 characters
          </div>
        )}
      </div>

      {/* Content preview */}
      <div className="flex-1 overflow-y-auto">
        {isMarkdown ? (
          <SyntaxHighlighter
            language="markdown"
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              borderRadius: 0,
              fontSize: '13px',
              lineHeight: '1.5',
            }}
            showLineNumbers
            wrapLongLines
          >
            {deliverable.filePreview}
          </SyntaxHighlighter>
        ) : (
          <pre className="p-6 text-xs font-mono text-slate-700 whitespace-pre-wrap bg-slate-50">
            {deliverable.filePreview}
          </pre>
        )}
      </div>
    </div>
  );
}
