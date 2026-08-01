import { describe, it, expect } from '@jest/globals';
import { summaryToCsv } from '../analyticsCsv';
import type { BusinessSummary } from '@/api/engagement';

const base: BusinessSummary = {
  days: 90,
  totals: { projects: 1, posts: 1, clients: 1 },
  monthly: [{ month: '2026-07', projects: 1, posts: 1 }],
  by_client: [{ client_name: 'Acme', projects: 1, posts: 1 }],
  by_template: [{ template_name: 'How-To', usage_count: 1 }],
};

describe('summaryToCsv', () => {
  it('serializes totals, monthly, client, and template rows', () => {
    const csv = summaryToCsv(base);
    expect(csv.split('\n')[0]).toBe('section,label,projects_or_uses,posts');
    expect(csv).toContain('monthly,2026-07,1,1');
    expect(csv).toContain('by_client,Acme,1,1');
    expect(csv).toContain('by_template,How-To,1,');
  });

  it('neutralizes spreadsheet formula injection in tenant-controlled names', () => {
    const csv = summaryToCsv({
      ...base,
      by_client: [{ client_name: '=HYPERLINK("http://evil","x")', projects: 1, posts: 1 }],
      by_template: [{ template_name: '+CMD()', usage_count: 1 }],
    });

    // Formula-leading cells are single-quote-prefixed (and quoted because of the comma).
    expect(csv).toContain(`"'=HYPERLINK(""http://evil"",""x"")"`);
    expect(csv).toContain("'+CMD()");
    // A raw, unneutralized formula must never appear at a cell boundary.
    expect(csv).not.toMatch(/(^|,)=HYPERLINK/m);
    expect(csv).not.toMatch(/(^|,)\+CMD/m);
  });

  it('also neutralizes - and @ leading cells', () => {
    const csv = summaryToCsv({
      ...base,
      by_client: [
        { client_name: '-2+3', projects: 1, posts: 1 },
        { client_name: '@SUM(A1)', projects: 1, posts: 1 },
      ],
    });
    expect(csv).toContain("'-2+3");
    expect(csv).toContain("'@SUM(A1)");
  });
});
