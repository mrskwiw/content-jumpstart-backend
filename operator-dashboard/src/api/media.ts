import apiClient from './client';

// Phase 12 — Media generation (audio + video).

export interface MediaAsset {
  id: string;
  kind: string; // audio | clip | video | final
  url: string; // durable storage key (sign via assetUrl())
  duration_s?: number | null;
  mime?: string | null;
}

export interface MediaJob {
  id: string;
  pipeline?: string | null;
  pipeline_run_id?: string | null;
  stage_index: number;
  kind: string;
  provider: string;
  status: string; // queued | processing | awaiting_dependency | done | failed | canceled
  external_id?: string | null;
  output_asset_id?: string | null;
  cost_cents: number;
  error_message?: string | null;
  retry_count: number;
}

export interface MediaJobDetail extends MediaJob {
  assets: MediaAsset[];
}

export interface StageEstimate {
  kind: string;
  provider: string;
  cost_cents: number;
}
export interface Estimate {
  pipeline: string;
  stages: StageEstimate[];
  total_cost_cents: number;
}

export interface GenerateResponse {
  estimate: Estimate;
  confirmed: boolean;
  root_job?: MediaJob;
}

export interface GenerateBody {
  pipeline?: string;
  kind?: string;
  spec: Record<string, unknown>;
  client_id?: string;
  project_id?: string;
  confirm: boolean;
}

export interface PipelineShape {
  [name: string]: { kind: string; provider: string }[];
}

export const mediaApi = {
  async pipelines(): Promise<PipelineShape> {
    const { data } = await apiClient.get<{ pipelines: PipelineShape }>('/api/media/pipelines');
    return data.pipelines;
  },
  async generate(body: GenerateBody): Promise<GenerateResponse> {
    const { data } = await apiClient.post<GenerateResponse>('/api/media/generate', body);
    return data;
  },
  async jobs(params?: { status?: string; pipeline?: string; run_id?: string }): Promise<MediaJob[]> {
    const { data } = await apiClient.get<MediaJob[]>('/api/media/jobs', { params });
    return data;
  },
  async job(id: string): Promise<MediaJobDetail> {
    const { data } = await apiClient.get<MediaJobDetail>(`/api/media/jobs/${id}`);
    return data;
  },
  async cancelJob(id: string): Promise<MediaJob> {
    const { data } = await apiClient.post<MediaJob>(`/api/media/jobs/${id}/cancel`);
    return data;
  },
  async cancelRun(runId: string): Promise<{ run_id: string; canceled: number }> {
    const { data } = await apiClient.post(`/api/media/runs/${runId}/cancel`);
    return data;
  },
  // Fresh signed URL for an asset (JSON — usable from the browser without the 302).
  async assetUrl(assetId: string): Promise<string> {
    const { data } = await apiClient.get<{ url: string }>(`/api/media/assets/${assetId}/url`);
    return data.url;
  },
};
