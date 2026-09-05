import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import { createProject, studioChapters, typeChapter } from "../content_acceptance_helpers";

// Placement contract: this directory sorts after studio-ts.spec.ts and
// whole_book.spec.ts under Playwright's localeCompare file order, so the
// owner-setup file always starts in the first worker wave and the login
// polling below cannot starve it (see #467 PR notes).
//
// #467 reorder workflow (shell tasks 5.1/5.2): chapter placement through the
// Navigator's move commands, and volume placement/order through the API —
// the Studio UI exposes no volume create/move/reorder controls (see the #467
// triage), so the volume half is verified at the API level and judged by the
// shell projection the browser then renders.
test.describe
  .serial("#467 navigator reorder", () => {
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

    async function seedThreeChapters(title: string): Promise<string> {
      const projectId = await createProject(studio, title);
      for (const chapter of [1, 2, 3]) {
        if (chapter > 1) {
          await studio.getByRole("button", { name: "Add Manuscript" }).click();
          await expect(studio.getByRole("textbox", { name: "Document title" })).toHaveValue(
            `Chapter ${chapter}`,
          );
        }
        await typeChapter(studio, `# Chapter ${chapter}\n\nBell ${chapter} rang.`);
      }
      return projectId;
    }

    test("move commands reorder chapters in the navigator with busy naming and persistence", async () => {
      const projectId = await seedThreeChapters("Reorder Ledger");
      const chapterGroup = studio.locator(".studio-nav__document-group", {
        has: studio.getByRole("button", { name: "Add Manuscript" }),
      });
      const volumeRows = chapterGroup.locator(".volume-group");
      const rowTitles = () =>
        volumeRows
          .locator(".document-row")
          .evaluateAll((rows) =>
            rows.map((row) => (row instanceof HTMLElement ? row.getAttribute("aria-label") : "")),
          );
      await expect.poll(rowTitles).toEqual(["Chapter 1", "Chapter 2", "Chapter 3"]);
      await expect(volumeRows).toHaveCount(1);

      const reorderPath = `/api/projects/${projectId}/documents/reorder`;
      let reorderDelayMs = 0;
      await studio.route(`**${reorderPath}`, async (route) => {
        if (route.request().method() !== "PUT") {
          await route.fallback();
          return;
        }
        if (reorderDelayMs > 0) {
          await new Promise((resolve) => setTimeout(resolve, reorderDelayMs));
        }
        await route.continue();
      });

      // The reorder response carries summaries only — no body hydration at
      // response time (shell task 1.4's browser-visible half).
      reorderDelayMs = 700;
      const reorderResponsePromise = studio.waitForResponse(
        (response) =>
          new URL(response.url()).pathname === reorderPath && response.request().method() === "PUT",
      );
      await studio.getByRole("button", { name: "Move Chapter 3 up" }).click();
      const movingUp = studio.getByRole("button", { name: "Moving Chapter 3 up" });
      await expect(movingUp).toHaveAttribute("aria-busy", "true");
      await expect(studio.getByRole("button", { name: "Move Chapter 1 down" })).toBeDisabled();
      const reorderResponse = await reorderResponsePromise;
      const reorderBody = (await reorderResponse.json()) as {
        documents: Array<Record<string, unknown>>;
      };
      for (const summary of reorderBody.documents) {
        expect(summary).not.toHaveProperty("content_markdown");
        expect(summary).not.toHaveProperty("metadata");
        expect(typeof summary.current_revision_id).toBe("string");
      }
      await expect.poll(rowTitles).toEqual(["Chapter 1", "Chapter 3", "Chapter 2"]);
      await expect(studio.getByRole("button", { name: "Move Chapter 3 up" })).toBeEnabled();

      reorderDelayMs = 0;
      await studio.getByRole("button", { name: "Move Chapter 3 up" }).click();
      await expect.poll(rowTitles).toEqual(["Chapter 3", "Chapter 1", "Chapter 2"]);

      // The new order survives a reload and matches the persisted positions.
      await studio.reload();
      await expect.poll(rowTitles).toEqual(["Chapter 3", "Chapter 1", "Chapter 2"]);
      const ordinals = () =>
        volumeRows
          .locator(".document-row__ordinal")
          .evaluateAll((badges) => badges.map((badge) => badge.textContent?.trim() ?? ""));
      await expect.poll(ordinals).toEqual(["1", "2", "3"]);
      const chapters = await studioChapters(studio, projectId);
      expect(chapters.map((chapter) => chapter.title)).toEqual([
        "Chapter 3",
        "Chapter 1",
        "Chapter 2",
      ]);
      await studio.unroute(`**${reorderPath}`);
    });

    test("API volume placement and order project the navigator shell", async () => {
      const projectId = await seedThreeChapters("Volume Ledger");
      const csrfToken =
        (await studioContext.cookies()).find((cookie) => cookie.name === "novel_engine_csrf")
          ?.value ?? "";
      expect(csrfToken).not.toBe("");
      const csrfHeader = { "x-csrf-token": csrfToken };

      const shellResponse = await studio.request.get(`/api/projects/${projectId}`);
      expect(shellResponse.status()).toBe(200);
      const documents = (
        (await shellResponse.json()) as {
          documents: Array<{ id: string; title: string }>;
        }
      ).documents;
      const chapterTwo = documents.find((document) => document.title === "Chapter 2");
      expect(chapterTwo).toBeTruthy();

      const volumesResponse = await studio.request.get(`/api/projects/${projectId}/volumes`);
      expect(volumesResponse.status()).toBe(200);
      const initialVolumes = (
        (await volumesResponse.json()) as {
          volumes: Array<{ id: string; title: string }>;
        }
      ).volumes;
      expect(initialVolumes.map((volume) => volume.title)).toEqual(["Default Volume"]);

      const created = await studio.request.post(`/api/projects/${projectId}/volumes`, {
        data: { title: "Volume Two" },
        headers: csrfHeader,
      });
      expect(created.status()).toBe(201);
      const volumeTwoId = ((await created.json()) as { id: string }).id;

      const moved = await studio.request.put(
        `/api/projects/${projectId}/documents/${chapterTwo?.id}/volume`,
        { data: { volume_id: volumeTwoId }, headers: csrfHeader },
      );
      expect(moved.status(), await moved.text()).toBe(200);
      const movedDocument = (await moved.json()) as { volume_id: string };
      expect(movedDocument.volume_id).toBe(volumeTwoId);

      const reordered = await studio.request.put(`/api/projects/${projectId}/volumes/reorder`, {
        data: { volume_ids: [volumeTwoId, initialVolumes[0]?.id] },
        headers: csrfHeader,
      });
      expect(reordered.status(), await reordered.text()).toBe(200);
      const reorderedVolumes = (
        (await reordered.json()) as {
          volumes: Array<{ title: string }>;
        }
      ).volumes;
      expect(reorderedVolumes.map((volume) => volume.title)).toEqual([
        "Volume Two",
        "Default Volume",
      ]);

      // The browser consumes the same projection: headers in the reordered
      // volume sequence with Chapter 2 grouped under Volume Two.
      await studio.reload();
      const chapterGroup = studio.locator(".studio-nav__document-group", {
        has: studio.getByRole("button", { name: "Add Manuscript" }),
      });
      await expect(chapterGroup.locator(".studio-nav__volume-header")).toHaveText([
        "Volume Two",
        "Default Volume",
      ]);
      const volumeTwoGroup = chapterGroup.locator(".volume-group", { hasText: "Volume Two" });
      const defaultGroup = chapterGroup.locator(".volume-group", { hasText: "Default Volume" });
      await expect(
        volumeTwoGroup.getByRole("button", { name: "Chapter 2", exact: true }),
      ).toBeVisible();
      await expect(
        defaultGroup.getByRole("button", { name: "Chapter 1", exact: true }),
      ).toBeVisible();
      await expect(
        defaultGroup.getByRole("button", { name: "Chapter 3", exact: true }),
      ).toBeVisible();
      await expect(
        volumeTwoGroup.getByRole("button", { name: "Chapter 1", exact: true }),
      ).toHaveCount(0);
    });
  });
