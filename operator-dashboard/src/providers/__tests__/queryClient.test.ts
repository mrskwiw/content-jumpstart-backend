/**
 * Tests for queryClient configuration
 */
import { describe, it, expect } from '@jest/globals';
import { queryClient } from '../queryClient';

describe('queryClient', () => {
  it('should be defined', () => {
    expect(queryClient).toBeDefined();
  });

  it('should have default options configured', () => {
    const defaultOptions = queryClient.getDefaultOptions();
    expect(defaultOptions).toBeDefined();
  });

  it('should have query defaults', () => {
    const defaultOptions = queryClient.getDefaultOptions();
    expect(defaultOptions.queries).toBeDefined();
  });

  it('should have mutation defaults', () => {
    const defaultOptions = queryClient.getDefaultOptions();
    expect(defaultOptions.mutations).toBeDefined();
  });
});
