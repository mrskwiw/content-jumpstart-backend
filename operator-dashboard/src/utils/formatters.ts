/**
 * Utility functions for formatting data for display.
 */

/**
 * Format bytes to human-readable file size.
 *
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "1.5 MB", "234 KB")
 *
 * @example
 * formatFileSize(1024) // "1.0 KB"
 * formatFileSize(1536) // "1.5 KB"
 * formatFileSize(1048576) // "1.0 MB"
 * formatFileSize(0) // "0 B"
 * formatFileSize(undefined) // "Unknown"
 */
export function formatFileSize(bytes: number | undefined | null): string {
  if (bytes === undefined || bytes === null) {
    return 'Unknown';
  }

  if (bytes === 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let unitIndex = 0;
  let size = bytes;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  // Format with appropriate precision
  if (size < 10) {
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  } else {
    return `${Math.round(size)} ${units[unitIndex]}`;
  }
}
