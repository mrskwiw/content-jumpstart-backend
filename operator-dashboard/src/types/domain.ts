import { z } from 'zod';

export const ClientStatusSchema = z.enum(['active', 'inactive']);
export type ClientStatus = z.infer<typeof ClientStatusSchema>;

export const ProjectStatusSchema = z.enum([
  'draft',
  'ready',
  'generating',
  'qa',
  'exported',
  'delivered',
  'error',
]);
export type ProjectStatus = z.infer<typeof ProjectStatusSchema>;

export const RunStatusSchema = z.enum(['pending', 'running', 'succeeded', 'failed']);
export type RunStatus = z.infer<typeof RunStatusSchema>;

export const DeliverableStatusSchema = z.enum(['draft', 'ready', 'delivered']);
export type DeliverableStatus = z.infer<typeof DeliverableStatusSchema>;

export const PlatformSchema = z.enum(['linkedin', 'twitter', 'facebook', 'blog', 'email', 'generic']);
export type Platform = z.infer<typeof PlatformSchema>;

// Input schema that accepts both name and companyName from backend
const ClientSchemaInput = z.object({
  id: z.string(),
  name: z.string().optional(),
  companyName: z.string().optional(),
  email: z.string().email().nullish(),
  businessDescription: z.string().nullish(),
  idealCustomer: z.string().nullish(),
  mainProblemSolved: z.string().nullish(),
  tonePreference: z.string().nullish(),
  platforms: z.array(z.string()).nullish(),
  customerPainPoints: z.array(z.string()).nullish(),
  customerQuestions: z.array(z.string()).nullish(),
  industry: z.string().nullish(),
  keywords: z.array(z.string()).nullish(),
  competitors: z.array(z.string()).nullish(),
  location: z.string().nullish(),
  createdAt: z.string().datetime({ offset: true }),
});

// Output schema with only 'name' field
const ClientSchemaOutput = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email().nullish(),
  businessDescription: z.string().nullish(),
  idealCustomer: z.string().nullish(),
  mainProblemSolved: z.string().nullish(),
  tonePreference: z.string().nullish(),
  platforms: z.array(z.string()).nullish(),
  customerPainPoints: z.array(z.string()).nullish(),
  customerQuestions: z.array(z.string()).nullish(),
  industry: z.string().nullish(),
  keywords: z.array(z.string()).nullish(),
  competitors: z.array(z.string()).nullish(),
  location: z.string().nullish(),
  createdAt: z.string().datetime({ offset: true }),
});

// Transform backend response (companyName) to frontend format (name)
export const ClientSchema = ClientSchemaInput.transform((data) => {
  const name = data.name || data.companyName;
  if (!name) {
    throw new Error('Either name or companyName is required');
  }
  const { companyName, ...rest } = data;
  return {
    ...rest,
    name,
  };
}).pipe(ClientSchemaOutput);
export type Client = z.infer<typeof ClientSchema>;

export const ProjectSchema = z.object({
  id: z.string(),
  clientId: z.string(),
  name: z.string(),
  status: z.string(),
  templates: z.array(z.string()).nullish(),
  templateQuantities: z.record(z.string(), z.number()).nullish(),
  platforms: z.array(z.string()).nullish(),
  targetPlatform: z.string().nullish(),
  tone: z.string().nullish(),
  numPosts: z.number().int().nullish(),
  pricePerPost: z.number().nullish(),
  researchPricePerPost: z.number().nullish(),
  totalPrice: z.number().nullish(),
  postsCost: z.number().nullish(),
  researchAddonCost: z.number().nullish(),
  toolsCost: z.number().nullish(),
  discountAmount: z.number().nullish(),
  selectedTools: z.array(z.string()).nullish(),
  createdAt: z.string().datetime({ offset: true }),
  updatedAt: z.string().datetime({ offset: true }).nullish(),
});
export type Project = z.infer<typeof ProjectSchema>;

export const RunSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  isBatch: z.boolean(),
  params: z.record(z.string(), z.unknown()).optional(),
  startedAt: z.string().datetime({ offset: true }),
  completedAt: z.string().datetime({ offset: true }).nullish(),
  logs: z.array(z.union([z.string(), z.object({ timestamp: z.string(), message: z.string() })])).nullish(),
  status: RunStatusSchema.optional(),
  errorMessage: z.string().nullish(),
  totalInputTokens: z.number().int().nullish(),
  totalOutputTokens: z.number().int().nullish(),
  totalCacheCreationTokens: z.number().int().nullish(),
  totalCacheReadTokens: z.number().int().nullish(),
  totalCostUsd: z.number().nullish(),
  estimatedCostUsd: z.number().nullish(),
  qaScore: z.number().nullish(),
});
export type Run = z.infer<typeof RunSchema>;

export const PostDraftSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  runId: z.string(),
  content: z.string(),
  templateId: z.string().nullish(),
  templateName: z.string().nullish(),
  variant: z.number().int().nullish(),
  targetPlatform: PlatformSchema.nullish(),
  wordCount: z.number().int().nullish(),
  readabilityScore: z.number().nullish(),
  hasCta: z.boolean().nullish(),
  status: z.enum(['pending', 'flagged', 'approved', 'regenerating']).optional(),
  flags: z.array(z.string()).optional(),
  createdAt: z.string().datetime({ offset: true }),
  inputTokens: z.number().int().nullish(),
  outputTokens: z.number().int().nullish(),
  cacheReadTokens: z.number().int().nullish(),
  costUsd: z.number().nullish(),
  twitterShareCopy: z.string().nullish(),
});
export type PostDraft = z.infer<typeof PostDraftSchema>;

export const DeliverableSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  clientId: z.string(),
  format: z.enum(['txt', 'md', 'docx']),
  path: z.string(),
  createdAt: z.string().datetime({ offset: true }),
  status: DeliverableStatusSchema,
  deliveredAt: z.string().datetime({ offset: true }).nullish(),
  proofUrl: z.string().url().nullish(),
  proofNotes: z.string().nullish(),
  runId: z.string().nullish(),
  checksum: z.string().nullish(),
  fileSizeBytes: z.number().nullish(),
});
export type Deliverable = z.infer<typeof DeliverableSchema>;

export const PostSummarySchema = z.object({
  id: z.string(),
  templateName: z.string().optional(),
  wordCount: z.number().nullish(),
  readabilityScore: z.number().nullish(),
  status: z.string(),
  flags: z.array(z.string()).nullish(),
  content: z.string().optional().default(''),
  contentPreview: z.string(),
});
export type PostSummary = z.infer<typeof PostSummarySchema>;

// Full post with complete content (used for editing)
export const PostSchema = PostSummarySchema.extend({
  content: z.string(),
});
export type Post = z.infer<typeof PostSchema>;

export const QASummarySchema = z.object({
  avgReadability: z.number().nullish(),
  avgWordCount: z.number().nullish(),
  totalPosts: z.number(),
  flaggedCount: z.number(),
  approvedCount: z.number(),
  ctaPercentage: z.number().nullish(),
  commonFlags: z.array(z.string()),
});
export type QASummary = z.infer<typeof QASummarySchema>;

export const ResearchResultSummarySchema = z.object({
  id: z.string(),
  userId: z.string(),
  clientId: z.string(),
  projectId: z.string().optional().nullable(),
  toolName: z.string(),
  toolLabel: z.string().optional().nullable(),
  toolPrice: z.number().optional().nullable(),
  actualCostUsd: z.number().optional().nullable(),
  summary: z.string().optional().nullable(),
  status: z.string(),
  errorMessage: z.string().nullish().nullable(),
  durationSeconds: z.number().optional().nullable(),
  createdAt: z.string().datetime({ offset: true }),
});
export type ResearchResultSummary = z.infer<typeof ResearchResultSummarySchema>;

export const DeliverableDetailsSchema = DeliverableSchema.extend({
  filePreview: z.string().nullish(),
  filePreviewTruncated: z.boolean(),
  posts: z.array(PostSummarySchema),
  qaSummary: QASummarySchema.nullish(),
  fileModifiedAt: z.string().datetime({ offset: true }).nullish(),
  researchResults: z.array(ResearchResultSummarySchema).optional().default([]),
});
export type DeliverableDetails = z.infer<typeof DeliverableDetailsSchema>;

export const AuditEntrySchema = z.object({
  id: z.string(),
  actor: z.string(),
  action: z.string(),
  targetType: z.enum(['project', 'run', 'deliverable', 'post', 'client']),
  targetId: z.string(),
  timestamp: z.string().datetime({ offset: true }),
  metadata: z.record(z.string(), z.unknown()).optional(),
});
export type AuditEntry = z.infer<typeof AuditEntrySchema>;

export const MarkDeliveredSchema = z.object({
  deliveredAt: z.string().datetime({ offset: true }),
  proofUrl: z.string().url().optional(),
  proofNotes: z.string().optional(),
});
export type MarkDeliveredInput = z.infer<typeof MarkDeliveredSchema>;

export const GenerateAllSchema = z.object({
  projectId: z.string(),
  clientId: z.string(),
  isBatch: z.boolean().default(true),
  templateQuantities: z.record(z.string(), z.number()).optional(),
  customTopics: z.array(z.string()).optional(),  // NEW: topic override for generation
  targetPlatform: z.string().optional(),  // NEW: target platform for platform-specific generation
});
export type GenerateAllInput = z.infer<typeof GenerateAllSchema>;

export const RegenerateSchema = z.object({
  projectId: z.string(),
  postIds: z.array(z.string()),
  reason: z.string().optional(),
});
export type RegenerateInput = z.infer<typeof RegenerateSchema>;

// Export target platforms
export const ExportTargetSchema = z.enum([
  // Social Media
  'linkedin-posts',
  'linkedin-articles',
  'twitter',
  'twitter-threads',
  'facebook',
  // Standard Formats
  'docx',
  'markdown',
  'txt',
]);
export type ExportTarget = z.infer<typeof ExportTargetSchema>;

// Export file formats
export const ExportFormatSchema = z.enum(['txt', 'md', 'docx', 'html', 'json', 'wxr']);
export type ExportFormat = z.infer<typeof ExportFormatSchema>;

export const ExportSchema = z.object({
  projectId: z.string(),
  clientId: z.string(),
  format: ExportFormatSchema,
  target: ExportTargetSchema.optional(),
  includeAuditLog: z.boolean().default(false),
  includeResearch: z.boolean().default(false),
});
export type ExportInput = z.infer<typeof ExportSchema>;

export const ClientBriefSchema = z.object({
  companyName: z.string().min(1, 'Company name is required'),
  businessDescription: z
    .string()
    .min(70, 'Business description must be at least 70 characters (required for research tools)'),
  idealCustomer: z
    .string()
    .min(20, 'Target audience description must be at least 20 characters (required for research tools)'),
  mainProblemSolved: z.string().optional(),
  tonePreference: z.string().default('professional'),
  platforms: z.array(PlatformSchema).optional(),
  customerPainPoints: z.array(z.string()).optional(),
  customerQuestions: z.array(z.string()).optional(),
  industry: z.string().optional(),
  keywords: z.array(z.string()).optional(),
  competitors: z.array(z.string()).optional(),
  location: z.string().optional(),
});
export type ClientBrief = z.infer<typeof ClientBriefSchema>;

export const ResearchResultSchema = z.object({
  id: z.string(),
  userId: z.string(),
  clientId: z.string(),
  projectId: z.string().nullish(),
  toolName: z.string(),
  toolLabel: z.string().nullish(),
  toolPrice: z.number().nullish(),
  params: z.record(z.string(), z.any()).nullish(),
  outputs: z.record(z.string(), z.string()),
  data: z.record(z.string(), z.unknown()).nullish(),
  status: z.string(),
  errorMessage: z.string().nullish(),
  durationSeconds: z.number().nullish(),
  createdAt: z.string().datetime({ offset: true }),
  inputTokens: z.number().int().nullish(),
  outputTokens: z.number().int().nullish(),
  cacheCreationTokens: z.number().int().nullish(),
  cacheReadTokens: z.number().int().nullish(),
  actualCostUsd: z.number().nullish(),
});
export type ResearchResult = z.infer<typeof ResearchResultSchema>;
