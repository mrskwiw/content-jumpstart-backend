import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

// Polyfills for Jest environment
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as typeof global.TextDecoder;

// Shim Vite-style env for tests (consumed via import.meta.env fallback).
interface TestEnv {
  VITE_API_URL: string;
  VITE_USE_MOCKS: string;
  VITE_DEBUG_MODE: string;
  MODE: string;
}

(globalThis as typeof globalThis & { __ENV__: TestEnv }).__ENV__ = {
  VITE_API_URL: 'http://localhost:8000',
  VITE_USE_MOCKS: 'false',
  VITE_DEBUG_MODE: 'false',
  MODE: 'test',
};

// Mock the env module to avoid import.meta parse errors
jest.mock('@/utils/env');

// jsdom has no matchMedia; ThemeProvider (mounted via AllTheProviders) calls it.
// Default to light theme (matches: false) so theme-aware components render deterministically.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated, retained for older consumers
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }),
});

// Mock react-syntax-highlighter to avoid ESM import issues. PreviewTab imports the
// PrismLight build and calls registerLanguage(), plus a deep per-language ESM module
// that jest can't parse — stub all of them with a plain <pre> renderer.
jest.mock('react-syntax-highlighter', () => {
  // jest.mock factories are hoisted above the file's imports, so a top-level `import`
  // can't be referenced here — require() is the supported pattern inside a factory.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const React = require('react');
  interface MockHighlighterProps {
    children?: React.ReactNode;
    [key: string]: unknown;
  }
  const Highlighter = ({ children, ...props }: MockHighlighterProps) =>
    React.createElement('pre', props, children);
  Highlighter.registerLanguage = () => {};
  return {
    Prism: Highlighter,
    Light: Highlighter,
    PrismLight: Highlighter,
    PrismAsyncLight: Highlighter,
    default: Highlighter,
  };
});

jest.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  vscDarkPlus: {},
  vs: {},
}));

// Deep per-language import used by PreviewTab; the real file is untransformed ESM.
jest.mock(
  'react-syntax-highlighter/dist/esm/languages/prism/markdown',
  () => ({ __esModule: true, default: {} }),
  { virtual: true }
);

// ==================== MSW Server Setup ====================
// Import MSW server for API mocking in tests
// import { server } from './__tests__/integration/mocks/server';

// Start MSW server before all tests
// beforeAll(() => {
//   server.listen({
//     onUnhandledRequest: 'error',
//   });
// });

// Reset handlers after each test to ensure test isolation
afterEach(() => {
    // server.resetHandlers();
});

// Clean up MSW server after all tests
afterAll(() => {
    // server.close();
});
