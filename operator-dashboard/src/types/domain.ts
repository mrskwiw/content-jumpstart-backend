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

export const PlatformSchema = z.enum(['linkedin', 'twitter', 'blog', 'email', 'generic']);
export type Platform = z.infer<typeof PlatformSchema>;

export const ClientSchema = z.object({
  id: z.string(),
  name: z.string(),
  tags: z.array(z.string()).optional(),
  status: ClientStatusSchema.optional(),
});
export type Client = z.infer<typeof ClientSchema>;

export const ProjectSchema = z.object({
  id: z.string(),
  clientId: z.string(),
  name: z.string(),
  status: ProjectStatusSchema,
  templates: z.array(z.string()),
  platforms: z.array(PlatformSchema),
  tone: z.string().optional(),
  lastRunAt: z.string().datetime().optional(),
  updatedAt: z.string().datetime().optional(),
  createdAt: z.string().datetime().optional(),
});
export type Project = z.infer<typeof ProjectSchema>;

export const RunSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  isBatch: z.boolean().optional(),
  params: z.record(z.string(), z.any()).optional(),
  startedAt: z.string().datetime(),
  completedAt: z.string().datetime().optional(),
  logs: z.array(z.string()).optional(),
  status: RunStatusSchema.optional(),
});
export type Run = z.infer<typeof RunSchema>;

export const PostDraftSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  runId: z.string(),
  content: z.string(),
  length: z.number().int().nonnegative().optional(),
  readabilityScore: z.number().optional(),
  hasCta: z.boolean().optional(),
  platform: PlatformSchema.optional(),
  status: z.enum(['pending', 'flagged', 'approved', 'regenerating']).optional(),
  flags: z.array(z.string()).optional(),
  notes: z.string().optional(),
});
export type PostDraft = z.infer<typeof PostDraftSchema>;

export const DeliverableSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  clientId: z.string(),
  format: z.enum(['txt', 'docx']),
  path: z.string(),
  createdAt: z.string().datetime(),
  status: DeliverableStatusSchema,
  deliveredAt: z.string().datetime().optional(),
  proofUrl: z.string().url().optional(),
  proofNotes: z.string().optional(),
  runId: z.string().optional(),
  checksum: z.string().optional(),
});
export type Deliverable = z.infer<typeof DeliverableSchema>;

export const AuditEntrySchema = z.object({
  id: z.string(),
  actor: z.string(),
  action: z.string(),
  targetType: z.enum(['project', 'run', 'deliverable', 'post', 'client']),
  targetId: z.string(),
  timestamp: z.string().datetime(),
  metadata: z.record(z.string(), z.any()).optional(),
});
export type AuditEntry = z.infer<typeof AuditEntrySchema>;

export const MarkDeliveredSchema = z.object({
  deliveredAt: z.string().datetime(),
  proofUrl: z.string().url().optional(),
  proofNotes: z.string().optional(),
});
export type MarkDeliveredInput = z.infer<typeof MarkDeliveredSchema>;

export const GenerateAllSchema = z.object({
  projectId: z.string(),
  clientId: z.string(),
  isBatch: z.boolean().default(true),
});
export type GenerateAllInput = z.infer<typeof GenerateAllSchema>;

export const RegenerateSchema = z.object({
  projectId: z.string(),
  postIds: z.array(z.string()),
  reason: z.string().optional(),
});
export type RegenerateInput = z.infer<typeof RegenerateSchema>;

export const ExportSchema = z.object({
  projectId: z.string(),
  clientId: z.string(),
  format: z.enum(['txt', 'docx']),
  includeAuditLog: z.boolean().default(false),
});
export type ExportInput = z.infer<typeof ExportSchema>;

export const ClientBriefSchema = z.object({
  companyName: z.string().min(1, 'Company name is required'),
  businessDescription: z.string().min(10, 'Please provide a brief business description'),
  idealCustomer: z.string().min(10, 'Please describe your ideal customer'),
  mainProblemSolved: z.string().min(10, 'Describe the main problem you solve'),
  tonePreference: z.string().default('professional'),
  platforms: z.array(PlatformSchema).min(1, 'Select at least one platform'),
  customerPainPoints: z.array(z.string()).optional(),
  customerQuestions: z.array(z.string()).optional(),
});
export type ClientBrief = z.infer<typeof ClientBriefSchema>;
