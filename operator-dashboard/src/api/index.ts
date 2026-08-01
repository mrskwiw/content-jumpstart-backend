// API barrel exports
export { authApi } from './auth';
export { auditApi } from './audit';
export { clientsApi } from './clients';
export { costsApi } from './costs';
export { deliverablesApi } from './deliverables';
export { generatorApi } from './generator';
export { postsApi } from './posts';
export { projectsApi } from './projects';
export { reviewApi } from './review';
export { runsApi } from './runs';
export { settingsApi } from './settings';
export { storiesApi } from './stories';
export { teamsApi } from './teams';
export { usersApi } from './users';

// Research API and types
export { researchApi } from './research';
export type {
  ResearchTool,
  RunResearchInput,
  ResearchRunResult,
  ResearchResultHistory,
  ResearchHistoryResponse,
  ResearchResultListResponse,
  NextBundleSuggestion,
  PricingPreview,
  ToolStats,
  ResearchAnalytics,
} from './research';

// Default export (apiClient)
export { default as apiClient } from './client';
