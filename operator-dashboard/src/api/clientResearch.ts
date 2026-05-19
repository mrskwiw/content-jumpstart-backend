import apiClient from './client';
import type { ClientBrief, Platform } from '@/types/domain';

export interface ClientResearchRequest {
  name: string;
  location: string;
  website?: string;
}

/** snake_case → camelCase mapping for the brief dict returned by the backend */
function mapBriefToCamel(brief: Record<string, unknown>): Partial<ClientBrief> {
  return {
    companyName: (brief.company_name as string) ?? '',
    founderName: (brief.founder_name as string | null) ?? undefined,
    businessDescription: (brief.business_description as string | null) ?? undefined,
    industry: (brief.industry as string | null) ?? undefined,
    keywords: (brief.keywords as string[]) ?? [],
    competitors: (brief.competitors as string[]) ?? [],
    location: (brief.location as string | null) ?? undefined,
    idealCustomer: (brief.ideal_customer as string | null) ?? undefined,
    mainProblemSolved: (brief.main_problem_solved as string | null) ?? undefined,
    customerPainPoints: (brief.customer_pain_points as string[]) ?? [],
    customerQuestions: (brief.customer_questions as string[]) ?? [],
    tonePreference: (brief.tone_preference as string | null) ?? undefined,
    brandPersonality: (brief.brand_personality as string[]) ?? [],
    brandVoice: (brief.brand_voice as string | null) ?? undefined,
    toneToAvoid: (brief.tone_to_avoid as string | null) ?? undefined,
    keyPhrases: (brief.key_phrases as string[]) ?? [],
    platforms: (brief.target_platforms as Platform[]) ?? [],
    postingFrequency: (brief.posting_frequency as string | null) ?? undefined,
    mainCta: (brief.main_cta as string | null) ?? undefined,
    measurableResults: (brief.measurable_results as string | null) ?? undefined,
    stories: (brief.stories as string[]) ?? [],
    misconceptions: (brief.misconceptions as string[]) ?? [],
  };
}

export interface ClientResearchResult {
  brief: Partial<ClientBrief>;
  /** Raw snake_case brief dict from the backend — used by the download endpoint */
  rawBrief: Record<string, unknown>;
  /** field_name → 0.0–1.0 confidence score */
  confidence: Record<string, number>;
  sources: string[];
  durationSeconds: number;
  stubMode: boolean;
  warning?: string;
  creditCost: number;
}

async function researchBrief(req: ClientResearchRequest): Promise<ClientResearchResult> {
  const { data } = await apiClient.post('/api/client-research/brief', req);
  const rawBrief: Record<string, unknown> = data.brief ?? {};
  return {
    brief: mapBriefToCamel(rawBrief),
    rawBrief,
    confidence: data.confidence ?? {},
    sources: data.sources ?? [],
    durationSeconds: data.duration_seconds ?? 0,
    stubMode: data.stub_mode ?? false,
    warning: data.warning ?? undefined,
    creditCost: data.credit_cost ?? 200,
  };
}

async function applyToClient(clientId: string): Promise<void> {
  await apiClient.post(`/api/client-research/clients/${clientId}/apply`);
}

export type BriefFormat = 'md' | 'docx' | 'pdf';

async function downloadBrief(
  brief: Record<string, unknown>,
  confidence: Record<string, number>,
  format: BriefFormat,
  companyName?: string,
): Promise<void> {
  const response = await apiClient.post(
    '/api/client-research/brief/download',
    { brief, confidence, format, company_name: companyName },
    { responseType: 'blob' },
  );

  const mimeTypes: Record<BriefFormat, string> = {
    md: 'text/markdown',
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    pdf: 'application/pdf',
  };

  const blob = new Blob([response.data as BlobPart], { type: mimeTypes[format] });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const safe = (companyName ?? 'client-brief').replace(/\s+/g, '_');
  a.href = url;
  a.download = `${safe}_brief.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

export const clientResearchApi = { researchBrief, applyToClient, downloadBrief };
