import { describe, it, expect } from "@jest/globals";

const formatLastRun = (date: Date | undefined): { text: string; variant: "fresh" | "stale" | "never" } => {
  if (!date) return { text: "Never run", variant: "never" };

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return { text: "Today", variant: "fresh" };
  if (diffDays === 1) return { text: "Yesterday", variant: "fresh" };
  if (diffDays < 7) return { text: `${diffDays} days ago`, variant: "fresh" };
  if (diffDays < 30) return { text: `${Math.floor(diffDays / 7)} weeks ago`, variant: "fresh" };
  if (diffDays < 365) return { text: `${Math.floor(diffDays / 30)} months ago`, variant: "stale" };
  return { text: "Over a year ago", variant: "stale" };
};

describe("formatLastRun Helper", () => {
  it("should return never run for undefined", () => {
    expect(formatLastRun(undefined)).toEqual({ text: "Never run", variant: "never" });
  });

  it("should return Today for same day", () => {
    const today = new Date();
    expect(formatLastRun(today)).toEqual({ text: "Today", variant: "fresh" });
  });

  it("should return Yesterday for 1 day ago", () => {
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
    expect(formatLastRun(yesterday)).toEqual({ text: "Yesterday", variant: "fresh" });
  });

  it("should return days ago for 2-6 days", () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000);
    const result = formatLastRun(threeDaysAgo);
    expect(result.text).toBe("3 days ago");
    expect(result.variant).toBe("fresh");
  });

  it("should return weeks ago for 7-29 days", () => {
    const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);
    const result = formatLastRun(twoWeeksAgo);
    expect(result.text).toBe("2 weeks ago");
    expect(result.variant).toBe("fresh");
  });

  it("should return stale for 30+ days", () => {
    const fortyFiveDaysAgo = new Date(Date.now() - 45 * 24 * 60 * 60 * 1000);
    const result = formatLastRun(fortyFiveDaysAgo);
    expect(result.variant).toBe("stale");
  });

  it("should return over a year ago for 365+ days", () => {
    const overAYear = new Date(Date.now() - 400 * 24 * 60 * 60 * 1000);
    expect(formatLastRun(overAYear)).toEqual({ text: "Over a year ago", variant: "stale" });
  });
});
