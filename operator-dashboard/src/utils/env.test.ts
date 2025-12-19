import { describe, expect, it, beforeEach, afterEach, jest } from '@jest/globals';
import { getApiBaseUrl, getEnvConfig, getUseMocksEnabled } from './env';

describe('env helpers', () => {
  const originalEnv = (globalThis as any).__ENV__;
  const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => undefined);

  beforeEach(() => {
    (globalThis as any).__ENV__ = {};
    warnSpy.mockClear();
  });

  afterEach(() => {
    (globalThis as any).__ENV__ = originalEnv;
  });

  it('falls back to default API URL and warns when missing', () => {
    const apiUrl = getApiBaseUrl();
    expect(apiUrl).toBe('http://localhost:8000');
    expect(warnSpy).toHaveBeenCalled();
  });

  it('normalizes and validates API URL', () => {
    (globalThis as any).__ENV__ = { VITE_API_URL: 'https://example.com/' };
    const apiUrl = getApiBaseUrl();
    expect(apiUrl).toBe('https://example.com');
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it('handles invalid API URL with fallback', () => {
    (globalThis as any).__ENV__ = { VITE_API_URL: 'not-a-url' };
    const apiUrl = getApiBaseUrl();
    expect(apiUrl).toBe('http://localhost:8000');
    expect(warnSpy).toHaveBeenCalled();
  });

  it('interprets mock flag correctly', () => {
    (globalThis as any).__ENV__ = { VITE_USE_MOCKS: 'true' };
    expect(getUseMocksEnabled()).toBe(true);
    (globalThis as any).__ENV__ = { VITE_USE_MOCKS: 'false' };
    expect(getUseMocksEnabled()).toBe(false);
  });

  it('returns env snapshot', () => {
    (globalThis as any).__ENV__ = {
      VITE_API_URL: 'https://api.test',
      VITE_USE_MOCKS: 'true',
      VITE_DEBUG_MODE: 'true',
      MODE: 'test',
    };
    const config = getEnvConfig();
    expect(config).toEqual({
      apiUrl: 'https://api.test',
      useMocks: true,
      debugMode: true,
      mode: 'test',
    });
  });
});
