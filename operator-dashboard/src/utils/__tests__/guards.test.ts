/**
 * Tests for path guards/validators
 */
import { describe, it, expect } from '@jest/globals';
import { isSafeRelativePath } from '../guards';

describe('isSafeRelativePath', () => {
  it('should return false for empty string', () => {
    expect(isSafeRelativePath('')).toBe(false);
  });

  it('should return false for paths starting with /', () => {
    expect(isSafeRelativePath('/etc/passwd')).toBe(false);
    expect(isSafeRelativePath('/absolute/path')).toBe(false);
  });

  it('should return false for paths starting with \\', () => {
    expect(isSafeRelativePath('\\windows\\system32')).toBe(false);
    expect(isSafeRelativePath('\\absolute\\path')).toBe(false);
  });

  it('should return false for paths containing ..', () => {
    expect(isSafeRelativePath('../etc/passwd')).toBe(false);
    expect(isSafeRelativePath('foo/../bar')).toBe(false);
    expect(isSafeRelativePath('../../secrets')).toBe(false);
  });

  it('should return false for absolute paths with protocol', () => {
    expect(isSafeRelativePath('http://example.com/file')).toBe(false);
    expect(isSafeRelativePath('https://evil.com/malware')).toBe(false);
    expect(isSafeRelativePath('file:///etc/passwd')).toBe(false);
    expect(isSafeRelativePath('ftp://server/file')).toBe(false);
  });

  it('should return true for safe relative paths', () => {
    expect(isSafeRelativePath('file.txt')).toBe(true);
    expect(isSafeRelativePath('folder/file.txt')).toBe(true);
    expect(isSafeRelativePath('path/to/file.txt')).toBe(true);
    expect(isSafeRelativePath('subfolder/nested/deep/file.txt')).toBe(true);
  });

  it('should return true for paths with dots that are not ..', () => {
    expect(isSafeRelativePath('file.name.txt')).toBe(true);
    expect(isSafeRelativePath('.env')).toBe(true);
    expect(isSafeRelativePath('.hidden/file')).toBe(true);
  });

  it('should return true for paths with numbers and special chars', () => {
    expect(isSafeRelativePath('file-123.txt')).toBe(true);
    expect(isSafeRelativePath('my_file.txt')).toBe(true);
    expect(isSafeRelativePath('folder-name/file.txt')).toBe(true);
  });
});
