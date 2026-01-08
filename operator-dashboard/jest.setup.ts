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

// Mock react-syntax-highlighter to avoid ESM import issues
jest.mock('react-syntax-highlighter', () => {
  const React = require('react');
  interface MockHighlighterProps {
    children?: React.ReactNode;
    [key: string]: unknown;
  }
  return {
    Prism: ({ children, ...props }: MockHighlighterProps) => React.createElement('pre', props, children),
    Light: ({ children, ...props }: MockHighlighterProps) => React.createElement('pre', props, children),
  };
});

jest.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  vscDarkPlus: {},
}));
