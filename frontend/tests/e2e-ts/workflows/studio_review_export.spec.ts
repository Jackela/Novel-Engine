import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import { createProject, typeChapter } from "../content_acceptance_helpers";

// Placement contract: this directory sorts after studio-ts.spec.ts and
// whole_book.spec.ts under Playwright's localeCompare file order, so the
// owner-setup file always starts in the first worker wave and the login
// polling below cannot starve it (see #467 PR notes).
//
// #467 Review-run and Export-failure workflows (shell tasks 4.1/5.1/5.2):
// the mock provider's review run with its busy naming and finding rendering,
// and an export failure whose Retry recovers without blanking any other
// surface. Request isolation between the two lazy histories is asserted at
// the network layer.
test.describe
  .serial("#467 review and export workflows", () => {
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

    test("review runs through the mock provider with busy naming and never requests exports", async () => {
      const projectId = await createProject(studio, "Review Ledger");
      await typeChapter(studio, "# Chapter 1\n\nThe harbor bell rang twice.");

      let reviewReads = 0;
      let exportReads = 0;
      const countReads = (request: { method(): string; url(): string }) => {
        if (request.method() !== "GET") return;
        const pathname = new URL(request.url()).pathname;
        if (pathname === `/api/projects/${projectId}/reviews`) reviewReads += 1;
        if (pathname === `/api/projects/${projectId}/exports`) exportReads += 1;
      };
      studio.on("request", countReads);

      // Direct navigation activates only the route-selected panel (4.1).
      await studio.goto(`/projects/${projectId}/review`);
      await expect(studio.getByRole("heading", { name: "Review findings" })).toBeVisible();
      await expect(studio.getByText("No review findings. Run a review when ready.")).toBeVisible();
      expect(reviewReads).toBe(1);
      expect(exportReads).toBe(0);

      // Busy naming while the review job runs: the run stays observable.
      await studio.route(`**/api/projects/${projectId}/reviews`, async (route) => {
        if (route.request().method() !== "POST") {
          await route.fallback();
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 700));
        await route.continue();
      });
      await studio.getByRole("button", { name: "Run review" }).click();
      await expect(studio.getByRole("button", { name: "Running review" })).toHaveAttribute(
        "aria-busy",
        "true",
      );
      await expect(studio.getByText("Running review…")).toBeVisible();

      // The deterministic provider flags the thin chapter as a pacing warning.
      const issue = studio.locator(".studio-inspector__review-issue--warning").first();
      await expect(issue).toBeVisible();
      await expect(issue.locator("header strong")).toHaveText("pacing");
      await expect(issue.locator("header span")).toHaveText("warning");
      await expect(issue.locator("p")).toContainText(/Chapter 1 contains only \d+ words/);
      await expect(issue.locator("small").first()).toContainText("Develop the scene turn");
      await expect(studio.getByRole("button", { name: "Run review" })).toBeEnabled();

      // The run refreshed the assessment list; the Export surface was never
      // requested while Review stayed selected.
      expect(reviewReads).toBe(2);
      expect(exportReads).toBe(0);
      await studio.unroute(`**/api/projects/${projectId}/reviews`);
      studio.off("request", countReads);
    });

    test("export failure renders a panel-local Retry that recovers without blanking other surfaces", async () => {
      const projectId = await createProject(studio, "Export Failure Ledger");
      await typeChapter(studio, "# Chapter 1\n\nThe harbor bell rang twice.");

      await studio.getByRole("tab", { name: "Export" }).click();
      await expect(studio).toHaveURL(/\/export$/);
      await expect(studio.getByText("No exports yet.")).toBeVisible();

      const exportsPath = `**/api/projects/${projectId}/exports`;
      await studio.route(exportsPath, async (route) => {
        if (route.request().method() !== "POST") {
          await route.fallback();
          return;
        }
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "SERVICE_UNAVAILABLE",
              message: "Export service is temporarily down.",
            },
          }),
        });
      });

      await studio.getByRole("button", { name: /^Markdown/ }).click();
      const failureAlert = studio.locator(".export-panel .studio-inspector__error[role=alert]");
      await expect(failureAlert).toContainText("Export service is temporarily down.");
      const retryExport = studio.getByRole("button", { name: "Retry markdown export" });
      await expect(retryExport).toBeVisible();

      // No cross-resource blanking: editor, navigator, and the Review surface
      // stay usable while the Export action holds its failure.
      await expect(studio.locator(".cm-content")).toContainText("The harbor bell rang twice.");
      await expect(studio.getByRole("button", { name: "Chapter 1", exact: true })).toBeVisible();
      await studio.getByRole("tab", { name: "Review" }).click();
      await expect(studio.getByText("No review findings. Run a review when ready.")).toBeVisible();
      await studio.getByRole("tab", { name: "Export" }).click();
      await expect(failureAlert).toBeVisible();

      await studio.unroute(exportsPath);
      const [download] = await Promise.all([studio.waitForEvent("download"), retryExport.click()]);
      expect(download.suggestedFilename()).toBe("Export Failure Ledger.md");
      await expect(failureAlert).toHaveCount(0);
      const historyRow = studio.locator(".studio-inspector__export-row");
      await expect(historyRow).toHaveCount(1);
      await expect(historyRow).toContainText("MARKDOWN");
    });
  });
