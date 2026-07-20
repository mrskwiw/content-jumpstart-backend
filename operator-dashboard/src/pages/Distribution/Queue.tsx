import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge, BadgeProps } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { distributionApi, ScheduledPost } from '@/api/distribution';

const STATUS_VARIANT: Record<string, BadgeProps['variant']> = {
  pending: 'secondary',
  posting: 'warning',
  posted: 'success',
  failed: 'danger',
  canceled: 'default',
};

export default function Queue() {
  const qc = useQueryClient();
  const creds = useQuery({ queryKey: ['credentials'], queryFn: distributionApi.listCredentials });
  const queue = useQuery({ queryKey: ['queue'], queryFn: () => distributionApi.queue() });

  const [platform, setPlatform] = useState('stub');
  const [content, setContent] = useState('');
  const [scheduledFor, setScheduledFor] = useState('');
  const [mediaUrl, setMediaUrl] = useState('');

  const schedule = useMutation({
    mutationFn: () =>
      distributionApi.schedule({
        platform,
        content,
        scheduled_for: new Date(scheduledFor || Date.now()).toISOString(),
        media_url: mediaUrl || undefined,
      }),
    onSuccess: () => {
      setContent('');
      setMediaUrl('');
      qc.invalidateQueries({ queryKey: ['queue'] });
    },
  });

  const publishNow = useMutation({
    mutationFn: (id: string) => distributionApi.publishNow(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  });

  // Connected platforms plus the always-available stub (safe demo target).
  const platformOptions = ['stub', ...(creds.data ?? []).map((c) => c.platform)];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          Publishing queue
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Schedule posts to connected accounts. The scheduler publishes them at their time; you can
          also publish immediately.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Schedule a post</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              schedule.mutate();
            }}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-sm">
                <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">
                  Platform
                </span>
                <select
                  className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-600 dark:bg-neutral-900"
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                >
                  {[...new Set(platformOptions)].map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">
                  Scheduled for
                </span>
                <Input
                  type="datetime-local"
                  value={scheduledFor}
                  onChange={(e) => setScheduledFor(e.target.value)}
                />
              </label>
            </div>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">
                Content
              </span>
              <Textarea
                rows={4}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="What do you want to post?"
                required
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700 dark:text-slate-300">
                Media URL (required for Instagram / TikTok / YouTube)
              </span>
              <Input
                value={mediaUrl}
                onChange={(e) => setMediaUrl(e.target.value)}
                placeholder="https://…"
              />
            </label>
            <Button type="submit" loading={schedule.isPending} disabled={!content}>
              Add to queue
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Queue</CardTitle>
        </CardHeader>
        <CardContent>
          {queue.isLoading ? (
            <p className="text-sm text-slate-500">Loading…</p>
          ) : (queue.data ?? []).length === 0 ? (
            <p className="text-sm text-slate-500">Nothing queued yet.</p>
          ) : (
            <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
              {(queue.data ?? []).map((post) => (
                <QueueRow key={post.id} post={post} onPublish={() => publishNow.mutate(post.id)} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function QueueRow({ post, onPublish }: { post: ScheduledPost; onPublish: () => void }) {
  return (
    <li className="flex items-start justify-between gap-4 py-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <Badge variant={STATUS_VARIANT[post.status] ?? 'default'}>{post.status}</Badge>
          <span className="text-xs font-medium uppercase text-slate-500">{post.platform}</span>
          <span className="text-xs text-slate-400">
            {new Date(post.scheduled_for).toLocaleString()}
          </span>
        </div>
        <p className="mt-1 truncate text-sm text-slate-700 dark:text-slate-300">{post.content}</p>
        {post.error_message && (
          <p className="mt-1 text-xs text-red-600 dark:text-red-400">{post.error_message}</p>
        )}
        {post.platform_url && (
          <a
            href={post.platform_url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-block text-xs text-blue-600 hover:underline dark:text-blue-400"
          >
            View published post →
          </a>
        )}
      </div>
      {post.status === 'pending' && (
        <Button size="sm" variant="secondary" onClick={onPublish}>
          Publish now
        </Button>
      )}
    </li>
  );
}
