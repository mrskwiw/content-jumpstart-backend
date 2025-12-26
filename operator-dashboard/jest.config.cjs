const { pathsToModuleNameMapper } = require('ts-jest');
const { compilerOptions } = require('./tsconfig.app.json');

module.exports = {
  preset: 'ts-jest/presets/default-esm',
  testEnvironment: 'jsdom',
  extensionsToTreatAsEsm: ['.ts', '.tsx'],
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', { tsconfig: 'tsconfig.jest.json', useESM: true }],
  },
  transformIgnorePatterns: [
    'node_modules/(?!(react-syntax-highlighter|refractor|hastscript|hast-.*|property-information|space-separated-tokens|comma-separated-tokens|web-namespaces)/)',
  ],
  moduleNameMapper: {
    ...pathsToModuleNameMapper(compilerOptions.paths || {}, { prefix: '<rootDir>/' }),
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    // Mock env module to avoid import.meta parse errors in Jest
    '^@/utils/env$': '<rootDir>/src/utils/__mocks__/env.ts',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testPathIgnorePatterns: ['/node_modules/', '/dist/'],
  globals: {
    'ts-jest': {
      useESM: true,
      tsconfig: 'tsconfig.jest.json',
    },
  },
};
