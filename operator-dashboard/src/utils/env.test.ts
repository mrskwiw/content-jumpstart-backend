import { describe, expect, it, beforeEach, afterEach, jest } from '@jest/globals';
import { getApiBaseUrl, getEnvConfig, getUseMocksEnabled } from './env';

type GlobalWithEnv = typeof globalThis & {
  __ENV__?: Record<string, string | undefined>;
};

describe('env helpers', () => {
  const originalEnv = (globalThis as GlobalWithEnv).__ENV__;
  const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => undefined);

  beforeEach(() => {
    (globalThis as GlobalWithEnv).__ENV__ = {};
    warnSpy.mockClear();
  });

  afterEach(() => {
    (globalThis as GlobalWithEnv).__ENV__ = originalEnv;
  });

  it('falls back to default API URL and warns when missing', () => {
    const apiUrl = getApiBaseUrl();
    expect(apiUrl).toBe('http://localhost:8000');
    expect(warnSpy).toHaveBeenCalled();
  });

  it('normalizes and validates API URL', () => {
    (globalThis as GlobalWithEnv).__ENV__ = { VITE_API_URL: 'https://example.com/' };
    const apiUrl = getApiBaseUrl();
    expect(apiUrl).toBe('https://example.com');
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it('handles invalid API URL with fallback', () => {
    (globalThis as GlobalWithEnv).__ENV__ = { VITE_API_URL: 'not-a-url' };
    const apiUrl = getApiBaseUrl();
    expect(apiUrl).toBe('http://localhost:8000');
    expect(warnSpy).toHaveBeenCalled();
  });

  it('interprets mock flag correctly', () => {
    (globalThis as GlobalWithEnv).__ENV__ = { VITE_USE_MOCKS: 'true' };
    expect(getUseMocksEnabled()).toBe(true);
    (globalThis as GlobalWithEnv).__ENV__ = { VITE_USE_MOCKS: 'false' };
    expect(getUseMocksEnabled()).toBe(false);
  });

  it('returns env snapshot', () => {
    (globalThis as GlobalWithEnv).__ENV__ = {
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
