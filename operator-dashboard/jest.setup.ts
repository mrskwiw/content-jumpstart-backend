import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

// Polyfills for Jest environment
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as typeof global.TextDecoder;

// Shim Vite-style env for tests (consumed via import.meta.env fallback).
(globalThis as any).__ENV__ = {
  VITE_API_URL: 'http://localhost:8000',
  VITE_USE_MOCKS: 'false',
  VITE_DEBUG_MODE: 'false',
  MODE: 'test',
};
