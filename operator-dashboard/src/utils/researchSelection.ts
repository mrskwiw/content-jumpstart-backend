import type { ResearchTool } from '@/api/research';

/**
 * Return the selected tools that can actually run, in selection order.
 *
 * A tool that is (or became) `coming_soon` — by backend status or because the feature
 * registry disabled it — is dropped, so it can't linger in what is displayed, priced or
 * submitted after a refetch. The registry case matters most: the backend would still
 * run, and charge for, a tool only the registry disables. A tool missing from `tools`
 * (e.g. while the list loads) is kept; the backend validates it.
 *
 * @param selected - tool names in the order the user selected them
 * @param tools - the effective tool list (registry overrides already applied)
 */
export function runnableSelection(
  selected: readonly string[],
  tools: readonly ResearchTool[]
): string[] {
  const unavailable = new Set(tools.filter((t) => t.status === 'coming_soon').map((t) => t.name));
  return selected.filter((name) => !unavailable.has(name));
}
