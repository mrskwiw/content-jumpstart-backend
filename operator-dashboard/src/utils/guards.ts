const ABSOLUTE_OR_PROTOCOL = /^[a-zA-Z]+:\/\//;

export function isSafeRelativePath(path: string): boolean {
  if (!path) return false;
  if (path.startsWith('/') || path.startsWith('\\')) return false;
  if (path.includes('..')) return false;
  if (ABSOLUTE_OR_PROTOCOL.test(path)) return false;
  return true;
}
