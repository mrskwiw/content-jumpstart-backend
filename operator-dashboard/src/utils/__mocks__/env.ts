/**
 * Jest mock for env.ts
 * Uses globalThis.__ENV__ shim set up in jest.setup.ts
 * Avoids import.meta syntax which causes parse errors in Jest
 */

const FALLBACK_API_URL = 'http://localhost:8000';

function getEnvValue(key: string): string | undefined {
  const env = (globalThis as any).__ENV__ || {};
  return env[key];
}

export function getApiBaseUrl(): string {
  const value = getEnvValue('VITE_API_URL');
  const mode = getEnvValue('MODE') || 'test';

  if (!value) {
    if (mode === 'production') {
      return '';  // Relative URLs
    }
    return FALLBACK_API_URL;
  }

  try {
    const normalized = new URL(value).toString();
    return normalized.endsWith('/') ? normalized.slice(0, -1) : normalized;
  } catch {
    return FALLBACK_API_URL;
  }
}

export function getUseMocksEnabled(): boolean {
  const raw = getEnvValue('VITE_USE_MOCKS');
  return raw === 'true';
}

export function getDebugModeEnabled(): boolean {
  const raw = getEnvValue('VITE_DEBUG_MODE');
  return raw === 'true';
}

export function getEnvConfig() {
  return {
    apiUrl: getApiBaseUrl(),
    useMocks: getUseMocksEnabled(),
    debugMode: getDebugModeEnabled(),
    mode: getEnvValue('MODE') || 'test',
  };
}
