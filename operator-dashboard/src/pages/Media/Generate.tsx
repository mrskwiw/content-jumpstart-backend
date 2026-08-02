import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { mediaApi, Estimate, GenerateBody } from '@/api/media';

// Pipelines that generate from a prompt/script vs. standalone ops on an existing asset.
const PIPELINES = [
  { id: 'gen_image', label: 'Image (Flux)' },
  { id: 'talking_head', label: 'Talking-head video (HeyGen)' },
  { id: 'cinematic', label: 'Cinematic b-roll (Kling + stitch)' },
  { id: 'audio_only', label: 'Voiceover only (TTS)' },
] as const;
const AUDIO_OPS = [
  { id: 'audio_clean', label: 'Clean / de-noise (Voice Isolator)' },
  { id: 'audio_master', label: 'Loudness master (Auphonic)' },
  { id: 'dub', label: 'Dub / translate (ElevenLabs)' },
] as const;

const usd = (cents: number) => `$${(cents / 100).toFixed(2)}`;

type ApiError = { response?: { status?: number; data?: { detail?: string } } };
const detailOf = (e: unknown) => (e as ApiError)?.response?.data?.detail;
const statusOf = (e: unknown) => (e as ApiError)?.response?.status;

export default function MediaGenerate() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const pipelines = useQuery({ queryKey: ['media', 'pipelines'], queryFn: mediaApi.pipelines });

  const [choice, setChoice] = useState<string>('talking_head');
  const [script, setScript] = useState('');
  const [scenes, setScenes] = useState('');
  const [sourceAssetId, setSourceAssetId] = useState('');
  const [targetLang, setTargetLang] = useState('es');
  const [estimate, setEstimate] = useState<Estimate | null>(null);

  const isAudioOp = AUDIO_OPS.some((o) => o.id === choice);

  const body = useMemo<GenerateBody>(() => {
    const spec: Record<string, unknown> = {};
    if (choice === 'cinematic') {
      spec.scenes = scenes.split('\n').map((s) => s.trim()).filter(Boolean);
      if (script.trim()) spec.script = script.trim();
    } else if (isAudioOp) {
      spec.source_asset_id = sourceAssetId.trim();
      if (choice === 'dub') spec.target_lang = targetLang.trim();
    } else if (choice === 'gen_image') {
      spec.prompt = script.trim();
    } else {
      spec.script = script.trim();
    }
    return isAudioOp ? { kind: choice, spec, confirm: false } : { pipeline: choice, spec, confirm: false };
  }, [choice, script, scenes, sourceAssetId, targetLang, isAudioOp]);

  const estimateMut = useMutation({
    mutationFn: () => mediaApi.generate({ ...body, confirm: false }),
    onSuccess: (r) => setEstimate(r.estimate),
    onError: (e: unknown) => toast.error(detailOf(e) ?? 'Estimate failed'),
  });

  const confirmMut = useMutation({
    mutationFn: () => mediaApi.generate({ ...body, confirm: true }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['media', 'jobs'] });
      toast.success('Media job started');
      setEstimate(null);
      if (r.root_job?.pipeline_run_id) navigate(`/dashboard/media/jobs?run=${r.root_job.pipeline_run_id}`);
      else navigate('/dashboard/media/jobs');
    },
    onError: (e: unknown) => {
      const detail = detailOf(e) ?? 'Submit failed';
      toast.error(statusOf(e) === 402 ? `Over budget: ${detail}` : detail);
    },
  });

  const canEstimate = isAudioOp ? sourceAssetId.trim().length > 0 : choice === 'cinematic' ? scenes.trim().length > 0 : script.trim().length > 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Generate media</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Turn a script or prompt into finished audio/video. Review the cost estimate, then confirm to
          start — renders run in the background on the Jobs page.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>What to make</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              estimateMut.mutate();
            }}
          >
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">Type</span>
              <select
                className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-600 dark:bg-neutral-900"
                value={choice}
                onChange={(e) => {
                  setChoice(e.target.value);
                  setEstimate(null);
                }}
              >
                <optgroup label="Generate">
                  {PIPELINES.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Process an existing audio asset">
                  {AUDIO_OPS.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </optgroup>
              </select>
            </label>

            {choice === 'cinematic' && (
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">
                  Scenes (one prompt per line — each becomes a clip)
                </span>
                <Textarea
                  rows={4}
                  value={scenes}
                  onChange={(e) => setScenes(e.target.value)}
                  placeholder={'a city skyline at dawn\na coffee being poured, slow motion'}
                />
              </label>
            )}

            {isAudioOp ? (
              <>
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">
                    Source asset id (a media asset you own)
                  </span>
                  <Input
                    value={sourceAssetId}
                    onChange={(e) => setSourceAssetId(e.target.value)}
                    placeholder="asset id from a previous job"
                  />
                </label>
                {choice === 'dub' && (
                  <label className="block text-sm">
                    <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">
                      Target language
                    </span>
                    <Input value={targetLang} onChange={(e) => setTargetLang(e.target.value)} placeholder="es" />
                  </label>
                )}
              </>
            ) : (
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">
                  {choice === 'cinematic'
                    ? 'Voiceover script (optional)'
                    : choice === 'gen_image'
                      ? 'Image prompt'
                      : 'Script'}
                </span>
                <Textarea
                  rows={4}
                  value={script}
                  onChange={(e) => setScript(e.target.value)}
                  placeholder={
                    choice === 'gen_image'
                      ? 'a golden retriever wearing sunglasses, studio lighting'
                      : 'What should it say?'
                  }
                />
              </label>
            )}

            <Button type="submit" loading={estimateMut.isPending} disabled={!canEstimate}>
              Estimate cost
            </Button>
          </form>
        </CardContent>
      </Card>

      {estimate && (
        <Card>
          <CardHeader>
            <CardTitle>Estimate — {usd(estimate.total_cost_cents)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <ul className="divide-y divide-neutral-200 text-sm dark:divide-neutral-800">
              {estimate.stages.map((s, i) => (
                <li key={i} className="flex justify-between py-1.5">
                  <span className="text-slate-700 dark:text-slate-300">
                    {s.kind} <span className="text-slate-400">· {s.provider}</span>
                  </span>
                  <span className="tabular-nums text-slate-500">{usd(s.cost_cents)}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-500">
              Estimated maximum; actual spend is billed per provider and shown on each job.
            </p>
            <div className="flex gap-2">
              <Button loading={confirmMut.isPending} onClick={() => confirmMut.mutate()}>
                Confirm &amp; start ({usd(estimate.total_cost_cents)})
              </Button>
              <Button variant="secondary" onClick={() => setEstimate(null)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {pipelines.isError && (
        <p className="text-xs text-red-600 dark:text-red-400">Couldn't load pipeline info.</p>
      )}
    </div>
  );
}
