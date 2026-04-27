import { ResearchResult } from '@/types/domain';
import { X, Download, FileText, Code2, Info } from 'lucide-react';
import { useState } from 'react';

interface ResultDetailModalProps {
  result: ResearchResult;
  onClose: () => void;
}

export function ResultDetailModal({ result, onClose }: ResultDetailModalProps) {
  const [activeTab, setActiveTab] = useState<'preview' | 'data' | 'metadata'>('preview');
  const [primaryOutputName, primaryOutputContent] = Object.entries(result.outputs)[0] ?? [
    'output',
    '',
  ];

  const handleDownload = () => {
    const payload = JSON.stringify(
      {
        id: result.id,
        toolName: result.toolName,
        toolLabel: result.toolLabel,
        outputs: result.outputs,
        data: result.data,
        metadata: {
          status: result.status,
          durationSeconds: result.durationSeconds,
          toolPrice: result.toolPrice,
          actualCostUsd: result.actualCostUsd,
          createdAt: result.createdAt,
        },
      },
      null,
      2
    );
    const blob = new Blob([payload], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${result.toolName}-${result.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-neutral-700">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              {result.toolLabel || 'Research Result'}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {new Date(result.createdAt).toLocaleString()}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-neutral-700 px-6">
          <TabButton
            active={activeTab === 'preview'}
            onClick={() => setActiveTab('preview')}
            icon={<FileText className="h-4 w-4" />}
            label="Preview"
          />
          <TabButton
            active={activeTab === 'data'}
            onClick={() => setActiveTab('data')}
            icon={<Code2 className="h-4 w-4" />}
            label="Structured Data"
          />
          <TabButton
            active={activeTab === 'metadata'}
            onClick={() => setActiveTab('metadata')}
            icon={<Info className="h-4 w-4" />}
            label="Execution Details"
          />
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          <>
            {activeTab === 'preview' && (
              <div className="space-y-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  {primaryOutputName}
                </div>
                <div className="prose dark:prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm text-gray-800 dark:bg-neutral-800 dark:text-gray-100">
                    {primaryOutputContent || 'No output content available.'}
                  </pre>
                </div>
              </div>
            )}
            {activeTab === 'data' && (
              <div className="bg-gray-50 dark:bg-neutral-800 rounded-lg p-4">
                <pre className="text-sm text-gray-900 dark:text-gray-100 overflow-auto">
                  {JSON.stringify(result.data || result.outputs || {}, null, 2)}
                </pre>
              </div>
            )}
            {activeTab === 'metadata' && (
              <div className="space-y-4">
                <MetadataRow label="Status" value={result.status || '—'} />
                <MetadataRow
                  label="Duration"
                  value={result.durationSeconds ? `${result.durationSeconds}s` : '—'}
                />
                <MetadataRow
                  label="Business Price"
                  value={result.toolPrice ? `$${result.toolPrice}` : '—'}
                />
                <MetadataRow
                  label="Actual API Cost"
                  value={result.actualCostUsd ? `$${result.actualCostUsd.toFixed(4)}` : '—'}
                />
              </div>
            )}
          </>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-neutral-700">
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <Download className="h-4 w-4" />
            Download All
          </button>
        </div>
      </div>
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

function TabButton({ active, onClick, icon, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
        active
          ? 'border-blue-600 text-blue-600 dark:text-blue-400'
          : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

interface MetadataRowProps {
  label: string;
  value: string;
}

function MetadataRow({ label, value }: MetadataRowProps) {
  return (
    <div className="flex justify-between py-2 border-b border-gray-200 dark:border-neutral-700">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
      <span className="text-sm text-gray-600 dark:text-gray-400">{value}</span>
    </div>
  );
}
