import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, Button, Input, Textarea } from '@/components/ui';
import { AlertCircle, Plus, X, FileText, CheckCircle2, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { ContentAuditCollector } from './ContentAuditCollector';
import { researchApi } from '@/api/research';
import type { Client } from '@/types/domain';

interface ResearchDataCollectionPanelProps {
  selectedTools: string[];
  clientData: Client | null;
  projectId?: string;
  onContinue: (collectedData: Record<string, unknown>) => void;
  onBack: () => void;
}

// Client field → Tool input field mappings
const CLIENT_TO_TOOL_FIELD_MAPPINGS: Record<string, Record<string, string>> = {
  voice_analysis: {
    brandPersonality: 'brand_personality',
    toneToAvoid: 'tone_to_avoid',
  },
  seo_keyword_research: {
    keywords: 'main_topics',
    location: 'location',
  },
  determine_competitors: {
    industry: 'industry',
    location: 'location'
  },
  competitive_analysis: {
    competitors: 'competitors',
    toneToAvoid: 'tone_to_avoid',
    measurableResults: 'measurable_results',
    brandPersonality: 'brand_personality',
  },
  market_trends_research: {
    industry: 'industry',
    location: 'location',
    keywords: 'focus_areas',
    customerPainPoints: 'customer_pain_points',
    misconceptions: 'misconceptions',
  },
  platform_strategy: {
    platforms: 'current_platforms',
    mainProblemSolved: 'content_goals',
    tonePreference: 'tone_preference',
    brandPersonality: 'brand_personality',
    postingFrequency: 'posting_frequency',
    dataUsage: 'data_usage',
  },
  content_calendar_strategy: {
    platforms: 'primary_platforms',
    mainProblemSolved: 'content_goals',
    postingFrequency: 'posting_frequency',
    mainCta: 'main_cta',
  },
  content_gap_analysis: {
    keywords: 'current_content_topics',
    misconceptions: 'known_misconceptions',
    customerQuestions: 'customer_questions',
    customerPainPoints: 'customer_pain_points',
  },
  story_mining: {
    stories: 'existing_stories',
    measurableResults: 'measurable_results',
    founderName: 'business_name',
  },
  icp_workshop: {
    idealCustomer: 'existing_customer_data',
    stories: 'stories',
    measurableResults: 'measurable_results',
    customerPainPoints: 'customer_pain_points',
  },
  audience_research: {
    customerPainPoints: 'customer_pain_points',
    customerQuestions: 'customer_questions',
  },
  brand_archetype: {
    brandPersonality: 'brand_personality',
    toneToAvoid: 'tone_to_avoid',
  },
  business_report: {
    name: 'company_name',
    location: 'location'
  }
};

// Tool data requirements mapping
const TOOL_DATA_REQUIREMENTS: Record<string, {
  fields: Array<{
    key: string;
    label: string;
    type: 'textarea' | 'text-list' | 'content-list' | 'text';
    required: boolean;
    min?: number;
    max?: number;
    placeholder?: string;
    helperText?: string;
  }>;
}> = {
  voice_analysis: {
    fields: [{
      key: 'content_samples',
      label: 'Content Samples',
      type: 'content-list',
      required: true,
      min: 5,
      max: 30,
      placeholder: 'Paste a sample of client\'s writing (blog post, LinkedIn post, email, etc.)',
      helperText: 'Provide 5-30 samples of the client\'s existing writing (minimum 50 characters each). More samples = better voice analysis.'
    }, {
      key: 'brand_personality',
      label: 'Declared Personality Traits (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., approachable, direct, data-driven',
      helperText: '✨ Auto-populates from client profile. Used to validate whether the observed voice matches declared brand direction — highlights alignment gaps.'
    }, {
      key: 'tone_to_avoid',
      label: 'Tone to Avoid (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., corporate jargon, overly salesy, condescending',
      helperText: '✨ Auto-populates from client profile. If this tone is detected in the content samples it will be flagged in the analysis.'
    }]
  },
  seo_keyword_research: {
    fields: [{
      key: 'main_topics',
      label: 'Seed Keywords / Main Topics (Optional — Auto-Populated)',
      type: 'text-list',
      required: false,
      min: 0,
      placeholder: 'Leave empty to auto-generate, or override with custom topics',
      helperText: '✨ Auto-populates from client profile keywords if set. Or manually add 1-10 custom topics. If 5+ keywords provided they are used directly as seed topics.'
    }, {
      key: 'location',
      label: 'Geographic Market (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., United States, New York, Global',
      helperText: '✨ Auto-populates from client profile location. Focuses keyword research on geo-specific search volume and local competition.'
    }]
  },
  determine_competitors: {
    fields: [{
      key: 'industry',
      label: 'Industry (Optional - Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'Leave empty to use client profile industry',
      helperText: '✨ Auto-populates from your client profile. Override if needed (e.g., "B2B SaaS", "Healthcare").'
    }, {
      key: 'location',
      label: 'Geographic Market (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., United States, Global, EMEA',
      helperText: '✨ Auto-populates from your client profile location if set. Override to focus on a different geographic market.'
    }]
  },
  competitive_analysis: {
    fields: [{
      key: 'competitors',
      label: 'Competitor Names (Recommended — Auto-Populated)',
      type: 'text-list',
      required: false,
      min: 1,
      max: 5,
      placeholder: 'Leave empty to use competitors from client profile or Determine Competitors results',
      helperText: '⚠️ Required in practice — auto-populates from Determine Competitors results or client profile. If neither has data this tool will fail. Run Determine Competitors first, or add 1–5 names here.'
    }, {
      key: 'brand_personality',
      label: 'Brand Personality Traits (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., Bold, Empathetic, No-nonsense...',
      helperText: '✨ Auto-populates from client profile. Used to anchor positioning recommendations to the client\'s declared brand identity.'
    }, {
      key: 'tone_to_avoid',
      label: 'Tone to Avoid (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., Overly formal, corporate jargon, aggressive...',
      helperText: '✨ Auto-populates from client profile. Prevents positioning recommendations from suggesting messaging that conflicts with the client\'s stated tone boundaries.'
    }, {
      key: 'measurable_results',
      label: 'Measurable Results / Proof Points (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., 3x revenue increase, 40% churn reduction...',
      helperText: '✨ Auto-populates from client profile. Concrete proof points are used as differentiator evidence in the positioning statement.'
    }]
  },
  content_gap_analysis: {
    fields: [{
      key: 'current_content_topics',
      label: 'Current Content Topics (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      min: 0,
      placeholder: 'Leave empty to auto-populate from client keywords or SEO research results...',
      helperText: '✨ Auto-populates from client profile keywords, then from SEO keyword research results if available. Override to describe your current topics manually (minimum 10 characters if provided).'
    }, {
      key: 'known_misconceptions',
      label: 'Known Industry Misconceptions (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'e.g., "People think we\'re only for enterprise, but we serve SMBs too"',
      helperText: '✨ Auto-populates from client profile. Misconceptions the client wants to correct make high-value gap content — they\'re underserved topics their audience is confused about.'
    }, {
      key: 'customer_questions',
      label: 'Top Customer Questions (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'e.g., "How long does onboarding take? What does it cost?"',
      helperText: '✨ Auto-populates from client profile. Questions customers already ask ARE the content gaps — they map directly to missing educational content.'
    }, {
      key: 'customer_pain_points',
      label: 'Customer Pain Points (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'e.g., "Wasting hours on manual reporting, losing deals to faster competitors"',
      helperText: '✨ Auto-populates from client profile. Pain-point content is consistently underserved — these identify gaps with guaranteed audience demand.'
    }]
  },
  content_audit: {
    fields: [{
      key: 'content_inventory',
      label: 'Content to Audit',
      type: 'content-list',
      required: true,
      min: 1,
      max: 100,
      placeholder: 'URLs will be auto-analyzed...',
      helperText: 'Paste URLs for quick import, or manually add content without URLs. Tool analyzes performance, identifies top/underperformers, and recommends updates, refreshes, or archives.'
    }, {
      key: 'audit_focus_areas',
      label: 'Audit Focus Areas (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'Leave empty, or enter topics to focus the audit on...',
      helperText: '✨ Auto-populates from Content Gap Analysis results if available. Focuses the audit on known gap areas rather than auditing everything.'
    }]
  },
  market_trends_research: {
    fields: [{
      key: 'industry',
      label: 'Industry (Optional - Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'Leave empty to use client profile industry',
      helperText: '✨ Auto-populates from your client profile if left empty. Override if researching a different industry.'
    }, {
      key: 'focus_areas',
      label: 'Focus Areas (Optional — Auto-Populated)',
      type: 'text-list',
      required: false,
      placeholder: 'Leave empty to auto-populate from client keywords or SEO research results...',
      helperText: '✨ Auto-populates from client profile keywords, then from SEO keyword research results if available. Add or remove topics to focus the trend research.'
    }, {
      key: 'location',
      label: 'Location (Optional — Auto-Populated, Enables Review Analysis)',
      type: 'text',
      required: false,
      placeholder: 'e.g., San Francisco, CA',
      helperText: '✨ Auto-populates from client profile. When set, also pulls Google Maps reviews from industry businesses in your market for real customer insights.'
    }, {
      key: 'customer_pain_points',
      label: 'Customer Pain Points (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'e.g., Wasting hours on manual reporting, losing deals to faster competitors...',
      helperText: '✨ Auto-populates from client profile. Trends that address confirmed pain points are flagged as higher relevance — guaranteed audience demand.'
    }, {
      key: 'misconceptions',
      label: 'Industry Misconceptions (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'e.g., "People think this only works for enterprise, but SMBs get better ROI"',
      helperText: '✨ Auto-populates from client profile. Misconception-debunking content outperforms generic thought leadership — these seed a high-value trend opportunity category.'
    }]
  },
  platform_strategy: {
    fields: [{
      key: 'current_platforms',
      label: 'Current Platforms (Optional)',
      type: 'text-list',
      required: false,
      placeholder: 'e.g., LinkedIn, Twitter, Blog',
      helperText: 'Platforms you currently use for content distribution.'
    }, {
      key: 'content_goals',
      label: 'Content Goals (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., awareness and leads, thought leadership, customer education',
      helperText: '✨ Auto-populates from the main problem your client solves. Override with specific content objectives.'
    }, {
      key: 'tone_preference',
      label: 'Tone Preference (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., professional, conversational, authoritative',
      helperText: '✨ Auto-populates from client profile. Constrains platform fit — e.g., witty/casual tone favors Twitter over LinkedIn.'
    }, {
      key: 'brand_personality',
      label: 'Brand Personality Traits (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., approachable, direct, data-driven',
      helperText: '✨ Auto-populates from client profile. Used to match platform culture to brand voice.'
    }, {
      key: 'posting_frequency',
      label: 'Posting Frequency (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., 3x per week, daily',
      helperText: '✨ Auto-populates from client profile. Factors into how many primary platforms are realistic given available bandwidth.'
    }, {
      key: 'data_usage',
      label: 'Data & Statistics Usage (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., heavy, moderate, minimal',
      helperText: '✨ Auto-populates from client profile. Heavy data usage favors LinkedIn and blog over Twitter/Instagram.'
    }]
  },
  content_calendar_strategy: {
    fields: [{
      key: 'content_goals',
      label: 'Content Goals (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., brand awareness, lead generation, thought leadership',
      helperText: '✨ Auto-populates from the main problem your client solves. Override with specific calendar objectives (10-1000 characters).'
    }, {
      key: 'primary_platforms',
      label: 'Primary Platforms (Optional)',
      type: 'text-list',
      required: false,
      placeholder: 'e.g., LinkedIn, Twitter, Blog',
      helperText: 'Platforms where you plan to publish content. Leave empty to get recommendations.'
    }, {
      key: 'posting_frequency',
      label: 'Posting Frequency (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., 3x per week, daily, twice weekly',
      helperText: '✨ Auto-populates from client profile if set. Guides platform schedule recommendations.'
    }, {
      key: 'main_cta',
      label: 'Primary Call to Action (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., Book a discovery call, Download free guide',
      helperText: '✨ Auto-populates from client profile. Used to align weekly CTA focus across the calendar.'
    }]
  },
  audience_research: {
    fields: [{
      key: 'customer_pain_points',
      label: 'Customer Pain Points (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'e.g., Wasting hours on manual reporting, losing deals to faster competitors...',
      helperText: '✨ Auto-populates from client profile. Treated as confirmed intelligence — seeds the pain point analysis so the AI builds from real problems rather than inferred ones.'
    }, {
      key: 'customer_questions',
      label: 'Top Customer Questions (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'e.g., How long does onboarding take? What does it cost?',
      helperText: '✨ Auto-populates from client profile. Real questions are treated as confirmed pain signals — surfaced directly in the pain points and decision factors output.'
    }]
  },
  icp_workshop: {
    fields: [{
      key: 'existing_customer_data',
      label: 'Existing Customer Data (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'Leave empty to auto-populate from client ideal customer profile and audience research results...',
      helperText: '✨ Auto-populates from client ideal customer description, then enriched with audience research pain points and psychographics if available. Add more detail or override entirely.'
    }, {
      key: 'stories',
      label: 'Customer Wins / Stories (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'Leave empty to use stories from client profile...',
      helperText: '✨ Auto-populates from client profile stories. Used as ICP evidence — who the client has already successfully helped reveals who the ideal customer is.'
    }, {
      key: 'measurable_results',
      label: 'Measurable Results / Success Benchmarks (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., 40% cost reduction, 3x pipeline in 90 days',
      helperText: '✨ Auto-populates from client profile. Defines what success looks like in quantifiable terms — grounds ICP criteria in real outcomes.'
    }, {
      key: 'customer_pain_points',
      label: 'Known Customer Pain Points (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'Leave empty to use pain points from client profile...',
      helperText: '✨ Auto-populates from client profile. Seeds the ICP pain-point discovery prompts with known problems, improving specificity.'
    }]
  },
  story_mining: {
    fields: [{
      key: 'customer_context',
      label: 'Customer Context',
      type: 'textarea',
      required: true,
      min: 30,
      placeholder: 'Describe the customer success story context: who the customer is, their challenges, how they used your product/service, results achieved...',
      helperText: 'Provide context about the customer story you want to mine (30-2000 characters). Include customer background, challenges faced, and outcomes.'
    }, {
      key: 'interview_notes',
      label: 'Interview Notes (Optional)',
      type: 'textarea',
      required: false,
      placeholder: 'Paste interview transcript, customer quotes, or detailed notes from conversations...',
      helperText: 'Optional. Add detailed interview notes or customer quotes to enrich the story (0-10000 characters).'
    }, {
      key: 'existing_stories',
      label: 'Existing Client Stories (Optional — Auto-Populated)',
      type: 'textarea',
      required: false,
      placeholder: 'Leave empty to use stories from client profile, or paste additional story material...',
      helperText: '✨ Auto-populates from client profile stories. Used to seed the analysis with narratives the client has already shared.'
    }, {
      key: 'measurable_results',
      label: 'Measurable Results / Success Benchmarks (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., 3x revenue increase in 6 months, 40% churn reduction...',
      helperText: '✨ Auto-populates from client profile. Frames the results-gathering stage with concrete benchmarks so the AI probes for matching outcomes.'
    }, {
      key: 'business_name',
      label: 'Business Name / Story Attribution (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., Jane Smith / Acme Co...',
      helperText: '✨ Auto-populates from client founder name. Used to attribute the customer story to the right person or brand.'
    }]
  },
  brand_archetype: {
    fields: [{
      key: 'brand_personality',
      label: 'Brand Personality Traits (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., Bold, Empathetic, No-nonsense, Approachable...',
      helperText: '✨ Auto-populates from client profile. Declared personality traits are weighted heavily when scoring archetype fit — improves accuracy.'
    }, {
      key: 'tone_to_avoid',
      label: 'Tone to Avoid (Optional — Auto-Populated)',
      type: 'text',
      required: false,
      placeholder: 'e.g., Overly formal, aggressive, corporate jargon...',
      helperText: '✨ Auto-populates from client profile. Archetypes that embody the avoided tone receive lower scores, steering recommendations away from mismatched identities.'
    }]
  },
  business_report: {
    fields: [{
      key: 'company_name',
      label: 'Company Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., Acme Coffee Co',
      helperText: 'Name of the company to analyze (2-200 characters).'
    }, {
      key: 'location',
      label: 'Location',
      type: 'text',
      required: true,
      placeholder: 'e.g., Seattle, WA',
      helperText: 'Location of the company - city and state or city and country (2-200 characters).'
    }, {
      key: 'max_web_results',
      label: 'Max Web Results (Optional)',
      type: 'text',
      required: false,
      placeholder: '10',
      helperText: 'Maximum number of web search results to analyze (1-50, default: 10).'
    }, {
      key: 'max_reviews',
      label: 'Max Reviews (Optional)',
      type: 'text',
      required: false,
      placeholder: '50',
      helperText: 'Maximum number of Google Maps reviews to analyze (1-200, default: 50).'
    }]
  }
};

export function ResearchDataCollectionPanel({
  selectedTools,
  clientData,
  projectId,
  onContinue,
  onBack
}: ResearchDataCollectionPanelProps) {
  const [collectedData, setCollectedData] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [autoFilledFields, setAutoFilledFields] = useState<Set<string>>(new Set());

  // Fetch prior research results for cross-tool auto-populate
  const { data: priorResearch } = useQuery({
    queryKey: ['research-results', projectId],
    queryFn: () => researchApi.getProjectResearchResults(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  // Auto-populate fields from client data and prior research results
  useEffect(() => {
    if (!clientData) return;

    const updates: Record<string, any> = {};
    const autoFilled = new Set<string>();

    // Helper: set a field only if not already populated by the user
    const maybeSet = (targetField: string, value: unknown) => {
      if (collectedData[targetField]) return;
      if (value === undefined || value === null || value === '') return;
      if (Array.isArray(value) && value.length === 0) return;
      updates[targetField] = value;
      autoFilled.add(targetField);
    };

    // 1. Client profile → tool field mappings
    selectedTools.forEach(toolId => {
      const mapping = CLIENT_TO_TOOL_FIELD_MAPPINGS[toolId];
      if (!mapping) return;

      Object.entries(mapping).forEach(([sourceField, targetField]) => {
        const value = clientData[sourceField as keyof Client];
        if (value === undefined || value === null || value === '') return;

        if (Array.isArray(value)) {
          const allFields = TOOL_DATA_REQUIREMENTS[toolId]?.fields || [];
          const fieldDef = allFields.find(f => f.key === targetField);
          const capped = fieldDef?.max ? value.slice(0, fieldDef.max) : value;
          maybeSet(targetField, capped.join(', '));
        } else {
          maybeSet(targetField, value);
        }
      });
    });

    // 2. Cross-tool populate from prior research results
    const completedResults = priorResearch?.results?.filter(r => r.status === 'completed') ?? [];

    if (selectedTools.includes('competitive_analysis')) {
      // Populate competitors from determine_competitors results if available
      const dcResult = completedResults.find(r => r.toolName === 'determine_competitors');
      if (dcResult?.data) {
        const primary = (dcResult.data as any).primary_competitors ?? [];
        const names: string[] = primary
          .map((c: any) => (typeof c === 'string' ? c : c?.name))
          .filter(Boolean)
          .slice(0, 5);
        if (names.length > 0) maybeSet('competitors', names.join(', '));
      }
    }

    if (selectedTools.includes('market_trends_research')) {
      // Populate focus_areas from seo_keyword_research if available
      const seoResult = completedResults.find(r => r.toolName === 'seo_keyword_research');
      if (seoResult?.data) {
        const keywords = (seoResult.data as any).primary_keywords ?? (seoResult.data as any).keywords ?? [];
        const topKeywords: string[] = keywords
          .slice(0, 8)
          .map((k: any) => (typeof k === 'string' ? k : k?.keyword))
          .filter(Boolean);
        if (topKeywords.length > 0) maybeSet('focus_areas', topKeywords.join(', '));
      }
    }

    if (selectedTools.includes('content_gap_analysis')) {
      // Populate current_content_topics from seo_keyword_research if available
      const seoResult = completedResults.find(r => r.toolName === 'seo_keyword_research');
      if (seoResult?.data) {
        const keywords = (seoResult.data as any).primary_keywords ?? (seoResult.data as any).keywords ?? [];
        const topKeywords: string[] = keywords
          .slice(0, 10)
          .map((k: any) => (typeof k === 'string' ? k : k?.keyword))
          .filter(Boolean);
        if (topKeywords.length > 0) maybeSet('current_content_topics', topKeywords.join(', '));
      }
    }

    if (selectedTools.includes('content_audit')) {
      // Populate audit_focus_areas from content_gap_analysis results if available
      const gapResult = completedResults.find(r => r.toolName === 'content_gap_analysis');
      if (gapResult?.data) {
        const data = gapResult.data as any;
        const gaps: string[] = (data.content_gaps ?? data.gaps ?? [])
          .slice(0, 5)
          .map((g: any) => (typeof g === 'string' ? g : g?.topic ?? g?.title))
          .filter(Boolean);
        if (gaps.length > 0) maybeSet('audit_focus_areas', gaps.join(', '));
      }
    }

    // 4A — Feed voice_analysis → platform_strategy
    if (selectedTools.includes('platform_strategy')) {
      const voiceResult = completedResults.find(r => r.toolName === 'voice_analysis');
      if (voiceResult?.data) {
        const data = voiceResult.data as any;
        const voiceGuide = data.brand_voice_guide ?? data.voice_characteristics ?? '';
        const primaryTone = data.primary_tone ?? data.dominant_tone ?? data.tone ?? '';
        const voiceContext = voiceGuide || (primaryTone ? `Tone: ${primaryTone}` : '');
        if (voiceContext) maybeSet('tone_preference', voiceContext);
      }
    }

    // 4B — Feed brand_archetype → content_calendar_strategy
    if (selectedTools.includes('content_calendar_strategy')) {
      const archetypeResult = completedResults.find(r => r.toolName === 'brand_archetype');
      if (archetypeResult?.data) {
        const data = archetypeResult.data as any;
        const primaryArchetype = data.primary_archetype ?? data.archetype ?? '';
        const messaging = data.messaging_framework ?? data.content_recommendations ?? data.brand_voice ?? '';
        if (primaryArchetype) {
          const archetypeGoals = messaging
            ? `${primaryArchetype} archetype — ${messaging}`
            : `${primaryArchetype} archetype content strategy`;
          maybeSet('content_goals', archetypeGoals);
        }
      }
    }

    // 4C — Feed audience_research → icp_workshop
    if (selectedTools.includes('icp_workshop')) {
      const audienceResult = completedResults.find(r => r.toolName === 'audience_research');
      if (audienceResult?.data) {
        const data = audienceResult.data as any;
        const painPoints: string[] = (data.pain_points ?? data.behaviors_pain?.pain_points ?? []).slice(0, 5);
        const infoSources: string[] = (data.information_sources ?? data.behaviors_pain?.information_sources ?? []).slice(0, 5);
        const psycho = typeof data.psychographics === 'string' ? data.psychographics : (data.demographics_psycho?.psychographics ?? '');

        const parts: string[] = [];
        if (painPoints.length > 0) parts.push(`Known Pain Points: ${painPoints.join('; ')}`);
        if (infoSources.length > 0) parts.push(`Where They Get Info: ${infoSources.join(', ')}`);
        if (psycho) parts.push(`Psychographics: ${psycho}`);

        if (parts.length > 0) maybeSet('existing_customer_data', parts.join('\n'));
      }
    }

    // 4D — Feed seo_keyword_research → platform_strategy (content_goals)
    if (selectedTools.includes('platform_strategy')) {
      const seoResult = completedResults.find(r => r.toolName === 'seo_keyword_research');
      if (seoResult?.data) {
        const data = seoResult.data as any;
        const keywords: string[] = (data.primary_keywords ?? data.keywords ?? [])
          .slice(0, 5)
          .map((k: any) => (typeof k === 'string' ? k : k?.keyword))
          .filter(Boolean);
        if (keywords.length > 0) maybeSet('content_goals', `Content topics: ${keywords.join(', ')}`);
      }
    }

    if (Object.keys(updates).length > 0) {
      setCollectedData(prev => ({ ...prev, ...updates }));
      setAutoFilledFields(autoFilled);
    }
  }, [clientData, selectedTools, priorResearch]);

  // Get all required fields for selected tools
  const requiredFields = selectedTools.flatMap(tool =>
    TOOL_DATA_REQUIREMENTS[tool]?.fields || []
  );

  const handleFieldChange = (fieldKey: string, value: unknown) => {
    setCollectedData(prev => ({ ...prev, [fieldKey]: value }));
    setErrors(prev => ({ ...prev, [fieldKey]: '' }));

    // Remove auto-fill indicator when user edits
    setAutoFilledFields(prev => {
      const next = new Set(prev);
      next.delete(fieldKey);
      return next;
    });
  };

  const handleTextListChange = (key: string, value: string) => {
    // Store the raw string value directly without processing
    // Processing will happen during validation/submission
    handleFieldChange(key, value);
  };

  const handleContentListChange = (key: string, index: number, value: string) => {
    const current = collectedData[key];
    const currentList = Array.isArray(current) ? current : [];
    const newList = [...currentList];
    newList[index] = value;
    setCollectedData(prev => ({ ...prev, [key]: newList }));
    setErrors(prev => ({ ...prev, [key]: '' }));
  };

  const handleAddContentSample = (key: string) => {
    const current = collectedData[key];
    const currentList = Array.isArray(current) ? current : [];
    setCollectedData(prev => ({ ...prev, [key]: [...currentList, ''] }));
  };

  const handleRemoveContentSample = (key: string, index: number) => {
    const current = collectedData[key];
    const currentList = Array.isArray(current) ? current : [];
    const newList = currentList.filter((_, i: number) => i !== index);
    setCollectedData(prev => ({ ...prev, [key]: newList }));
  };

  const validateData = (): boolean => {
    const newErrors: Record<string, string> = {};
    let isValid = true;

    requiredFields.forEach(field => {
      const value = collectedData[field.key];

      if (field.required) {
        // For text-list fields, convert string to array for validation
        let processedValue = value;
        if (field.type === 'text-list' && typeof value === 'string') {
          processedValue = value.split(',').map(item => item.trim()).filter(item => item.length > 0);
        }

        if (!processedValue || (Array.isArray(processedValue) && processedValue.length === 0) || (typeof processedValue === 'string' && processedValue.trim().length === 0)) {
          newErrors[field.key] = `${field.label} is required`;
          isValid = false;
          return;
        }

        if (Array.isArray(processedValue)) {
          // Check minimum count
          if (field.min && processedValue.length < field.min) {
            newErrors[field.key] = `Minimum ${field.min} items required`;
            isValid = false;
            return;
          }

          // Check maximum count
          if (field.max && processedValue.length > field.max) {
            newErrors[field.key] = `Maximum ${field.max} items allowed`;
            isValid = false;
            return;
          }

          // For content samples, check each item length
          if (field.key === 'content_samples') {
            const validSamples = processedValue.filter((sample: string) => sample.length >= 50);
            if (validSamples.length < (field.min || 0)) {
              newErrors[field.key] = `At least ${field.min} samples must be 50+ characters`;
              isValid = false;
              return;
            }
          }
        } else if (typeof processedValue === 'string') {
          // Special validation for content_gap_analysis topics (optional field)
          if (field.key === 'current_content_topics') {
            // Field is optional - skip validation if empty (will auto-generate)
            // If provided, enforce minimum length
            if (processedValue.length > 0 && processedValue.length < 10) {
              newErrors[field.key] = 'Please enter at least 10 characters or leave empty to auto-generate';
              isValid = false;
              return;
            }
          } else {
            // Check minimum length for other textarea fields
            if (field.min && processedValue.length < field.min) {
              newErrors[field.key] = `Minimum ${field.min} characters required`;
              isValid = false;
              return;
            }
          }
        }
      }
    });

    setErrors(newErrors);
    return isValid;
  };

  const handleContinue = () => {
    if (validateData()) {
      // Process text-list fields: convert strings to arrays
      const processedData = { ...collectedData };
      requiredFields.forEach(field => {
        const value = processedData[field.key];
        if (field.type === 'text-list') {
          if (typeof value === 'string') {
            // Convert comma-separated string to array (Bug #38 fix)
            let items = value
              .split(',')
              .map((item: string) => item.trim())
              .filter((item: string) => item.length > 0);
            // Cap to field max to prevent backend validation errors (Bug #99 fix)
            if (field.max && items.length > field.max) {
              items = items.slice(0, field.max);
            }
            processedData[field.key] = items;
          } else if (!value || value === '') {
            // Convert null/undefined/empty to empty array (Bug #38 fix)
            processedData[field.key] = [];
          } else if (Array.isArray(value) && field.max && (value as unknown[]).length > field.max) {
            // Cap array values to field max (Bug #99 fix)
            processedData[field.key] = (value as unknown[]).slice(0, field.max);
          }
        }
      });
      onContinue(processedData);
    }
  };

  // Collapsed/expanded state for the client context preview
  const [contextExpanded, setContextExpanded] = useState(false);

  // Client context preview — shows business_description + target_audience the tools will silently consume
  const ClientContextPreview = () => {
    if (!clientData) return null;

    const businessDesc = clientData.businessDescription ?? '';
    const targetAudience = clientData.idealCustomer ?? '';

    if (!businessDesc && !targetAudience) return null;

    const PREVIEW_LEN = 200;

    const truncate = (text: string) =>
      text.length > PREVIEW_LEN ? text.slice(0, PREVIEW_LEN).trimEnd() + '…' : text;

    return (
      <div className="mb-6 rounded-lg border border-neutral-200 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800/50">
        <button
          type="button"
          onClick={() => setContextExpanded(prev => !prev)}
          className="flex w-full items-center justify-between px-4 py-3 text-left"
        >
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Client context the tools will use
          </span>
          <span className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400">
            {contextExpanded ? (
              <>Hide <ChevronUp className="h-3.5 w-3.5" /></>
            ) : (
              <>Show <ChevronDown className="h-3.5 w-3.5" /></>
            )}
          </span>
        </button>

        {contextExpanded && (
          <div className="border-t border-neutral-200 px-4 py-3 dark:border-neutral-700 space-y-3">
            {businessDesc && (
              <div>
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
                  Business Description
                </p>
                <p className="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
                  {truncate(businessDesc)}
                </p>
              </div>
            )}
            {targetAudience && (
              <div>
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
                  Ideal Customer / Target Audience
                </p>
                <p className="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
                  {truncate(targetAudience)}
                </p>
              </div>
            )}
            <p className="text-xs text-neutral-400 dark:text-neutral-500 flex items-center gap-1">
              <ExternalLink className="h-3 w-3" />
              To update these, edit the client profile before running the tools.
            </p>
          </div>
        )}
      </div>
    );
  };

  // Auto-fill badge component
  const AutoFillBadge = ({ isAutoFilled }: { isAutoFilled: boolean }) => {
    if (!isAutoFilled) return null;

    return (
      <span className="ml-2 inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
        <CheckCircle2 className="h-3 w-3" />
        Auto-filled
      </span>
    );
  };

  // If no data is needed, skip this step
  if (requiredFields.length === 0) {
    onContinue({});
    return null;
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
            Additional Data Required
          </h3>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            The selected research tools need some additional information. Please provide the following data:
          </p>
        </div>

        <ClientContextPreview />

        <div className="space-y-6">
          {requiredFields.map(field => (
            <div key={field.key}>
              {field.type === 'text' && (
                <div>
                  <label className="mb-1 flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
                    {field.label}
                    {field.required && <span className="text-rose-500">*</span>}
                    <AutoFillBadge isAutoFilled={autoFilledFields.has(field.key)} />
                  </label>
                  <Input
                    value={typeof collectedData[field.key] === 'string' ? collectedData[field.key] as string : ''}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className={`${errors[field.key] ? 'border-rose-500' : ''} ${
                      autoFilledFields.has(field.key)
                        ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-300 dark:border-emerald-700'
                        : ''
                    }`}
                  />
                  {errors[field.key] && (
                    <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors[field.key]}</p>
                  )}
                  {field.helperText && (
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{field.helperText}</p>
                  )}
                </div>
              )}

              {field.type === 'textarea' && (
                <div>
                  <label className="mb-1 flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
                    {field.label}
                    {field.required && <span className="text-rose-500">*</span>}
                    <AutoFillBadge isAutoFilled={autoFilledFields.has(field.key)} />
                  </label>
                  <Textarea
                    value={typeof collectedData[field.key] === 'string' ? collectedData[field.key] as string : ''}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    rows={4}
                    className={`${errors[field.key] ? 'border-rose-500' : ''} ${
                      autoFilledFields.has(field.key)
                        ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-300 dark:border-emerald-700'
                        : ''
                    }`}
                  />
                  {errors[field.key] && (
                    <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors[field.key]}</p>
                  )}
                  {field.helperText && (
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{field.helperText}</p>
                  )}
                </div>
              )}

              {field.type === 'text-list' && (
                <div>
                  <label className="mb-1 flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
                    {field.label}
                    {field.required && <span className="text-rose-500">*</span>}
                    <AutoFillBadge isAutoFilled={autoFilledFields.has(field.key)} />
                  </label>
                  <Textarea
                    value={typeof collectedData[field.key] === 'string' ? collectedData[field.key] as string : ''}
                    onChange={(e) => handleTextListChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    rows={3}
                    className={`${errors[field.key] ? 'border-rose-500' : ''} ${
                      autoFilledFields.has(field.key)
                        ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-300 dark:border-emerald-700'
                        : ''
                    }`}
                  />
                  <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400">
                    Separate items with commas
                    {field.min && ` (minimum ${field.min})`}
                    {field.max && ` (maximum ${field.max})`}
                  </p>
                  {errors[field.key] && (
                    <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{errors[field.key]}</p>
                  )}
                  {field.helperText && (
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{field.helperText}</p>
                  )}
                </div>
              )}

              {field.type === 'content-list' && (
                <div>
                  {/* Special handling for content_inventory (Content Audit) */}
                  {field.key === 'content_inventory' ? (
                    <ContentAuditCollector
                      value={Array.isArray(collectedData[field.key]) ? collectedData[field.key] as never[] : []}
                      onChange={(pieces) => {
                        setCollectedData(prev => ({ ...prev, [field.key]: pieces }));
                        setErrors(prev => ({ ...prev, [field.key]: '' }));
                      }}
                      error={errors[field.key]}
                    />
                  ) : (
                    <>
                      <label className="mb-2 flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
                        <FileText className="h-4 w-4" />
                        {field.label}
                        {field.required && <span className="text-rose-500">*</span>}
                      </label>

                      <div className="space-y-3">
                        {(Array.isArray(collectedData[field.key]) ? collectedData[field.key] as string[] : []).map((sample: string, index: number) => (
                          <div key={index} className="flex gap-2">
                            <Textarea
                              value={sample}
                              onChange={(e) => handleContentListChange(field.key, index, e.target.value)}
                              placeholder={`${field.placeholder} (${index + 1}/${field.max || '∞'})`}
                              rows={3}
                              className="flex-1"
                            />
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleRemoveContentSample(field.key, index)}
                              className="mt-1"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                      </div>

                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleAddContentSample(field.key)}
                        disabled={!!(field.max && Array.isArray(collectedData[field.key]) && (collectedData[field.key] as unknown[]).length >= field.max)}
                        className="mt-3"
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Add Sample ({Array.isArray(collectedData[field.key]) ? (collectedData[field.key] as unknown[]).length : 0}/{field.max || '∞'})
                      </Button>

                      {errors[field.key] && (
                        <p className="mt-2 text-xs text-rose-600 dark:text-rose-400 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors[field.key]}
                        </p>
                      )}
                      {field.helperText && (
                        <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">{field.helperText}</p>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 flex justify-between border-t border-neutral-200 dark:border-neutral-700 pt-4">
          <Button variant="secondary" onClick={onBack}>
            Back to Tool Selection
          </Button>
          <Button variant="primary" onClick={handleContinue}>
            Continue to Execute Tools
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
