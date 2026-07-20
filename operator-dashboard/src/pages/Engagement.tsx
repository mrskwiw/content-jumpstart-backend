import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { engagementApi } from '@/api/engagement';

const TIER_VARIANT: Record<string, 'success' | 'warning' | 'danger' | 'secondary'> = {
  excellent: 'success',
  good: 'success',
  average: 'warning',
  poor: 'danger',
};

function pct(rate: number | undefined) {
  return `${((rate ?? 0) * 100).toFixed(1)}%`;
}

export default function Engagement() {
  const qc = useQueryClient();
  const [overview, benchmarks, trend, insights, topPosts] = useQueries({
    queries: [
      { queryKey: ['eng-overview'], queryFn: engagementApi.overview },
      { queryKey: ['eng-benchmarks'], queryFn: engagementApi.benchmarks },
      { queryKey: ['eng-trend'], queryFn: engagementApi.trend },
      { queryKey: ['eng-insights'], queryFn: engagementApi.insights },
      { queryKey: ['eng-top'], queryFn: engagementApi.topPosts },
    ],
  });

  const collect = useMutation({
    mutationFn: engagementApi.collect,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['eng-overview'] }).then(() => qc.invalidateQueries()),
  });

  const downloadReport = useMutation({
    mutationFn: engagementApi.reportPdf,
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'engagement-report.pdf';
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const ov = overview.data;
  const tr = trend.data;
  const trendColor =
    tr?.direction === 'up'
      ? 'text-emerald-600'
      : tr?.direction === 'down'
        ? 'text-red-600'
        : 'text-slate-500';

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
            Engagement analytics
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Real social engagement across your connected accounts.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" loading={collect.isPending} onClick={() => collect.mutate()}>
            Refresh metrics
          </Button>
          <Button
            variant="outline"
            loading={downloadReport.isPending}
            onClick={() => downloadReport.mutate()}
          >
            Download PDF
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Posts" value={ov?.posts ?? 0} />
        <Stat label="Impressions" value={(ov?.impressions ?? 0).toLocaleString()} />
        <Stat label="Engagements" value={(ov?.engagement ?? 0).toLocaleString()} />
        <Stat
          label="Engagement rate"
          value={pct(ov?.engagement_rate)}
          sub={
            tr && tr.direction !== 'flat' ? (
              <span className={trendColor}>
                {tr.direction === 'up' ? '▲' : '▼'} {Math.abs(tr.change_pct)}% vs prior
              </span>
            ) : undefined
          }
        />
      </div>

      {insights.data && insights.data.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Insights</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm text-slate-700 dark:text-slate-300">
              {insights.data.map((line, i) => (
                <li key={i}>• {line}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>By platform</CardTitle>
          </CardHeader>
          <CardContent>
            {(benchmarks.data ?? []).length === 0 ? (
              <Empty />
            ) : (
              <ul className="space-y-2">
                {(benchmarks.data ?? []).map((row) => (
                  <li key={row.platform} className="flex items-center justify-between text-sm">
                    <span className="font-medium capitalize">{row.platform}</span>
                    <span className="flex items-center gap-2">
                      <span className="text-slate-500">{pct(row.engagement_rate)}</span>
                      <Badge variant={TIER_VARIANT[row.benchmark_tier] ?? 'secondary'}>
                        {row.benchmark_tier}
                      </Badge>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top posts</CardTitle>
          </CardHeader>
          <CardContent>
            {(topPosts.data ?? []).length === 0 ? (
              <Empty />
            ) : (
              <ul className="space-y-2">
                {(topPosts.data ?? []).slice(0, 5).map((p, i) => (
                  <li key={i} className="flex items-center justify-between text-sm">
                    <span className="min-w-0 truncate">
                      <span className="mr-2 text-xs uppercase text-slate-400">{p.platform}</span>
                      {p.template ?? 'untagged'}
                    </span>
                    <span className="text-slate-500">{pct(p.engagement_rate)}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
        {sub && <p className="mt-1 text-xs">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function Empty() {
  return (
    <p className="text-sm text-slate-500">
      No data yet — connect an account, publish, then Refresh metrics.
    </p>
  );
}
