import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import { createProject, studioChapters, typeChapter } from "../content_acceptance_helpers";

// Placement contract: this directory sorts after studio-ts.spec.ts and
// whole_book.spec.ts under Playwright's localeCompare file order, so the
// owner-setup file always starts in the first worker wave and the login
// polling below cannot starve it (see #467 PR notes).
//
// #467 project-switch workflow (shell task 5.1): open A, hold an unsaved
// Draft's autosave mid-flight, switch to B, then return to A through browser
// Back/Forward. DR-002: the explicit switch must rescue the pending Draft into
// A with exactly one write; no late save may fire or cross projects, and both
// projects must rehydrate cleanly.
test.describe
  .serial("#467 project switch", () => {
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

    test("switching projects rescues the pending Draft once with no late save crossing", async () => {
      const draftMarker = "UNSAVED DRAFT rescued from ledger A";
      const projectIdA = await createProject(studio, "Switch Ledger A");
      await typeChapter(studio, "# Chapter 1\n\nThe harbor bell of ledger A.");
      const projectUrlA = studio.url();

      const projectIdB = await createProject(studio, "Switch Ledger B");
      await typeChapter(studio, "# Chapter 1\n\nThe tide of ledger B.");
      const projectUrlB = studio.url();

      const savePuts = { a: 0, b: 0 };
      const countSavePut = (request: { method(): string; url(): string }) => {
        if (request.method() !== "PUT") return;
        const pathname = new URL(request.url()).pathname;
        if (pathname.startsWith(`/api/projects/${projectIdA}/documents/`)) savePuts.a += 1;
        if (pathname.startsWith(`/api/projects/${projectIdB}/documents/`)) savePuts.b += 1;
      };
      studio.on("request", countSavePut);

      // Re-open A by deep link and leave a genuinely unsaved Draft behind:
      // the editor enters the saving state with the 1.5s autosave debounce
      // still pending when the switch happens.
      await studio.goto(projectUrlA);
      await expect(studio.locator(".cm-content")).toContainText("ledger A");

      const editor = studio.locator(".cm-content");
      await editor.click();
      await studio.keyboard.press("ControlOrMeta+a");
      await studio.keyboard.type(draftMarker);
      await expect(editor).toContainText(draftMarker);
      const saveState = studio.locator(".studio-editor .editor__save-state");
      await expect(saveState).toHaveText(/saving/i);
      expect(savePuts).toEqual({ a: 0, b: 0 });

      // Switch to B through the library while the autosave debounce is still
      // pending. DR-002: the departure must rescue A's Draft with exactly one
      // PUT to A and none to B; waiting past the 1.5s window then proves no
      // late duplicate save fires at the network layer.
      await studio.getByRole("button", { name: "Back to projects" }).click();
      await expect(studio).toHaveURL(/\/projects$/);
      await expect.poll(() => savePuts.a, { message: "rescue write for A" }).toBe(1);
      expect(savePuts.b).toBe(0);
      // Starts-with: the same title also prefixes the row's delete command
      // (DR-018), which would otherwise make this locator ambiguous.
      await studio.getByRole("button", { name: /^Switch Ledger B/ }).click();
      await expect(studio).toHaveURL(new RegExp(`/projects/${projectIdB}/manuscript`));
      await expect(studio.locator(".cm-content")).toContainText("ledger B");
      await expect(studio.getByText(draftMarker)).toHaveCount(0);
      await studio.waitForTimeout(2_200);
      expect(savePuts).toEqual({ a: 1, b: 0 });

      // Return to A through Back/Forward: the rescue write committed the
      // Draft during the switch, so A rehydrates with the rescued text from
      // the server and re-entry fires no further save for A.
      await studio.goBack();
      await expect(studio).toHaveURL(/\/projects$/);
      await studio.goBack();
      await expect(studio).toHaveURL(new RegExp(`/projects/${projectIdA}/manuscript`));
      await expect(studio.getByRole("heading", { name: "Switch Ledger A" })).toBeVisible();
      await expect(studio.locator(".cm-content")).toContainText(draftMarker);
      await expect(studio.locator(".cm-content")).not.toContainText("The harbor bell of ledger A.");
      await expect(studio.locator(".studio-editor .editor__save-state")).toHaveText(/saved/i);
      // The switch rescue is A's only PUT; re-entry must not save again.
      expect(savePuts.a).toBe(1);
      const persistedA = (await studioChapters(studio, projectIdA)).map(
        (chapter) => chapter.content_markdown,
      );
      expect(persistedA).toEqual([draftMarker]);

      // Forward again lands on B with its own body intact; B was never
      // written by the switch.
      await studio.goForward();
      await expect(studio).toHaveURL(/\/projects$/);
      await studio.goForward();
      await expect(studio).toHaveURL(projectUrlB);
      await expect(studio.getByRole("heading", { name: "Switch Ledger B" })).toBeVisible();
      await expect(studio.locator(".cm-content")).toContainText("ledger B");
      expect(savePuts.b).toBe(0);

      studio.off("request", countSavePut);
    });
  });
