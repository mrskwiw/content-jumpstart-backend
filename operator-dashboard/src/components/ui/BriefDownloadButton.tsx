import { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { clientResearchApi, type BriefFormat } from '@/api/clientResearch';

interface Props {
  brief: Record<string, unknown>;
  confidence: Record<string, number>;
  companyName?: string;
}

const FORMATS: { value: BriefFormat; label: string }[] = [
  { value: 'md', label: 'MD' },
  { value: 'docx', label: 'DOCX' },
  { value: 'pdf', label: 'PDF' },
];

export function BriefDownloadButton({ brief, confidence, companyName }: Props) {
  const [selected, setSelected] = useState<BriefFormat>('md');
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    setIsDownloading(true);
    setError(null);
    try {
      await clientResearchApi.downloadBrief(brief, confidence, selected, companyName);
    } catch {
      setError('Download failed. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-0">
        {/* Format toggle */}
        <div className="flex rounded-l-md overflow-hidden border border-neutral-300 dark:border-neutral-600">
          {FORMATS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setSelected(value)}
              className={[
                'px-3 py-1.5 text-xs font-medium transition-colors',
                selected === value
                  ? 'bg-primary-600 text-white'
                  : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Download button */}
        <button
          type="button"
          onClick={handleDownload}
          disabled={isDownloading}
          className="flex items-center gap-1.5 rounded-r-md border border-l-0 border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 disabled:opacity-50 transition-colors"
        >
          {isDownloading ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Download className="h-3 w-3" />
          )}
          {isDownloading ? 'Downloading…' : 'Download'}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
