/**
 * Tests for formatters utility functions
 */
import { describe, it, expect } from '@jest/globals';
import { formatFileSize } from '../formatters';

describe('formatFileSize', () => {
  it('should return "Unknown" for undefined', () => {
    expect(formatFileSize(undefined)).toBe('Unknown');
  });

  it('should return "Unknown" for null', () => {
    expect(formatFileSize(null)).toBe('Unknown');
  });

  it('should return "0 B" for zero bytes', () => {
    expect(formatFileSize(0)).toBe('0 B');
  });

  it('should format bytes (< 1024)', () => {
    expect(formatFileSize(100)).toBe('100 B');
    expect(formatFileSize(1023)).toBe('1023 B');
  });

  it('should format kilobytes with 1 decimal for small values', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(2048)).toBe('2.0 KB');
    expect(formatFileSize(5120)).toBe('5.0 KB');
  });

  it('should format kilobytes as integers for large values', () => {
    expect(formatFileSize(10240)).toBe('10 KB');
    expect(formatFileSize(51200)).toBe('50 KB');
    expect(formatFileSize(102400)).toBe('100 KB');
  });

  it('should format megabytes with 1 decimal for small values', () => {
    expect(formatFileSize(1048576)).toBe('1.0 MB'); // 1 MB
    expect(formatFileSize(1572864)).toBe('1.5 MB'); // 1.5 MB
    expect(formatFileSize(5242880)).toBe('5.0 MB'); // 5 MB
  });

  it('should format megabytes as integers for large values', () => {
    expect(formatFileSize(10485760)).toBe('10 MB'); // 10 MB
    expect(formatFileSize(104857600)).toBe('100 MB'); // 100 MB
  });

  it('should format gigabytes', () => {
    expect(formatFileSize(1073741824)).toBe('1.0 GB'); // 1 GB
    expect(formatFileSize(5368709120)).toBe('5.0 GB'); // 5 GB
    expect(formatFileSize(10737418240)).toBe('10 GB'); // 10 GB
  });

  it('should format terabytes', () => {
    expect(formatFileSize(1099511627776)).toBe('1.0 TB'); // 1 TB
    expect(formatFileSize(5497558138880)).toBe('5.0 TB'); // 5 TB
  });

  it('should not exceed TB unit', () => {
    // Even for petabytes, should stay at TB
    expect(formatFileSize(1125899906842624)).toBe('1024 TB'); // 1 PB in TB
  });

  it('should handle fractional results correctly', () => {
    expect(formatFileSize(1536000)).toBe('1.5 MB');
    expect(formatFileSize(2621440)).toBe('2.5 MB');
  });
});
