import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import type { WritingStats, WritingStatsWords } from "../../../src/app/types/studio";
import { createProject, typeChapter } from "../content_acceptance_helpers";

// Placement contract: same as studio_diagnostics_export.spec.ts — this
// directory sorts after studio-ts.spec.ts under Playwright's localeCompare
// file order, so the owner-setup file always starts in the first worker
// wave and the login polling below cannot starve it (see #467 PR notes).

// #653 (T5.1) writing stats workflow: real author writing and an accepted
// Copilot proposal land attributed revisions, and the Stats inspector tab
// (deep link `?inspector=stats`) mirrors the aggregation's own figures —
// the spec never recomputes the word-count definition, it reads the stats
// response the panel just rendered and asserts the view against it. The
// deterministic mock provider reports no token counts, so its usage ledger
// rows fall back to the word-count estimates of the proposal landing —
// the same accounting the usage tab shows — and stay assertably positive.

// Same fragment-assembled credential as studio-ts.spec.ts, which owns the
// one-time owner setup on the shared store this suite logs into.
const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");

// Short on purpose: the accepted deterministic revision (~280 words) must
// exceed the typed author passage, so the day's ai_accepted delta is
// unambiguously positive.
const AUTHOR_CHAPTER = [
  "# Chapter 1",
  "",
  "The lamplighter counted nine steps down, then wrote the number in his",
  "ledger before the rain could erase it.",
].join("\n");

/** The panel's exact figure rendering: en-US grouping, pinned by the config. */
function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

function totalWords(words: WritingStatsWords): number {
  return words.author + words.ai_accepted + words.restore;
}

/**
 * Deep link into the Stats inspector tab and capture the stats response the
 * panel's lazy first-activation load just fired, so every view assertion
 * compares against the exact payload the UI rendered.
 */
async function openStatsTab(page: Page, projectId: string): Promise<WritingStats> {
  const statsEndpoint = `/api/projects/${projectId}/stats`;
  const responsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" && new URL(response.url()).pathname === statsEndpoint,
  );
  await page.goto(`/projects/${projectId}/manuscript?inspector=stats`);
  const response = await responsePromise;
  expect(response.status(), await response.text()).toBe(200);
  return (await response.json()) as WritingStats;
}

test.describe
  .serial("#653 writing stats workflow", () => {
    test.setTimeout(150_000);

    let studioContext: BrowserContext;
    let studio: Page;

    test.beforeAll(async ({ browser }) => {
      studioContext = await browser.newContext();
      studio = await studioContext.newPage();
      // In the full suite the owner setup is owned by studio-ts.spec.ts, which
      // starts in the first worker wave; this file only logs in. Run
      // standalone (`-- writing_stats`) against the same fresh store, no
      // other file creates the owner, so after the grace period this spec
      // completes the one-time setup itself with the same credential. Each
      // poll reloads the entry page — the rendered form only reflects the
      // owner's existence after a fresh load. Either path ends signed in at
      // the projects list.
      let ownerConfigured = false;
      const deadline = Date.now() + 20_000;
      while (!ownerConfigured && Date.now() < deadline) {
        await studio.goto("/");
        ownerConfigured = await studio
          .getByRole("heading", { name: "Open your writing studio" })
          .isVisible();
        if (!ownerConfigured) {
          await studio.waitForTimeout(2_000);
        }
      }
      await studio.getByLabel("Password").fill(OWNER_PASSWORD);
      await studio
        .getByRole("button", { name: ownerConfigured ? "Sign in" : "Create owner" })
        .click();
      await expect(studio).toHaveURL(/\/projects$/);
    });

    test.afterAll(async () => {
      await studioContext.close();
    });

    test("attributes author writing and an accepted proposal across the stats tab", async () => {
      const projectId = await createProject(studio, "Writing Stats Ledger");
      await typeChapter(studio, AUTHOR_CHAPTER);

      // The Copilot flow of the deterministic mock provider: Continue
      // proposes, Accept lands the ai-accepted revision and saves.
      await studio.getByLabel("Proposal instruction").fill("Bring the rain in.");
      await studio.getByRole("button", { name: "Continue" }).click();
      await expect(studio.getByRole("button", { name: "Accept" })).toBeVisible();
      await studio.getByRole("button", { name: "Accept" }).click();
      await expect(studio.getByText("Proposed Markdown")).toHaveCount(0);
      await expect(studio.locator(".studio-editor .editor__save-state")).toHaveText(/saved/i);

      const stats = await openStatsTab(studio, projectId);

      // The aggregation invariants this workflow just produced: an author
      // revision today (UTC) extends the streak, both source splits moved
      // the current UTC day positively, and the mock generation recorded a
      // usage event whose word-count fallback keeps the token sums positive.
      expect(stats.streak_days).toBeGreaterThanOrEqual(1);
      const today = stats.daily.at(-1);
      if (today === undefined) throw new Error("The stats window carried no trailing day.");
      expect(today.date).toBe(new Date().toISOString().slice(0, 10));
      expect(today.words.author).toBeGreaterThan(0);
      expect(today.words.ai_accepted).toBeGreaterThan(0);
      expect(stats.usage.request_count).toBe(1);
      expect(stats.usage.prompt_tokens + stats.usage.completion_tokens).toBeGreaterThan(0);

      // The tab the deep link selected, and the panel's own heading family.
      const tab = studio.getByRole("tab", { name: "Stats" });
      await expect(tab).toHaveAttribute("aria-selected", "true");
      const panel = studio.getByRole("tabpanel", { name: "Stats" });
      await expect(panel.getByRole("heading", { name: "Writing stats" })).toBeVisible();
      await expect(panel.getByText("Words per UTC day, attributed by source.")).toBeVisible();

      // Summary cards mirror the payload: streak, the day's net words, and
      // the started-chapters share.
      await expect(
        panel.getByRole("group", { name: `Day streak: ${formatCount(stats.streak_days)}` }),
      ).toBeVisible();
      await expect(
        panel.getByRole("group", {
          name: `Words today: ${formatCount(totalWords(today.words))}`,
        }),
      ).toBeVisible();
      await expect(
        panel.getByText(
          `${formatCount(stats.chapters.started)} of ${formatCount(stats.chapters.total)} chapters started`,
        ),
      ).toBeVisible();

      // The daily table's today row (UTC) carries the source split and its
      // total, under the source-named columns.
      const dailyTable = panel.getByRole("table", {
        name: "Daily words by source, last 30 days",
      });
      for (const column of ["Author", "Accepted", "Restored", "Total"]) {
        await expect(dailyTable.getByRole("columnheader", { name: column })).toBeVisible();
      }
      const todayRow = dailyTable.locator("tbody tr").filter({ hasText: today.date });
      await expect(todayRow.locator("td")).toHaveText([
        today.date,
        formatCount(today.words.author),
        formatCount(today.words.ai_accepted),
        formatCount(today.words.restore),
        formatCount(totalWords(today.words)),
      ]);

      // The current week's rollup sums the same split into one row.
      const currentWeek = stats.weekly.at(-1);
      if (currentWeek === undefined) throw new Error("The stats window carried no week.");
      const weeklyTable = panel.getByRole("table", { name: "Weekly words by source" });
      const weekRow = weeklyTable.locator("tbody tr").filter({ hasText: currentWeek.start_date });
      await expect(weekRow.locator("td")).toHaveText([
        currentWeek.start_date,
        formatCount(currentWeek.words.author),
        formatCount(currentWeek.words.ai_accepted),
        formatCount(currentWeek.words.restore),
        formatCount(totalWords(currentWeek.words)),
      ]);

      // The AI usage summary reuses the usage accounting's figures.
      const usageRegion = panel.getByRole("region", { name: "AI usage" });
      await expect(
        usageRegion.getByRole("group", {
          name: `Requests: ${formatCount(stats.usage.request_count)}`,
        }),
      ).toBeVisible();
      await expect(
        usageRegion.getByRole("group", {
          name: `Prompt tokens: ${formatCount(stats.usage.prompt_tokens)}`,
        }),
      ).toBeVisible();
      await expect(
        usageRegion.getByRole("group", {
          name: `Completion tokens: ${formatCount(stats.usage.completion_tokens)}`,
        }),
      ).toBeVisible();
    });

    test("renders the defined zero states for a project with no writing", async () => {
      const projectId = await createProject(studio, "Stats Blank Slate");

      // A fresh project seeds Chapter 1 with a two-word author revision, so
      // a truly empty project needs that seed gone: delete it through the
      // Navigator row command, the same workflow an author uses.
      await studio.getByRole("button", { name: "Delete Chapter 1" }).click();
      await studio.getByRole("button", { name: "Confirm delete Chapter 1" }).click();
      await expect(studio.getByRole("button", { name: "Delete Chapter 1" })).toHaveCount(0);

      const stats = await openStatsTab(studio, projectId);

      // Premise check: the aggregation reports a genuinely quiet project.
      expect(stats.streak_days).toBe(0);
      expect(stats.chapters).toEqual({ total: 0, started: 0 });
      expect(stats.usage.request_count).toBe(0);
      expect(
        stats.daily.every(
          (row) => row.words.author === 0 && row.words.ai_accepted === 0 && row.words.restore === 0,
        ),
      ).toBe(true);

      // The panel answers with honest zeros instead of placeholders: every
      // summary card (stats and usage alike), the share line, and the empty
      // writing state; no attributed-words table renders at all.
      const panel = studio.getByRole("tabpanel", { name: "Stats" });
      await expect(panel.getByRole("heading", { name: "Writing stats" })).toBeVisible();
      for (const cardLabel of [
        "Day streak: 0",
        "Chapters started: 0",
        "Words today: 0",
        "Requests: 0",
        "Prompt tokens: 0",
        "Completion tokens: 0",
      ]) {
        await expect(panel.getByRole("group", { name: cardLabel })).toBeVisible();
      }
      await expect(panel.getByText("0 of 0 chapters started")).toBeVisible();
      await expect(panel.getByText("No writing recorded yet.")).toBeVisible();
      await expect(panel.locator(".stats__table")).toHaveCount(0);
    });
  });
