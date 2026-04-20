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

      // VALIDATION: Check required fields
      const companyName = parsed.fields.companyName?.value;
      const hasCompanyName = companyName && typeof companyName === 'string' && companyName.trim().length > 0;

      if (!parsed.success || !hasCompanyName) {
        const missingFields: string[] = [];
        if (!hasCompanyName) missingFields.push('Company Name');

        const errorMessage = !parsed.success
          ? 'Brief parsing failed. AI could not extract required information.'
          : `Brief incomplete. Missing: ${missingFields.join(', ')}`;

        const details = [
          errorMessage,
          '',
          'Common causes:',
          '• API authentication failed (check ANTHROPIC_API_KEY in Render)',
          '• Brief format not recognized',
          '• Company information not clearly stated',
          '',
          'To fix:',
          '1. Verify API key in Render environment variables',
          '2. Ensure brief has clear company name',
          '3. Retry upload after fixing API key',
          '4. Or enter information manually below',
        ].join('\n');

        throw new Error(details);
      }

      onImport(parsed);
    } catch (err: unknown) {
      // Determine if error is retryable
      const message = err instanceof Error ? err.message : 'Failed to parse brief';
      const isRetryable =
        message.includes('timed out') ||
        message.includes('Network error') ||
        message.includes('Failed to parse') ||
        message.includes('authentication') ||
        message.includes('Missing');

      setError({
        code: (err && typeof err === 'object' && 'code' in err && typeof err.code === 'string') ? err.code : 'UNKNOWN_ERROR',
        message: message,
        retryable: isRetryable,
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="mb-6 border border-neutral-200 dark:border-neutral-700 rounded-lg p-4 bg-neutral-50 dark:bg-neutral-800">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full text-left"
        type="button"
      >
        <span className="font-medium text-neutral-900 dark:text-neutral-100">
          📁 Import Client Brief
        </span>
        <span className="text-neutral-500 dark:text-neutral-400 text-xl font-light">
          {isOpen ? '−' : '+'}
        </span>
      </button>

      {isOpen && (
        <div className="mt-4 space-y-4">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Upload a client brief file (.txt, .md, or .docx) to auto-populate form fields.
          </p>

          <FileUpload
            accept=".txt,.md,.docx"
            maxSizeMB={5}
            onFileSelect={setFile}
            disabled={isUploading}
          />

          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3 space-y-2">
              <p className="text-sm font-medium text-red-800 dark:text-red-400 whitespace-pre-wrap">
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
