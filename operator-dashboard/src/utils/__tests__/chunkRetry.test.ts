/**
 * Comprehensive tests for chunkRetry utility
 */
import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import {
  isChunkLoadError,
  retryChunkImport,
  setupChunkErrorHandler,
} from '../chunkRetry';

describe('chunkRetry', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('isChunkLoadError', () => {
    it('should return true for chunk load error messages', () => {
      expect(isChunkLoadError(new Error('Failed to fetch dynamically imported module'))).toBe(true);
      expect(isChunkLoadError(new Error('Importing a module script failed'))).toBe(true);
      expect(isChunkLoadError(new Error('error loading dynamically imported module'))).toBe(true);
      expect(isChunkLoadError(new Error('ChunkLoadError: Loading chunk failed'))).toBe(true);
    });

    it('should return true for network errors', () => {
      expect(isChunkLoadError(new Error('Failed to fetch'))).toBe(true);
      expect(isChunkLoadError(new Error('NetworkError when attempting to fetch'))).toBe(true);
    });

    it('should return false for non-chunk errors', () => {
      expect(isChunkLoadError(new Error('Regular error'))).toBe(false);
      expect(isChunkLoadError(new Error('Syntax error'))).toBe(false);
      expect(isChunkLoadError(new Error('TypeError'))).toBe(false);
    });

    it('should return false for null/undefined', () => {
      expect(isChunkLoadError(null)).toBe(false);
      expect(isChunkLoadError(undefined)).toBe(false);
    });

    it('should handle string errors', () => {
      expect(isChunkLoadError('Failed to fetch dynamically imported module')).toBe(true);
      expect(isChunkLoadError('Random error string')).toBe(false);
    });
  });

  describe('retryChunkImport', () => {
    it('should successfully import on first try', async () => {
      const mockImport = jest.fn<() => Promise<{ default: string }>>().mockResolvedValue({ default: 'Component' });

      const result = await retryChunkImport(mockImport);

      expect(result).toEqual({ default: 'Component' });
      expect(mockImport).toHaveBeenCalledTimes(1);
    });

    it('should retry on chunk load error', async () => {
      const mockImport = jest
        .fn<() => Promise<{ default: string }>>()
        .mockRejectedValueOnce(new Error('Failed to fetch dynamically imported module'))
        .mockResolvedValueOnce({ default: 'Component' });

      // Default maxRetries is 1 (a single attempt, no retry) — opt in to a retry.
      const promise = retryChunkImport(mockImport, { maxRetries: 2 });

      // Fast-forward through the delay
      await jest.advanceTimersByTimeAsync(1000);

      const result = await promise;

      expect(result).toEqual({ default: 'Component' });
      expect(mockImport).toHaveBeenCalledTimes(2);
    });

    it('should not retry on non-chunk errors', async () => {
      const mockImport = jest.fn<() => Promise<unknown>>().mockRejectedValue(new Error('Syntax error'));

      await expect(retryChunkImport(mockImport)).rejects.toThrow('Syntax error');
      expect(mockImport).toHaveBeenCalledTimes(1);
    });

    it('should use exponential backoff for retries', async () => {
      const mockImport = jest
        .fn<() => Promise<{ default: string }>>()
        .mockRejectedValueOnce(new Error('Failed to fetch dynamically imported module'))
        .mockRejectedValueOnce(new Error('Failed to fetch dynamically imported module'))
        .mockResolvedValueOnce({ default: 'Component' });

      const promise = retryChunkImport(mockImport, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 5000,
      });

      // First retry: 1000ms delay
      await jest.advanceTimersByTimeAsync(1000);
      // Second retry: 2000ms delay (exponential)
      await jest.advanceTimersByTimeAsync(2000);

      const result = await promise;

      expect(result).toEqual({ default: 'Component' });
      expect(mockImport).toHaveBeenCalledTimes(3);
    });

    it('should cap delay at maxDelay', async () => {
      const mockImport = jest
        .fn<() => Promise<{ default: string }>>()
        .mockRejectedValueOnce(new Error('Failed to fetch dynamically imported module'))
        .mockRejectedValueOnce(new Error('Failed to fetch dynamically imported module'))
        .mockResolvedValueOnce({ default: 'Component' });

      const promise = retryChunkImport(mockImport, {
        maxRetries: 3,
        initialDelay: 5000,
        maxDelay: 6000,
      });

      // Delay should be capped at 6000ms, not 10000ms (5000 * 2)
      await jest.advanceTimersByTimeAsync(5000);
      await jest.advanceTimersByTimeAsync(6000);

      const result = await promise;
      expect(result).toEqual({ default: 'Component' });
    });

    it('should reload page after max retries by default', async () => {
      const mockReload = jest.fn();
      Object.defineProperty(window, 'location', {
        value: { reload: mockReload },
        writable: true,
      });

      const mockImport = jest.fn<() => Promise<unknown>>().mockRejectedValue(new Error('Failed to fetch dynamically imported module'));

      // When retries are exhausted with shouldReload=true (the default), the util
      // triggers window.location.reload() and returns a deliberately
      // never-resolving promise (to halt further execution before the reload).
      // We must NOT await that promise — attach a no-op catch and assert on the
      // side effect (reload) once the retry timers have flushed.
      const promise = retryChunkImport(mockImport, { maxRetries: 2 });
      promise.catch(() => {});

      await jest.advanceTimersByTimeAsync(1000);
      await jest.advanceTimersByTimeAsync(2000);

      expect(mockReload).toHaveBeenCalled();
      expect(mockImport).toHaveBeenCalledTimes(2);
    });

    it('should throw error instead of reloading when shouldReload is false', async () => {
      const mockImport = jest.fn<() => Promise<unknown>>().mockRejectedValue(new Error('Failed to fetch dynamically imported module'));

      const promise = retryChunkImport(mockImport, { maxRetries: 2, shouldReload: false });

      // Attach the rejection expectation BEFORE advancing timers so the eventual
      // rejection is never briefly unhandled (which would fail the test run).
      const assertion = expect(promise).rejects.toThrow('Failed to fetch dynamically imported module');

      await jest.advanceTimersByTimeAsync(1000);

      await assertion;
      expect(mockImport).toHaveBeenCalledTimes(2);
    });

    it('should respect custom maxRetries', async () => {
      const mockImport = jest.fn<() => Promise<unknown>>().mockRejectedValue(new Error('Failed to fetch dynamically imported module'));

      const promise = retryChunkImport(mockImport, { maxRetries: 5, shouldReload: false });

      // Attach the rejection expectation before advancing timers to avoid a
      // transiently-unhandled rejection failing the test run.
      const assertion = expect(promise).rejects.toThrow();

      for (let i = 0; i < 4; i++) {
        await jest.advanceTimersByTimeAsync(Math.min(1000 * Math.pow(2, i), 5000));
      }

      await assertion;
      expect(mockImport).toHaveBeenCalledTimes(5);
    });
  });

  describe('setupChunkErrorHandler', () => {
    let mockReload: jest.Mock;
    let errorListeners: ((event: any) => void)[] = [];
    let rejectionListeners: ((event: any) => void)[] = [];

    beforeEach(() => {
      mockReload = jest.fn();
      Object.defineProperty(window, 'location', {
        value: { reload: mockReload },
        writable: true,
      });

      errorListeners = [];
      rejectionListeners = [];

      window.addEventListener = jest.fn((event, handler: any) => {
        if (event === 'error') {
          errorListeners.push(handler);
        } else if (event === 'unhandledrejection') {
          rejectionListeners.push(handler);
        }
      });
    });

    it('should set up error event listener', () => {
      setupChunkErrorHandler();
      expect(window.addEventListener).toHaveBeenCalledWith('error', expect.any(Function));
    });

    it('should set up unhandledrejection event listener', () => {
      setupChunkErrorHandler();
      expect(window.addEventListener).toHaveBeenCalledWith('unhandledrejection', expect.any(Function));
    });

    it('should reload on chunk load error event', () => {
      setupChunkErrorHandler();

      const event = {
        error: new Error('Failed to fetch dynamically imported module'),
        preventDefault: jest.fn(),
      };

      errorListeners.forEach(listener => listener(event));

      expect(event.preventDefault).toHaveBeenCalled();
      expect(mockReload).toHaveBeenCalled();
    });

    it('should not reload on non-chunk error event', () => {
      setupChunkErrorHandler();

      const event = {
        error: new Error('Regular error'),
        preventDefault: jest.fn(),
      };

      errorListeners.forEach(listener => listener(event));

      expect(event.preventDefault).not.toHaveBeenCalled();
      expect(mockReload).not.toHaveBeenCalled();
    });

    it('should reload on chunk load promise rejection', () => {
      setupChunkErrorHandler();

      const event = {
        reason: new Error('Failed to fetch dynamically imported module'),
        preventDefault: jest.fn(),
      };

      rejectionListeners.forEach(listener => listener(event));

      expect(event.preventDefault).toHaveBeenCalled();
      expect(mockReload).toHaveBeenCalled();
    });

    it('should not reload on non-chunk promise rejection', () => {
      setupChunkErrorHandler();

      const event = {
        reason: new Error('Regular error'),
        preventDefault: jest.fn(),
      };

      rejectionListeners.forEach(listener => listener(event));

      expect(event.preventDefault).not.toHaveBeenCalled();
      expect(mockReload).not.toHaveBeenCalled();
    });
  });
});
