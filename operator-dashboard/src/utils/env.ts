/**
 * Environment helpers for safely reading Vite-provided variables in browser and test contexts.
 * Falls back to a test shim (`globalThis.__ENV__`) when `import.meta.env` is unavailable.
 */
type EnvSource = Partial<{
  VITE_API_URL: string;
  VITE_USE_MOCKS: string;
  VITE_DEBUG_MODE: string;
  MODE: string;
}>;

const FALLBACK_API_URL = 'http://localhost:8000';

function resolveEnvSource(): EnvSource {
  try {
    // @ts-ignore Allow import.meta access in environments where module target may differ in tests.
    if (typeof import.meta !== 'undefined' && import.meta.env) {
      // @ts-ignore Allow import.meta access in environments where module target may differ in tests.
      return import.meta.env as EnvSource;
    }
  } catch {
    // Swallow reference errors when import.meta is unavailable (e.g., Jest without ESM env).
  }

  if ((globalThis as any).__ENV__) {
    return (globalThis as any).__ENV__ as EnvSource;
  }

  return {};
}

/**
 * Safely read a typed environment variable.
 * Returns undefined when missing to allow callers to layer defaults.
 */
function readEnvVar<K extends keyof EnvSource>(key: K): string | undefined {
  const envSource = resolveEnvSource();
  const value = envSource?.[key];
  return typeof value === 'string' ? value : undefined;
}

/**
 * Resolve the API base URL, validating format and normalizing trailing slashes.
 *
 * In production (when served from same origin as backend), uses relative URLs
 * to eliminate CORS issues. In development, defaults to localhost:8000.
 *
 * Set VITE_API_URL to empty string to use relative URLs (goes through Vite proxy).
 */
export function getApiBaseUrl(): string {
  const envSource = resolveEnvSource();
  const mode = readEnvVar('MODE') || 'development';

  // Check if VITE_API_URL key exists (even if empty)
  const hasApiUrl = 'VITE_API_URL' in envSource;
  const value = envSource.VITE_API_URL;

  // If explicitly set to empty string, use relative URLs (for Vite proxy)
  if (hasApiUrl && value === '') {
    console.log('VITE_API_URL set to empty string; using relative URLs (Vite proxy)');
    return '';
  }

  // If not set at all, use mode-based fallback
  if (!hasApiUrl || !value) {
    // Production: use relative URLs (same origin as backend)
    // Development: use localhost
    if (mode === 'production') {
      console.log('VITE_API_URL not set in production; using relative URLs (same origin)');
      return '';  // Relative URLs eliminate CORS
    } else {
      console.warn('VITE_API_URL not set; using default http://localhost:8000');
      return FALLBACK_API_URL;
    }
  }

  // Value is set and non-empty, validate and normalize
  try {
    const normalized = new URL(value).toString();
    return normalized.endsWith('/') ? normalized.slice(0, -1) : normalized;
  } catch (error) {
    console.warn('Invalid VITE_API_URL provided; using default http://localhost:8000', error);
    return FALLBACK_API_URL;
  }
}

/**
 * Determine whether mock APIs should be used.
 */
export function getUseMocksEnabled(): boolean {
  const raw = readEnvVar('VITE_USE_MOCKS');
  return raw === 'true';
}

/**
 * Determine whether debug mode is enabled.
 */
export function getDebugModeEnabled(): boolean {
  const raw = readEnvVar('VITE_DEBUG_MODE');
  return raw === 'true';
}

/**
 * Provide a snapshot of key environment flags for UI display.
 */
export function getEnvConfig() {
  return {
    apiUrl: getApiBaseUrl(),
    useMocks: getUseMocksEnabled(),
    debugMode: getDebugModeEnabled(),
    mode: readEnvVar('MODE') || 'development',
  };
}
