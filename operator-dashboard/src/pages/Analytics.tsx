import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, FileText, Users, LayoutTemplate, Download } from 'lucide-react';
import { engagementApi, type BusinessSummary } from '@/api/engagement';

/** Build a CSV of exactly what the page shows (real loaded data, no fabrication). */
function summaryToCsv(data: BusinessSummary): string {
  const esc = (v: string | number) => {
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const rows: string[] = [
    'section,label,projects_or_uses,posts',
    esc('totals') + `,All,${data.totals.projects},${data.totals.posts}`,
    ...data.monthly.map((m) => `monthly,${esc(m.month)},${m.projects},${m.posts}`),
    ...data.by_client.map((c) => `by_client,${esc(c.client_name)},${c.projects},${c.posts}`),
    ...data.by_template.map((t) => `by_template,${esc(t.template_name)},${t.usage_count},`),
  ];
  return rows.join('\n');
}

function downloadCsv(data: BusinessSummary) {
  const blob = new Blob([summaryToCsv(data)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `analytics-${data.days}d.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const RANGES: Array<{ label: string; days: number }> = [
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Last year', days: 365 },
];

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-700 dark:bg-neutral-900">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{label}</span>
        <Icon className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
      </div>
      <div className="mt-2 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
        {value.toLocaleString()}
      </div>
    </div>
  );
}

export default function Analytics() {
  const [days, setDays] = useState(90);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics', 'business-summary', days],
    queryFn: () => engagementApi.businessSummary(days),
  });

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">Analytics</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Project, post, client, and template activity across your workspace.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
          >
            {RANGES.map((r) => (
              <option key={r.days} value={r.days}>
                {r.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => data && downloadCsv(data)}
            disabled={!data}
            className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-200 dark:hover:bg-neutral-700"
          >
            <Download className="h-4 w-4" /> Export CSV
          </button>
        </div>
      </header>

      {isLoading && (
        <div className="flex h-64 items-center justify-center text-neutral-500">Loading analytics…</div>
      )}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50/40 p-6 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-400">
          Couldn't load analytics.
        </div>
      )}

      {data && (
        <>
          {/* KPI cards — real counts only (revenue/quality are not tracked). */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="Projects" value={data.totals.projects} icon={BarChart3} />
            <StatCard label="Posts" value={data.totals.posts} icon={FileText} />
            <StatCard label="Active clients" value={data.totals.clients} icon={Users} />
          </div>

          {/* Monthly trend */}
          <section className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-700 dark:bg-neutral-900">
            <h2 className="mb-3 text-sm font-semibold text-neutral-700 dark:text-neutral-200">
              Monthly activity
            </h2>
            {data.monthly.length === 0 ? (
              <p className="text-sm text-neutral-400">No activity in this window.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-neutral-500 dark:text-neutral-400">
                  <tr>
                    <th className="py-1 font-medium">Month</th>
                    <th className="py-1 font-medium text-right">Projects</th>
                    <th className="py-1 font-medium text-right">Posts</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
                  {data.monthly.map((m) => (
                    <tr key={m.month}>
                      <td className="py-1.5 text-neutral-800 dark:text-neutral-200">{m.month}</td>
                      <td className="py-1.5 text-right text-neutral-800 dark:text-neutral-200">{m.projects}</td>
                      <td className="py-1.5 text-right text-neutral-800 dark:text-neutral-200">{m.posts}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* By client */}
            <section className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-700 dark:bg-neutral-900">
              <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-neutral-700 dark:text-neutral-200">
                <Users className="h-4 w-4" /> By client
              </h2>
              {data.by_client.length === 0 ? (
                <p className="text-sm text-neutral-400">No client activity in this window.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-left text-neutral-500 dark:text-neutral-400">
                    <tr>
                      <th className="py-1 font-medium">Client</th>
                      <th className="py-1 font-medium text-right">Projects</th>
                      <th className="py-1 font-medium text-right">Posts</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
                    {data.by_client.map((c) => (
                      <tr key={c.client_name}>
                        <td className="py-1.5 text-neutral-800 dark:text-neutral-200">{c.client_name}</td>
                        <td className="py-1.5 text-right text-neutral-800 dark:text-neutral-200">{c.projects}</td>
                        <td className="py-1.5 text-right text-neutral-800 dark:text-neutral-200">{c.posts}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            {/* By template */}
            <section className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-700 dark:bg-neutral-900">
              <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-neutral-700 dark:text-neutral-200">
                <LayoutTemplate className="h-4 w-4" /> By template
              </h2>
              {data.by_template.length === 0 ? (
                <p className="text-sm text-neutral-400">No template usage in this window.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-left text-neutral-500 dark:text-neutral-400">
                    <tr>
                      <th className="py-1 font-medium">Template</th>
                      <th className="py-1 font-medium text-right">Uses</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
                    {data.by_template.map((t) => (
                      <tr key={t.template_name}>
                        <td className="py-1.5 text-neutral-800 dark:text-neutral-200">{t.template_name}</td>
                        <td className="py-1.5 text-right text-neutral-800 dark:text-neutral-200">{t.usage_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
