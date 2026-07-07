const { pathsToModuleNameMapper } = require('ts-jest');
const { compilerOptions } = require('./tsconfig.app.json');

module.exports = {
  preset: 'ts-jest/presets/default-esm',
  testEnvironment: 'jsdom',
  extensionsToTreatAsEsm: ['.ts', '.tsx'],
  transform: {
    '^.+\\.(ts|tsx)$': [
      'ts-jest',
      {
        tsconfig: 'tsconfig.jest.json',
        useESM: true,
        // Transpile-only: jest transpiles, tsc type-checks (separate CI step).
        isolatedModules: true,
        diagnostics: false,
      },
    ],
  },
  transformIgnorePatterns: [
    'node_modules/(?!(react-syntax-highlighter|refractor|hastscript|hast-.*|property-information|space-separated-tokens|comma-separated-tokens|web-namespaces)/)',
  ],
  moduleNameMapper: {
    ...pathsToModuleNameMapper(compilerOptions.paths || {}, { prefix: '<rootDir>/' }),
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    // Mock env module to avoid import.meta parse errors in Jest
    '^@/utils/env$': '<rootDir>/src/utils/__mocks__/env.ts',
    // Shim vitest imports to jest globals (some tests were authored for vitest)
    '^vitest$': '<rootDir>/src/__tests__/setup/vitest-shim.ts',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  // Only run actual test/spec files. The default testMatch also globs every
  // file under __tests__/ (setup helpers, fixtures, MSW mocks), which jest then
  // reports as failing suites for containing no tests.
  testMatch: ['**/?(*.)+(spec|test).[jt]s?(x)'],
  testPathIgnorePatterns: ['/node_modules/', '/dist/', '/tests/e2e/'],

  // Coverage configuration
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/__tests__/**',
    '!src/**/*.test.{ts,tsx}',
    '!src/**/*.spec.{ts,tsx}',
    '!src/main.tsx',
    '!src/vite-env.d.ts',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['html', 'text', 'json', 'lcov'],
  coverageThreshold: {
    global: {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90,
    },
  },
};
