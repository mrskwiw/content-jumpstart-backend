/**
 * Feature Registry — single source of truth for feature completeness.
 *
 * HOW TO USE:
 *   - Set status: 'complete' and add completedAt when a feature ships.
 *   - Incomplete features are automatically disabled in templates, research tools,
 *     and the early-access splash screen. No other changes needed.
 *
 * TO ENABLE A FEATURE:
 *   1. Change status: 'incomplete'  →  status: 'complete'
 *   2. Add completedAt: 'YYYY-MM-DD'
 *   That's it. The UI disabling and splash screen update automatically.
 */

export type FeatureStatus = 'complete' | 'incomplete';
export type FeatureCategory = 'app_feature' | 'template' | 'research_tool';

export interface RegistryFeature {
  id: string;
  name: string;
  description: string;
  category: FeatureCategory;
  status: FeatureStatus;
  completedAt?: string;  // ISO date — required when status === 'complete'
  templateId?: number;   // template category only
  toolId?: string;       // research_tool category only
}

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

export function isNewlyCompleted(feature: RegistryFeature): boolean {
  if (feature.status !== 'complete' || !feature.completedAt) return false;
  return Date.now() - new Date(feature.completedAt).getTime() < SEVEN_DAYS_MS;
}

export function isDisabled(feature: RegistryFeature): boolean {
  return feature.status === 'incomplete';
}

// ─── Registry ────────────────────────────────────────────────────────────────

export const FEATURE_REGISTRY: RegistryFeature[] = [

  // ── App Features ─────────────────────────────────────────────────────────
  {
    id: 'auth',
    name: 'Authentication & Login',
    description: 'Secure JWT login with role-based access control',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-03-01',
  },
  {
    id: 'dashboard',
    name: 'Dashboard & Overview',
    description: 'Project stats, quality scores, recent activity at a glance',
    category: 'app_feature',
    status: 'incomplete',
  },
  {
    id: 'client_management',
    name: 'Client Management',
    description: 'Create, edit, archive, and delete clients with full GDPR compliance',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-04-05',
  },
  {
    id: 'brief_import',
    name: 'Brief Import (PDF, DOCX, MD, TXT)',
    description: 'AI-powered field extraction from any brief format with confidence scores',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-04-22',
  },
  {
    id: 'project_management',
    name: 'Project Management',
    description: 'Full project lifecycle from brief to delivered content package',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-03-01',
  },
  {
    id: 'content_generation',
    name: 'Content Generation (30-Post Wizard)',
    description: 'Async parallel generation with 11 templates, quality validation, and auto-retry',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-04-01',
  },
  {
    id: 'quality_gate',
    name: 'Quality Gate & Post Review',
    description: '8 validators: hooks, CTAs, length, headlines, keywords, SEO, prompt injection',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-04-11',
  },
  {
    id: 'export_deliverables',
    name: 'Export & Deliverables',
    description: 'DOCX, PDF, and TXT export with embedded research results and formatted posts',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-04-11',
  },
  {
    id: 'credits',
    name: 'Credits System',
    description: 'Credit balance tracking; credits granted manually by admin',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-04-01',
  },
  {
    id: 'payments',
    name: 'Stripe Payments',
    description: 'Self-serve credit purchases via Stripe Checkout, webhooks, and billing portal',
    category: 'app_feature',
    status: 'incomplete',
  },
  {
    id: 'settings_integrations',
    name: 'Settings & Web Search Integrations',
    description: 'API key management for Brave, Tavily, SerpAPI; configurable web search provider',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-04-01',
  },
  {
    id: 'research_tool_library_page',
    name: 'Research Tool Library Page',
    description: 'Standalone page to browse, select, and run research tools outside the wizard',
    category: 'app_feature',
    status: 'incomplete',
  },
  {
    id: 'research_tools_in_wizard',
    name: 'Research Tools in Wizard',
    description: 'Research panel inside the content wizard — select and run tools as part of the workflow',
    category: 'app_feature',
    status: 'complete',
    completedAt: '2026-04-20',
  },
  {
    id: 'story_mining_feature',
    name: 'Story Mining & Story-Based Templates',
    description: 'Mine client stories to power Personal Story, Milestone, and Inside Look posts',
    category: 'app_feature',
    status: 'incomplete',
  },
  {
    id: 'analytics',
    name: 'Analytics Dashboard',
    description: 'Content performance metrics, engagement trends, platform analytics',
    category: 'app_feature',
    status: 'incomplete',
  },
  {
    id: 'content_calendar_view',
    name: 'Content Calendar',
    description: 'Visual scheduling and calendar view for planned and published content',
    category: 'app_feature',
    status: 'incomplete',
  },
  {
    id: 'team',
    name: 'Team Collaboration',
    description: 'Multi-user workspaces, role assignments, shared client access',
    category: 'app_feature',
    status: 'incomplete',
  },
  {
    id: 'notifications',
    name: 'Notifications',
    description: 'In-app and email notifications for completions, reviews, and deliveries',
    category: 'app_feature',
    status: 'incomplete',
  },
  {
    id: 'audit_trail',
    name: 'Audit Trail',
    description: 'Compliance logging for all content changes and client data modifications',
    category: 'app_feature',
    status: 'incomplete',
  },

  // ── Post Templates ────────────────────────────────────────────────────────
  { id: 'template_1',  templateId: 1,  name: 'Problem Recognition',  description: 'Hook problem → Validate feeling → Hint at solution',          category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_2',  templateId: 2,  name: 'Statistic + Insight',   description: 'Stat → What it means → Unexpected angle',                    category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_3',  templateId: 3,  name: 'Contrarian Take',       description: 'Challenge conventional wisdom → Show why → Give nuance',     category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_4',  templateId: 4,  name: 'What Changed',          description: 'Old way → What changed → New results',                       category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_5',  templateId: 5,  name: 'Question Post',         description: 'Thought-provoking question with context',                    category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_6',  templateId: 6,  name: 'Personal Story',        description: 'Vulnerable narrative with lesson learned — needs Story Mining', category: 'template', status: 'incomplete' },
  { id: 'template_7',  templateId: 7,  name: 'Myth Busting',          description: "Common belief → Why it's wrong → What is true",              category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_8',  templateId: 8,  name: 'Things I Got Wrong',    description: 'Past mistakes and lessons learned — needs Story Mining',     category: 'template', status: 'incomplete' },
  { id: 'template_9',  templateId: 9,  name: 'How-To',                description: 'Step-by-step actionable guide',                              category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_10', templateId: 10, name: 'Comparison',            description: 'Option A vs Option B breakdown',                             category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_11', templateId: 11, name: 'What I Learned From',   description: 'Lessons from books, events, or experiences',                 category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_12', templateId: 12, name: 'Inside Look',           description: 'Behind-the-scenes process reveal — needs Story Mining',      category: 'template', status: 'incomplete' },
  { id: 'template_13', templateId: 13, name: 'Future Thinking',       description: 'Predictions and forward-looking insights',                   category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_14', templateId: 14, name: 'Reader Q Response',     description: 'Answer common customer questions',                           category: 'template', status: 'complete',   completedAt: '2026-04-01' },
  { id: 'template_15', templateId: 15, name: 'Milestone',             description: 'Celebrate achievements and progress — needs Story Mining',   category: 'template', status: 'incomplete' },

  // ── Research Tools ────────────────────────────────────────────────────────
  { id: 'tool_voice_analysis',            toolId: 'voice_analysis',            name: 'Voice Analysis',            description: 'Analyze brand voice and tone from content samples',                  category: 'research_tool', status: 'incomplete' },
  { id: 'tool_brand_archetype',           toolId: 'brand_archetype',           name: 'Brand Archetype',           description: 'Identify the brand archetype that fits the client',                  category: 'research_tool', status: 'complete', completedAt: '2026-04-20' },
  { id: 'tool_seo_keyword_research',      toolId: 'seo_keyword_research',      name: 'SEO Keyword Research',      description: 'Target keywords with search volume and competition data',             category: 'research_tool', status: 'complete', completedAt: '2026-04-20' },
  { id: 'tool_audience_research',         toolId: 'audience_research',         name: 'Audience Research',         description: 'Deep-dive into ideal customer profiles and psychographics',           category: 'research_tool', status: 'complete', completedAt: '2026-04-20' },
  { id: 'tool_determine_competitors',     toolId: 'determine_competitors',     name: 'Determine Competitors',     description: "Identify top competitors from the client's market",                   category: 'research_tool', status: 'complete', completedAt: '2026-04-20' },
  { id: 'tool_competitive_analysis',      toolId: 'competitive_analysis',      name: 'Competitive Analysis',      description: 'Analyze competitor strengths, weaknesses, and content gaps',          category: 'research_tool', status: 'complete', completedAt: '2026-04-20' },
  { id: 'tool_content_gap_analysis',      toolId: 'content_gap_analysis',      name: 'Content Gap Analysis',      description: 'Identify content opportunities competitors are missing',              category: 'research_tool', status: 'complete', completedAt: '2026-04-20' },
  { id: 'tool_market_trends_research',    toolId: 'market_trends_research',    name: 'Market Trends Research',    description: 'Track industry trends and emerging opportunities',                    category: 'research_tool', status: 'incomplete' },
  { id: 'tool_icp_workshop',              toolId: 'icp_workshop',              name: 'ICP Workshop',              description: 'Define the ideal customer profile through structured discovery',      category: 'research_tool', status: 'complete', completedAt: '2026-04-20' },
  { id: 'tool_content_audit',             toolId: 'content_audit',             name: 'Content Audit',             description: 'Audit existing content for gaps, quality, and performance',           category: 'research_tool', status: 'complete', completedAt: '2026-04-20' },
  { id: 'tool_platform_strategy',         toolId: 'platform_strategy',         name: 'Platform Strategy',         description: 'Recommend the right platforms and content mix for the client',       category: 'research_tool', status: 'complete', completedAt: '2026-04-20' },
  { id: 'tool_content_calendar_strategy', toolId: 'content_calendar_strategy', name: 'Content Calendar Strategy', description: 'Build a data-driven 90-day content calendar with real event data',   category: 'research_tool', status: 'incomplete' },
  { id: 'tool_story_mining',              toolId: 'story_mining',              name: 'Story Mining',              description: 'Extract and categorize authentic client stories for storytelling templates', category: 'research_tool', status: 'incomplete' },
];

// ─── Derived lookups (computed once, referenced by UI components) ─────────────

/** Template IDs whose cards should be grayed out and non-interactive. */
export function getDisabledTemplateIds(): Set<number> {
  return new Set(
    FEATURE_REGISTRY
      .filter((f) => f.category === 'template' && f.status === 'incomplete' && f.templateId != null)
      .map((f) => f.templateId!)
  );
}

/** Research tool IDs whose cards should be grayed out and non-selectable. */
export function getDisabledToolIds(): Set<string> {
  return new Set(
    FEATURE_REGISTRY
      .filter((f) => f.category === 'research_tool' && f.status === 'incomplete' && f.toolId != null)
      .map((f) => f.toolId!)
  );
}

/** All complete features, newest first. Newly completed (< 7 days) sort to the top. */
export function getCompleteFeatures(category?: FeatureCategory): RegistryFeature[] {
  return FEATURE_REGISTRY
    .filter((f) => f.status === 'complete' && (!category || f.category === category))
    .sort((a, b) => {
      const aNew = isNewlyCompleted(a) ? 1 : 0;
      const bNew = isNewlyCompleted(b) ? 1 : 0;
      if (aNew !== bNew) return bNew - aNew;
      return (b.completedAt ?? '').localeCompare(a.completedAt ?? '');
    });
}

/** All incomplete features. */
export function getIncompleteFeatures(category?: FeatureCategory): RegistryFeature[] {
  return FEATURE_REGISTRY.filter(
    (f) => f.status === 'incomplete' && (!category || f.category === category)
  );
}
