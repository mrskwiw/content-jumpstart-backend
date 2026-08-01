import type { BusinessSummary } from '@/api/engagement';

/** Build a CSV of exactly what the Analytics page shows (real loaded data, no fabrication). */
export function summaryToCsv(data: BusinessSummary): string {
  const esc = (v: string | number) => {
    let s = String(v);
    // Neutralize spreadsheet formula injection (CWE-1236): a cell beginning with a
    // formula-trigger char is executed as a formula when the export is opened in
    // Excel/Sheets. Tenant-controlled client/template names could carry a payload like
    // =HYPERLINK(...), so prefix such values with a single quote. Cover the full
    // OWASP-documented set: ASCII = + - @, the whitespace triggers tab/CR/LF, and the
    // full-width homoglyphs ＝ ＋ － ＠ (U+FF1D/FF0B/FF0D/FF20) some apps normalize.
    if (/^[=+\-@\t\r\n＝＋－＠]/.test(s)) s = `'${s}`;
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

/** Serialize the summary to CSV and trigger a browser download. */
export function downloadSummaryCsv(data: BusinessSummary): void {
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
