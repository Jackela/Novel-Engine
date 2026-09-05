import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import { createProject, typeChapter } from "../content_acceptance_helpers";

// Placement contract: this directory sorts after studio-ts.spec.ts and
// whole_book.spec.ts under Playwright's localeCompare file order, so the
// owner-setup file always starts in the first worker wave and the login
// polling below cannot starve it (see #467 PR notes).
//
// #467 cross-resource failure matrix, lazy-hydration coexistence, and
// Review/Export request isolation (shell tasks 4.1-4.4 browser halves): one
// blocked surface must fail alone with its own Retry, 401/404 route to
// Entry/library, hydration never hides tab roving, busy naming, retry focus,
// or the whole-book Stop control, and selecting Review or Export never
// requests the other.
test.describe
  .serial("#467 failure isolation and lazy hydration", () => {
    test.setTimeout(150_000);

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

    function serviceUnavailable(message: string) {
      return {
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "SERVICE_UNAVAILABLE", message },
        }),
      };
    }

    test("one blocked resource fails alone: shell, document, review, and export keep the others usable", async ({
      browser,
    }) => {
      const projectId = await createProject(studio, "Matrix Ledger");
      await typeChapter(studio, "# Chapter 1\n\nThe harbor bell rang twice.");
      const projectUrl = studio.url();
      const routeUrl = (inspector: string) => projectUrl.replace(/\/manuscript$/, `/${inspector}`);

      // (a) Shell failure renders the explicit project-level surface — never
      // a blank studio or an empty-document phantom.
      await studio.route(`**/api/projects/${projectId}`, async (handled) => {
        if (handled.request().method() !== "GET") {
          await handled.fallback();
          return;
        }
        await handled.fulfill(serviceUnavailable("The studio shelf is unreachable."));
      });
      await studio.goto(projectUrl);
      await expect(
        studio.getByRole("heading", { name: "Unable to open this project" }),
      ).toBeVisible();
      await expect(studio.getByRole("alert")).toContainText("The studio shelf is unreachable.");
      await expect(studio.getByRole("button", { name: "Try again" })).toBeVisible();
      await expect(studio.locator(".studio-editor")).toHaveCount(0);
      await expect(studio.getByText("Create a document to begin writing.")).toHaveCount(0);
      await studio.unroute(`**/api/projects/${projectId}`);
      await studio.getByRole("button", { name: "Try again" }).click();
      await expect(studio.locator(".cm-content")).toContainText("The harbor bell rang twice.");

      // (b) Current-document failure stays editor-scoped with its own Retry;
      // the shell-driven navigator and the Review surface keep working.
      await studio.route(`**/api/projects/${projectId}/documents/*`, async (handled) => {
        const request = handled.request();
        const isBodyRead =
          request.method() === "GET" && !new URL(request.url()).pathname.endsWith("/reorder");
        if (!isBodyRead) {
          await handled.fallback();
          return;
        }
        await handled.fulfill(serviceUnavailable("The chapter body is unreachable."));
      });
      await studio.goto(projectUrl);
      const documentError = studio.locator(".editor__empty[role=alert]");
      await expect(documentError).toContainText("Unable to open this document");
      await expect(documentError).toContainText("The chapter body is unreachable.");
      await expect(studio.getByRole("button", { name: "Retry document" })).toBeVisible();
      await expect(studio.getByText("Create a document to begin writing.")).toHaveCount(0);
      await expect(studio.locator(".studio-nav__volume-header")).toHaveText("Default Volume");
      await expect(studio.getByRole("button", { name: "Chapter 1", exact: true })).toBeVisible();
      await studio.getByRole("tab", { name: "Review" }).click();
      await expect(studio.getByText("No review findings. Run a review when ready.")).toBeVisible();
      await studio.unroute(`**/api/projects/${projectId}/documents/*`);
      await studio.getByRole("button", { name: "Retry document" }).click();
      await expect(studio.locator(".cm-content")).toContainText("The harbor bell rang twice.");

      // (c) Review-history failure renders a panel-local alert and retry
      // focus returns to the panel heading; no empty-history phantom.
      await studio.route(`**/api/projects/${projectId}/reviews`, async (handled) => {
        if (handled.request().method() !== "GET") {
          await handled.fallback();
          return;
        }
        await handled.fulfill(serviceUnavailable("Review history is temporarily unavailable."));
      });
      await studio.goto(routeUrl("review"));
      const reviewAlert = studio.locator(".studio-inspector__error[role=alert]").first();
      await expect(reviewAlert).toContainText("Review history is temporarily unavailable.");
      await expect(studio.getByText("No review findings. Run a review when ready.")).toHaveCount(0);
      await expect(studio.locator(".cm-content")).toContainText("The harbor bell rang twice.");
      await studio.unroute(`**/api/projects/${projectId}/reviews`);
      await studio.getByRole("button", { name: "Try again" }).first().click();
      await expect(studio.getByText("No review findings. Run a review when ready.")).toBeVisible();
      await expect(studio.getByRole("heading", { name: "Review findings" })).toBeFocused();

      // (d) Export-history failure behaves identically and keeps the editor.
      await studio.route(`**/api/projects/${projectId}/exports`, async (handled) => {
        if (handled.request().method() !== "GET") {
          await handled.fallback();
          return;
        }
        await handled.fulfill(serviceUnavailable("Export history is temporarily unavailable."));
      });
      await studio.goto(routeUrl("export"));
      const exportAlert = studio.locator(".export-history .studio-inspector__error[role=alert]");
      await expect(exportAlert).toContainText("Export history is temporarily unavailable.");
      await expect(studio.getByText("No exports yet.")).toHaveCount(0);
      await expect(studio.locator(".cm-content")).toContainText("The harbor bell rang twice.");
      await studio.getByRole("tab", { name: "Review" }).click();
      await expect(studio.getByText("No review findings. Run a review when ready.")).toBeVisible();
      await studio.unroute(`**/api/projects/${projectId}/exports`);
      // Lazy panels unmount when unselected and never auto-refetch on return
      // (a held failure is not idle), so the recovery path is: reselect the
      // Export tab — its failure state persists — then retry the history read.
      await studio.getByRole("tab", { name: "Export" }).click();
      await expect(exportAlert).toBeVisible();
      await studio.locator(".export-history").getByRole("button", { name: "Try again" }).click();
      await expect(studio.getByText("No exports yet.")).toBeVisible();

      // (e) Shell 404 routes to the project library; resource 401 routes to
      // Entry (shell task 4.3's navigation half).
      const csrfToken =
        (await studioContext.cookies()).find((cookie) => cookie.name === "novel_engine_csrf")
          ?.value ?? "";
      const probe = await studio.request.post("/api/projects", {
        data: { title: "Session Probe Ledger", description: "" },
        headers: { "x-csrf-token": csrfToken },
      });
      expect(probe.status()).toBe(201);
      const probeId = ((await probe.json()) as { id: string }).id;
      const expiredContext = await browser.newContext();
      const expired = await expiredContext.newPage();
      await expired.goto(`/projects/${probeId}/manuscript`);
      await expect(expired).toHaveURL(/\/$/);
      await expect(
        expired.getByRole("heading", { name: "Open your writing studio" }),
      ).toBeVisible();
      await expiredContext.close();

      const removal = await studio.request.delete(`/api/projects/${projectId}`, {
        headers: { "x-csrf-token": csrfToken },
      });
      expect(removal.status()).toBe(204);
      await studio.goto(projectUrl);
      await expect(studio).toHaveURL(/\/projects$/);
      await expect(studio.getByRole("heading", { name: "Projects" })).toBeVisible();
    });

    test("tab roving, busy naming, and whole-book Stop survive lazy hydration", async () => {
      const projectId = await createProject(studio, "Lazy Ledger");
      await typeChapter(studio, "# Chapter 1\n\nThe harbor bell rang twice.");
      await studio.getByRole("button", { name: "Add Manuscript" }).click();
      await expect(studio.getByRole("textbox", { name: "Document title" })).toHaveValue(
        "Chapter 2",
      );
      await typeChapter(studio, "# Chapter 2\n\nThe tide repaid nothing.");

      // Hold the review hydration open so the pending window is deterministic.
      let releaseReviews: (() => void) | undefined;
      const reviewsHeld = new Promise<void>((resolve) => {
        releaseReviews = resolve;
      });
      await studio.route(`**/api/projects/${projectId}/reviews`, async (handled) => {
        if (handled.request().method() !== "GET") {
          await handled.fallback();
          return;
        }
        await reviewsHeld;
        await handled.continue();
      });

      const tablist = studio.getByRole("tablist", { name: "Inspector panels" });
      const reviewTab = tablist.getByRole("tab", { name: "Review" });
      await studio.goto(`/projects/${projectId}/review`);
      await expect(studio.getByText("Loading review history…")).toBeVisible();
      await expect(
        studio.locator('div[role="tabpanel"]:not([hidden]) .studio-inspector__panel'),
      ).toHaveAttribute("aria-busy", "true");

      // Keyboard roving keeps working while hydration is pending (4.4).
      await reviewTab.focus();
      await studio.keyboard.press("ArrowRight");
      await expect(studio).toHaveURL(/\/history$/);
      await expect(tablist.getByRole("tab", { name: "History" })).toBeFocused();
      await expect(tablist.getByRole("tab", { name: "History" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
      await studio.keyboard.press("ArrowLeft");
      await expect(studio).toHaveURL(/\/review$/);
      await expect(reviewTab).toBeFocused();
      await expect(studio.getByText("Loading review history…")).toBeVisible();
      await studio.keyboard.press("Home");
      await expect(studio).toHaveURL(/\/manuscript$/);
      await studio.keyboard.press("End");
      await expect(studio).toHaveURL(/\/manuscript\?inspector=usage$/);

      // Freeze the first whole-book stream so the run is observably running,
      // then prove Stop stays visible while the lazy panels hydrate.
      let releaseStream: (() => void) | undefined;
      const streamHeld = new Promise<void>((resolve) => {
        releaseStream = resolve;
      });
      let streamHoldsLeft = 1;
      await studio.route("**/ai-proposals/stream", async (handled) => {
        if (streamHoldsLeft > 0) {
          streamHoldsLeft -= 1;
          await streamHeld;
        }
        await handled.continue();
      });
      await studio.keyboard.press("Home");
      await studio.getByRole("button", { name: "Generate whole book" }).click();
      await expect(studio.getByText("Generating chapter 1 of 2…")).toBeVisible();
      await reviewTab.click();
      await expect(studio.getByText("Loading review history…")).toBeVisible();
      await expect(studio.getByRole("button", { name: "Stop generating" })).toBeVisible();
      await tablist.getByRole("tab", { name: "Export" }).click();
      await expect(studio.getByText("No exports yet.")).toBeVisible();
      await expect(studio.getByRole("button", { name: "Stop generating" })).toBeVisible();

      // Release the hydration: the review history lands while the run stops
      // being observable only through its terminal outcome.
      await reviewTab.click();
      await expect(studio.getByText("Loading review history…")).toBeVisible();
      releaseReviews?.();
      await expect(studio.getByText("No review findings. Run a review when ready.")).toBeVisible();
      releaseStream?.();
      await expect(studio.locator(".whole-book__outcome")).toContainText(
        /^(Stopped|Completed) — \d+ chapters? accepted/,
        { timeout: 30_000 },
      );
      await expect(studio.getByText(/Generating chapter/)).toHaveCount(0);
      await expect(studio.getByRole("button", { name: "Stop generating" })).toHaveCount(0);
      await studio.unroute(`**/api/projects/${projectId}/reviews`);
      await studio.unroute("**/ai-proposals/stream");
    });

    test("review and export request isolation across direct navigation and Back/Forward", async () => {
      const projectId = await createProject(studio, "Isolation Ledger");
      await typeChapter(studio, "# Chapter 1\n\nThe harbor bell rang twice.");
      const base = studio.url().replace(/\/manuscript$/, "");

      let reviewReads = 0;
      let exportReads = 0;
      const countReads = (request: { method(): string; url(): string }) => {
        if (request.method() !== "GET") return;
        const pathname = new URL(request.url()).pathname;
        if (pathname === `/api/projects/${projectId}/reviews`) reviewReads += 1;
        if (pathname === `/api/projects/${projectId}/exports`) exportReads += 1;
      };
      studio.on("request", countReads);

      // Bootstrap on an authoring route reads neither lazy history (4.1).
      await studio.goto(`${base}/manuscript`);
      await expect(studio.locator(".cm-content")).toContainText("harbor bell");
      expect([reviewReads, exportReads]).toEqual([0, 0]);

      await studio.goto(`${base}/export`);
      await expect(studio.getByText("No exports yet.")).toBeVisible();
      expect([reviewReads, exportReads]).toEqual([0, 1]);

      // Direct navigation to Review never requests the Export surface.
      await studio.goto(`${base}/review`);
      await expect(studio.getByText("No review findings. Run a review when ready.")).toBeVisible();
      expect([reviewReads, exportReads]).toEqual([1, 1]);

      // Back/Forward rehydrate only the route-selected panel.
      await studio.goBack();
      await expect(studio.getByText("No exports yet.")).toBeVisible();
      expect([reviewReads, exportReads]).toEqual([1, 2]);
      await studio.goForward();
      await expect(studio.getByText("No review findings. Run a review when ready.")).toBeVisible();
      expect([reviewReads, exportReads]).toEqual([2, 2]);

      studio.off("request", countReads);
    });
  });
