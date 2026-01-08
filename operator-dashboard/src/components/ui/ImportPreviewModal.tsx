import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from './dialog';
import { Button } from './Button';
import type { ParsedBriefResponse } from '../wizard/BriefImportSection';

interface ImportPreviewModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  currentData: Record<string, unknown>;
  importedData: ParsedBriefResponse;
}

export function ImportPreviewModal({
  open,
  onClose,
  onConfirm,
  currentData,
  importedData,
}: ImportPreviewModalProps) {
  const validFields = Object.values(importedData.fields).filter(
    (f) => f.confidence === 'high' || f.confidence === 'medium'
  ).length;
  const totalFields = Object.keys(importedData.fields).length;

  const getConfidenceBadge = (confidence: 'high' | 'medium' | 'low') => {
    const styles = {
      high: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      low: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    };

    return (
      <span className={`ml-2 px-2 py-0.5 rounded text-xs ${styles[confidence]}`}>
        {confidence}
      </span>
    );
  };

  const formatFieldName = (fieldName: string): string => {
    return fieldName
      .replace(/([A-Z])/g, ' $1')
      .trim()
      .replace(/^./, (str) => str.toUpperCase());
  };

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '(empty)';
    if (Array.isArray(value)) return value.join(', ');
    if (typeof value === 'string') {
      return value.length > 100 ? value.substring(0, 97) + '...' : value;
    }
    return String(value);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            Review Imported Data ({validFields}/{totalFields} fields found)
          </DialogTitle>
        </DialogHeader>

        {importedData.warnings.length > 0 && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded p-3 mb-4">
            <p className="font-medium text-yellow-800 dark:text-yellow-400 mb-2">
              Warnings:
            </p>
            <ul className="list-disc list-inside text-sm space-y-1">
              {importedData.warnings.map((warning, i) => (
                <li key={i} className="text-yellow-700 dark:text-yellow-300">
                  {warning}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="space-y-4">
          {Object.entries(importedData.fields).map(([key, data]) => (
            <div
              key={key}
              className="border-b border-gray-200 dark:border-gray-700 pb-3"
            >
              <p className="font-medium text-sm text-gray-900 dark:text-gray-100 mb-2">
                {formatFieldName(key)}
              </p>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400 block mb-1">
                    Current:
                  </span>
                  <p className="text-gray-900 dark:text-gray-100">
                    {formatValue(currentData[key])}
                  </p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400 block mb-1">
                    Imported:
                  </span>
                  <p className="text-gray-900 dark:text-gray-100">
                    {formatValue(data.value)}
                    {getConfidenceBadge(data.confidence)}
                  </p>
                  {data.source && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Source: {data.source}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-between items-center mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            <p>Parse time: {importedData.metadata.parseTimeMs}ms</p>
            <p>File: {importedData.metadata.filename}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={onConfirm}>
              Import {validFields} Valid Field{validFields !== 1 ? 's' : ''}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
