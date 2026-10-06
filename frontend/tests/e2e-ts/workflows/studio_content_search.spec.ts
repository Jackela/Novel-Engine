import { type APIResponse, type BrowserContext, expect, type Page, test } from "@playwright/test";

import { createProject, studioChapters, typeChapter } from "../content_acceptance_helpers";

/**
 * #276 content-level acceptance, search and envelope half (split from
 * studio_content.spec.ts at the file-size gate): operator-safe FTS5
 * reduction plus the unified 409/CSRF envelopes against the TS stack. The
 * export-fidelity and project-deletion halves (and their serialized export
 * activity) stay in studio_content.spec.ts.
 *
 * Placement contract: this directory sorts after studio-ts.spec.ts under
 * Playwright's localeCompare file order, so the owner-setup file always
 * starts in the first worker wave even with two CI workers; a second
 * studio_content_*.spec.ts file at the root would have pushed the setup
 * file into the second wave while both content waiters starve (see #467
 * PR notes).
 */

interface EnvelopeBody {
  error: { code: string; message: string; details: Record<string, unknown> };
}

async function expectApiError(response: APIResponse, status: number, code: string) {
  expect(response.status()).toBe(status);
  const body = (await response.json()) as EnvelopeBody;
  expect(body.error.code).toBe(code);
  expect(typeof body.error.message).toBe("string");
  return body;
}

test.describe
  .serial("#276 content acceptance — search and envelopes", () => {
    test.setTimeout(120_000);

    // Same fragment-assembled credential as studio-ts.spec.ts, which owns the
    // one-time owner setup on the shared store this suite logs into.
    const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");

    let studioContext: BrowserContext;
    let studio: Page;
    let csrfToken: string;

    test.beforeAll(async ({ browser }) => {
      studioContext = await browser.newContext();
      studio = await studioContext.newPage();
      // The entry page probes setup once on mount, so poll by reloading until
      // the sibling suite's one-time owner setup has flipped the heading.
      await expect(async () => {
        await studio.goto("/");
        await expect(
          studio.getByRole("heading", { name: "Open your writing studio" }),
        ).toBeVisible();
      }).toPass({ timeout: 60_000 });
      await studio.getByLabel("Password").fill(OWNER_PASSWORD);
      await studio.getByRole("button", { name: "Sign in" }).click();
      await expect(studio).toHaveURL(/\/projects$/);

      // Cookie contract restated for this suite's session: the double-submit
      // pair is novel_engine_* and no legacy cookie survives.
      const cookieNames = (await studioContext.cookies()).map((cookie) => cookie.name);
      expect(cookieNames).toContain("novel_engine_session");
      expect(cookieNames).not.toContain("novel_studio_csrf");
      csrfToken =
        (await studioContext.cookies()).find((cookie) => cookie.name === "novel_engine_csrf")
          ?.value ?? "";
      expect(csrfToken).not.toBe("");
    });

    test.afterAll(async () => {
      await studioContext.close();
    });

    test("search reduces operators to literals; conflicts and csrf answer the unified envelope", async () => {
      const projectId = await createProject(studio, "Signal Ledger");
      await typeChapter(
        studio,
        "# Chapter 1\n\nThe harbor bell rang twice. Nobody answered the second time.",
      );

      // Punctuation-separated terms all exist in the chapter: a hit through
      // both the API and the browser flow.
      const punctuated = await studio.request.get(
        `/api/projects/${projectId}/search?q=${encodeURIComponent("harbor.bell,twice")}`,
      );
      const punctuatedBody = (await punctuated.json()) as {
        results: Array<{ document_id: string; title: string }>;
      };
      expect(punctuatedBody.results).toHaveLength(1);
      expect(punctuatedBody.results[0]?.title).toBe("Chapter 1");
      const searchBox = studio.getByLabel("Search project");
      await searchBox.fill("harbor.bell,twice");
      await searchBox.press("Enter");
      await expect(studio.getByLabel("Search results")).toBeVisible();

      // FTS5 operators become literal quoted tokens: "harbor OR bell" reduces
      // to harbor AND or AND bell, and the chapter has no standalone "or" — so
      // raw operator passthrough would have matched, the reduction must not.
      const operated = await studio.request.get(
        `/api/projects/${projectId}/search?q=${encodeURIComponent("harbor OR bell")}`,
      );
      expect(((await operated.json()) as { results: unknown[] }).results).toHaveLength(0);
      await searchBox.fill("harbor OR bell");
      await searchBox.press("Enter");
      // The previous query's results are still on screen, so this auto-retry
      // assertion cannot pass early: the section must first disappear once the
      // safely-reduced query returns its empty result set.
      await expect(studio.getByLabel("Search results")).toHaveCount(0);

      // Stale base revision: 409 with the unified envelope and the winner.
      const chapter = (await studioChapters(studio, projectId))[0];
      const history = (await (
        await studio.request.get(`/api/projects/${projectId}/documents/${chapter?.id}/revisions`)
      ).json()) as { revisions: Array<{ id: string }> };
      const conflict = await studio.request.put(
        `/api/projects/${projectId}/documents/${chapter?.id}`,
        {
          data: {
            content_markdown: "Stale tab write.",
            base_revision_id: history.revisions.find(
              (revision) => revision.id !== chapter?.current_revision_id,
            )?.id,
          },
          headers: { "x-csrf-token": csrfToken },
        },
      );
      const conflictBody = await expectApiError(conflict, 409, "REVISION_CONFLICT");
      expect(conflictBody.error.details.current_revision_id).toBe(chapter?.current_revision_id);

      // CSRF double-submit: a session-authenticated write without the header is
      // rejected, and a tampered token is rejected separately.
      const missingToken = await studio.request.post("/api/projects", {
        data: { title: "No token ledger" },
      });
      await expectApiError(missingToken, 403, "CSRF_TOKEN_MISSING");
      const tamperedToken = await studio.request.post("/api/projects", {
        data: { title: "Tampered token ledger" },
        headers: { "x-csrf-token": `${csrfToken}-tampered` },
      });
      await expectApiError(tamperedToken, 403, "CSRF_TOKEN_INVALID");
    });
  });
