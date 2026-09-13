import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import { createProject, studioChapters, typeChapter } from "../content_acceptance_helpers";

// Placement contract: this directory sorts after studio-ts.spec.ts and
// whole_book.spec.ts under Playwright's localeCompare file order, so the
// owner-setup file always starts in the first worker wave and the login
// polling below cannot starve it (see #467 PR notes).
//
// #481 Navigator row-command workflows: document deletion with its inline
// confirmation (cancel, Escape, busy naming, focus fallback, snapshot-conflict
// refusal surfaced inline with recovery) and chapter volume placement (shell
// update from the response, persistence, capacity refusal with retry).
test.describe
  .serial("#481 navigator row commands", () => {
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

    async function seedChapters(title: string): Promise<string> {
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

    function chapterGroup() {
      return studio.locator(".studio-nav__document-group", {
        has: studio.getByRole("button", { name: "Add Manuscript" }),
      });
    }

    /**
     * One volume's group scoped by its header. `hasText` alone is ambiguous
     * now that every row's placement select lists the other volumes' titles
     * as options inside its own group (#481).
     */
    function volumeGroup(group: ReturnType<typeof chapterGroup>, title: string) {
      return group.locator(".volume-group").filter({
        has: studio.locator(".studio-nav__volume-header", { hasText: title }),
      });
    }

    async function csrfHeader(): Promise<{ "x-csrf-token": string }> {
      const csrfToken =
        (await studioContext.cookies()).find((cookie) => cookie.name === "novel_engine_csrf")
          ?.value ?? "";
      expect(csrfToken).not.toBe("");
      return { "x-csrf-token": csrfToken };
    }

    test("delete confirms, cancels, falls back selection, and moves focus to a survivor", async () => {
      const projectId = await seedChapters("Delete Ledger");

      // Escape cancels the confirmation and leaves the document in place.
      await studio.getByRole("button", { name: "Delete Chapter 1" }).click();
      const strip = studio.getByRole("group", { name: "Delete Chapter 1 confirmation" });
      await expect(strip).toBeVisible();
      await expect(strip).toContainText("Permanently delete Chapter 1?");
      await expect(strip).toContainText("Unsaved changes are lost");
      await expect(strip.getByRole("button", { name: "Confirm delete Chapter 1" })).toBeFocused();
      await studio.keyboard.press("Escape");
      await expect(strip).toBeHidden();
      await expect(studio.getByRole("button", { name: "Delete Chapter 1" })).toBeFocused();

      // The cancelled command never fired; the confirm path deletes exactly
      // the named document and hands focus to the surviving neighbor row
      // (the row that took the deleted one's place in reading order).
      await studio.getByRole("button", { name: "Delete Chapter 2" }).click();
      await studio.getByRole("button", { name: "Confirm delete Chapter 2" }).click();
      await expect(studio.getByRole("button", { name: "Chapter 2", exact: true })).toHaveCount(0);
      await expect(studio.getByRole("button", { name: "Chapter 3", exact: true })).toBeFocused();
      const chapters = await studioChapters(studio, projectId);
      expect(chapters.map((chapter) => chapter.title)).toEqual(["Chapter 1", "Chapter 3"]);

      // The removal survives a reload — SQLite is the authority.
      await studio.reload();
      await expect(studio.getByRole("button", { name: "Chapter 2", exact: true })).toHaveCount(0);
    });

    test("delete surfaces a snapshot-conflict refusal inline and recovers on retry", async () => {
      const projectId = await seedChapters("Snapshot Ledger");
      const deletePath = `/api/projects/${projectId}/documents/`;
      let refuseOnce = true;
      await studio.route(`**${deletePath}**`, async (route) => {
        if (route.request().method() === "DELETE" && refuseOnce) {
          refuseOnce = false;
          await route.fulfill({
            status: 409,
            contentType: "application/json",
            body: JSON.stringify({
              error: {
                code: "SNAPSHOT_CONFLICT",
                message: "Document is referenced by an immutable snapshot.",
              },
            }),
          });
          return;
        }
        await route.fallback();
      });

      await studio.getByRole("button", { name: "Delete Chapter 1" }).click();
      await studio.getByRole("button", { name: "Confirm delete Chapter 1" }).click();
      const refusal = studio.getByRole("alert").filter({
        hasText: "Document is referenced by an immutable snapshot.",
      });
      await expect(refusal).toBeVisible();
      // The refused document stays in the navigator and remains deletable.
      await expect(studio.getByRole("button", { name: "Chapter 1", exact: true })).toBeVisible();

      await studio.getByRole("button", { name: "Confirm delete Chapter 1" }).click();
      await expect(studio.getByRole("button", { name: "Chapter 1", exact: true })).toHaveCount(0);
      await studio.unroute(`**${deletePath}**`);
    });

    test("volume placement moves the chapter between navigator groups and persists", async () => {
      const projectId = await seedChapters("Placement Ledger");
      const created = await studio.request.post(`/api/projects/${projectId}/volumes`, {
        data: { title: "Volume Two" },
        headers: await csrfHeader(),
      });
      expect(created.status(), await created.text()).toBe(201);
      await studio.reload();

      const group = chapterGroup();
      const placePath = `/api/projects/${projectId}/documents/`;
      let placeDelayMs = 0;
      await studio.route(`**${placePath}**/volume`, async (route) => {
        if (route.request().method() !== "PUT") {
          await route.fallback();
          return;
        }
        if (placeDelayMs > 0) {
          await new Promise((resolve) => setTimeout(resolve, placeDelayMs));
        }
        await route.continue();
      });

      // The chapter's current volume is never offered as a target.
      const select = studio.getByRole("combobox", { name: "Place Chapter 2 in volume" });
      const optionTitles = await select
        .locator("option")
        .evaluateAll((options) =>
          options.map((option) => (option instanceof HTMLOptionElement ? option.textContent : "")),
        );
      expect(optionTitles).toEqual(["Move to volume…", "Volume Two"]);

      placeDelayMs = 700;
      await select.selectOption({ label: "Volume Two" });
      await expect(
        studio.getByRole("combobox", { name: "Placing Chapter 2 in Volume Two" }),
      ).toBeDisabled();
      await expect(studio.getByRole("button", { name: "Move Chapter 2 up" })).toBeDisabled();

      const volumeTwoGroup = volumeGroup(group, "Volume Two");
      const defaultGroup = volumeGroup(group, "Default Volume");
      await expect(
        volumeTwoGroup.getByRole("button", { name: "Chapter 2", exact: true }),
      ).toBeVisible();
      await expect(
        defaultGroup.getByRole("button", { name: "Chapter 2", exact: true }),
      ).toHaveCount(0);

      // The shell update survives a reload and matches persisted placement:
      // shell document order is reading order (volume order, then in-volume
      // order), so Default Volume keeps Chapters 1 and 3 before Volume Two's
      // tail placement of Chapter 2.
      await studio.reload();
      await expect(
        volumeGroup(chapterGroup(), "Volume Two").getByRole("button", {
          name: "Chapter 2",
          exact: true,
        }),
      ).toBeVisible();
      const shellResponse = await studio.request.get(`/api/projects/${projectId}`);
      expect(shellResponse.status()).toBe(200);
      const shell = (await shellResponse.json()) as {
        documents: Array<{ kind: string; title: string }>;
      };
      expect(shell.documents.map((document) => document.title)).toEqual([
        "Chapter 1",
        "Chapter 3",
        "Chapter 2",
      ]);
      await studio.unroute(`**${placePath}**/volume`);
    });

    test("volume placement surfaces a capacity refusal inline and retries into the target", async () => {
      const projectId = await seedChapters("Capacity Ledger");
      await studio.request.post(`/api/projects/${projectId}/volumes`, {
        data: { title: "Full Volume" },
        headers: await csrfHeader(),
      });
      await studio.reload();

      const placePath = `/api/projects/${projectId}/documents/`;
      let refuseOnce = true;
      await studio.route(`**${placePath}**/volume`, async (route) => {
        if (route.request().method() === "PUT" && refuseOnce) {
          refuseOnce = false;
          await route.fulfill({
            status: 422,
            contentType: "application/json",
            body: JSON.stringify({
              error: {
                code: "STRUCTURE_CAPACITY_EXCEEDED",
                message: "That volume is full.",
                details: { resource: "volume_chapters", limit: 2000, observed: 2000 },
              },
            }),
          });
          return;
        }
        await route.fallback();
      });

      await studio
        .getByRole("combobox", { name: "Place Chapter 3 in volume" })
        .selectOption({ label: "Full Volume" });
      const refusal = studio.getByRole("alert").filter({
        hasText: "That volume is full. volume_chapters limit is 2000.",
      });
      await expect(refusal).toBeVisible();
      // The refused chapter stays in its current volume.
      await expect(
        volumeGroup(chapterGroup(), "Default Volume").getByRole("button", {
          name: "Chapter 3",
          exact: true,
        }),
      ).toBeVisible();

      // Re-issuing the placement is the retry and now succeeds.
      await studio
        .getByRole("combobox", { name: "Place Chapter 3 in volume" })
        .selectOption({ label: "Full Volume" });
      await expect(
        volumeGroup(chapterGroup(), "Full Volume").getByRole("button", {
          name: "Chapter 3",
          exact: true,
        }),
      ).toBeVisible();
      await studio.unroute(`**${placePath}**/volume`);
    });
  });
