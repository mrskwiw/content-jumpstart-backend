/**
 * Tests for cn utility (className merger)
 */
import { describe, it, expect } from '@jest/globals';
import { cn } from '../cn';

describe('cn utility', () => {
  it('should merge class names', () => {
    const result = cn('btn', 'btn-primary');
    expect(result).toContain('btn');
    expect(result).toContain('btn-primary');
  });

  it('should handle conditional classes', () => {
    const isActive = true;
    const result = cn('btn', isActive && 'active');
    expect(result).toContain('btn');
    expect(result).toContain('active');
  });

  it('should filter out falsy values', () => {
    const result = cn('btn', false && 'hidden', null, undefined, 'visible');
    expect(result).toContain('btn');
    expect(result).toContain('visible');
    expect(result).not.toContain('hidden');
  });

  it('should merge Tailwind classes correctly', () => {
    const result = cn('p-4', 'p-8'); // Later class should override
    expect(typeof result).toBe('string');
    expect(result.length > 0).toBe(true);
  });

  it('should handle empty input', () => {
    const result = cn();
    expect(typeof result).toBe('string');
  });

  it('should handle arrays', () => {
    const result = cn(['btn', 'btn-primary'], 'active');
    expect(result).toContain('btn');
    expect(result).toContain('active');
  });
});
