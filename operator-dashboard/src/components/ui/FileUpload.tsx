import React, { useState } from 'react';
import { Input } from './Input';

interface FileUploadProps {
  accept: string;
  maxSizeMB: number;
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

export function FileUpload({ accept, maxSizeMB, onFileSelect, disabled }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string>('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    const acceptedExts = accept.split(',').map(a => a.trim().replace('.', ''));

    if (!ext || !acceptedExts.includes(ext)) {
      setError(`Invalid file type. Expected: ${accept}`);
      setSelectedFile(null);
      return;
    }

    // Validate size
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      setError(`File too large. Max size: ${maxSizeMB}MB`);
      setSelectedFile(null);
      return;
    }

    setError('');
    setSelectedFile(file);
    onFileSelect(file);
  };

  return (
    <div className="space-y-2">
      <Input
        type="file"
        accept={accept}
        onChange={handleChange}
        disabled={disabled}
        className="cursor-pointer"
      />
      {selectedFile && (
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
        </p>
      )}
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
