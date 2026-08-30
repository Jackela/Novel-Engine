import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import {
  assertNarrativeProse,
  createProject,
  studioChapters,
  typeChapter,
} from "./content_acceptance_helpers";

interface ChapterDocument {
  id: string;
  kind: string;
  title: string;
  position: number;
  current_revision_id: string;
  content_markdown: string;
  revision_source: string;
}

test.describe
  .serial("#318 whole-book generation loop", () => {
    test.setTimeout(120_000);

    // Same fragment-assembled credential as studio-ts.spec.ts, which owns the
    // one-time owner setup on the shared store this suite logs into.
    const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");

    let studioContext: BrowserContext;
    let studio: Page;

    test.beforeAll(async ({ browser }) => {
      studioContext = await browser.newContext();
      studio = await studioContext.newPage();
      await expect(async () => {
        await studio.goto("/");
        await expect(
          studio.getByRole("heading", { name: "Open your writing studio" }),
        ).toBeVisible();
      }).toPass({ timeout: 60_000 });
      await studio.getByLabel("Password").fill(OWNER_PASSWORD);
      await studio.getByRole("button", { name: "Sign in" }).click();
      await expect(studio).toHaveURL(/\/projects$/);
    });

    test.afterAll(async () => {
      await studioContext.close();
    });

    test("auto-accepts chapters in reading order and preserves them after a stop", async () => {
      const projectId = await createProject(studio, "Whole Book Ledger");
      await typeChapter(studio, "# Chapter 1\n\nThe lighthouse keeper counted her debts aloud.");
      await studio.getByRole("button", { name: "Add Manuscript" }).click();
      await expect(studio.getByRole("textbox", { name: "Document title" })).toHaveValue(
        "Chapter 2",
      );
      await typeChapter(studio, "# Chapter 2\n\nThe tide repaid nothing and owed even less.");
      await studio.getByRole("button", { name: "Add Manuscript" }).click();
      await expect(studio.getByRole("textbox", { name: "Document title" })).toHaveValue(
        "Chapter 3",
      );
      await typeChapter(studio, "# Chapter 3\n\nEvery ledger closes on somebody eventually.");

      // All three authored chapters lack an accepted AI revision, so the loop
      // plans them in reading order (volume position, then chapter position).
      await studio.getByRole("button", { name: "Generate whole book" }).click();

      // At least two chapters must be drafted AND auto-accepted through the
      // synchronous proposal surface: their revision source is the closed
      // ai-accepted marker only the accept endpoint writes (#318).
      let earlyAccepted: ChapterDocument[] = [];
      await expect(async () => {
        earlyAccepted = (await studioChapters(studio, projectId)).filter(
          (chapter) => chapter.revision_source === "ai-accepted",
        );
        expect(earlyAccepted.length).toBeGreaterThanOrEqual(2);
      }).toPass({ timeout: 30_000 });
      // Reading order is pinned by position sorting inside studioChapters:
      // the first auto-accepted chapters are exactly chapters one and two.
      expect(earlyAccepted.slice(0, 2).map((chapter) => chapter.title)).toEqual([
        "Chapter 1",
        "Chapter 2",
      ]);
      for (const chapter of earlyAccepted) {
        await assertNarrativeProse(chapter.content_markdown);
      }
      // Sequential drafting produced distinct chapter prose, not one blob.
      expect(earlyAccepted[0]?.content_markdown).not.toBe(earlyAccepted[1]?.content_markdown);

      // Best-effort mid-run stop while chapter 3 is still being worked: the
      // deterministic provider may have settled the whole plan before this
      // click lands, and both outcomes must preserve the accepted work below.
      const stopButton = studio.getByRole("button", {
        name: "Stop generating",
      });
      try {
        await stopButton.click({ timeout: 500 });
      } catch {
        // The run completed before the stop could land; nothing to halt.
      }
      await expect(async () => {
        const outcome = (await studio.locator(".whole-book__outcome").textContent()) ?? "";
        expect(outcome).toMatch(/^(Stopped|Completed) — \d+ chapters? accepted/);
      }).toPass({ timeout: 30_000 });
      await expect(studio.getByText(/Generating chapter/)).toHaveCount(0);

      // Stop/completion preserves the accepted chapters byte-for-byte and
      // halts further generation: nothing changes after the terminal state.
      const readStates = async (): Promise<Array<[string, string]>> =>
        (await studioChapters(studio, projectId)).map((chapter) => [
          chapter.title,
          chapter.content_markdown,
        ]);
      const settledStates = await readStates();
      await studio.waitForTimeout(1_000);
      expect(await readStates()).toEqual(settledStates);
      for (const chapter of earlyAccepted) {
        const preserved = settledStates.find(([title]) => title === chapter.title);
        expect(preserved?.[1]).toBe(chapter.content_markdown);
      }

      // Jobs accounting reflects each accepted chapter: the store holds at
      // least one completed proposal job per auto-accepted chapter.
      const finalDocuments = await studioChapters(studio, projectId);
      const jobsResponse = await studio.request.get(`/api/projects/${projectId}/jobs`);
      const jobs = (await jobsResponse.json()) as {
        jobs: Array<{ kind: string; status: string }>;
      };
      const acceptedCount = finalDocuments.filter(
        (chapter) => chapter.revision_source === "ai-accepted",
      ).length;
      expect(acceptedCount).toBeGreaterThanOrEqual(2);
      expect(
        jobs.jobs.filter((job) => job.kind === "proposal" && job.status === "completed").length,
      ).toBeGreaterThanOrEqual(acceptedCount);
    });
  });
