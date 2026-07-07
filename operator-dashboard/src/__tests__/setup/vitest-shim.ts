/**
 * vitest -> jest compatibility shim.
 *
 * Some test files were authored against Vitest but this project runs Jest.
 * Rather than rewrite every file, `moduleNameMapper` maps `vitest` to this
 * shim so `import { vi, describe, it, ... } from 'vitest'` resolves to the
 * equivalent Jest globals. `vi` is aliased to Jest's `jest` object, whose API
 * (fn, spyOn, mock, clearAllMocks, useFakeTimers, ...) is compatible for the
 * usage in this suite.
 */
export const vi = jest;

export {
  describe,
  it,
  test,
  expect,
  beforeEach,
  afterEach,
  beforeAll,
  afterAll,
} from '@jest/globals';
