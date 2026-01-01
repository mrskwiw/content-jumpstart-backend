import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { FileUpload } from '../ui/FileUpload';
import { Button } from '../ui/Button';
import { briefImportService, type ParsedBriefResponse, type ParsedField } from '@/services/briefImportService';

// Re-export types for use in other components
export type { ParsedField, ParsedBriefResponse };

interface BriefImportSectionProps {
  onImport: (parsedData: ParsedBriefResponse) => void;
}

interface ErrorState {
  code: string;
  message: string;
  retryable: boolean;
}

export function BriefImportSection({ onImport }: BriefImportSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<ErrorState | null>(null);

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);

    try {
      const parsed = await briefImportService.parseFile(file);
      onImport(parsed);
    } catch (err: any) {
      // Determine if error is retryable
      const message = err.message || 'Failed to parse brief';
      const isRetryable =
        message.includes('timed out') ||
        message.includes('Network error') ||
        message.includes('Failed to parse brief');

      setError({
        code: err.code || 'UNKNOWN_ERROR',
        message: message,
        retryable: isRetryable,
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="mb-6 border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full text-left"
        type="button"
      >
        <span className="font-medium text-gray-900 dark:text-gray-100">
          📁 Import Client Brief
        </span>
        <span className="text-gray-500 dark:text-gray-400 text-xl font-light">
          {isOpen ? '−' : '+'}
        </span>
      </button>

      {isOpen && (
        <div className="mt-4 space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Upload a client brief file (.txt or .md) to auto-populate form fields.
          </p>

          <FileUpload
            accept=".txt,.md"
            maxSizeMB={0.05}
            onFileSelect={setFile}
            disabled={isUploading}
          />

          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3 space-y-2">
              <p className="text-sm font-medium text-red-800 dark:text-red-400">
                {error.message}
              </p>
              {error.retryable && (
                <Button
                  onClick={handleUpload}
                  disabled={!file}
                  variant="outline"
                  size="sm"
                  type="button"
                  className="mt-2"
                >
                  Retry Upload
                </Button>
              )}
            </div>
          )}

          <Button
            onClick={handleUpload}
            disabled={!file || isUploading}
            type="button"
          >
            {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isUploading ? 'Parsing...' : 'Upload and Parse'}
          </Button>
        </div>
      )}
    </div>
  );
}
