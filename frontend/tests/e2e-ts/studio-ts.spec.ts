import { expect, type Page, type Route, test } from "@playwright/test";

import type { RevisionPage } from "../../src/app/types/studio";

/**
 * #274 acceptance: the studio UI served by the TS backend itself. The
 * playwright.ts.config.ts webServer boots the emitted CLI (`serve`) which
 * serves the built SPA from frontend/dist, so every assertion here runs
 * against the same-origin TS contract — novel_engine_* cookies, the unified
 * error envelope, and the SPA deep-link fallback — not the Python stack that
 * tests/e2e/studio.spec.ts still covers until the #277 cutover.
 */

// Assembled from fragments so no literal is bound to a credential-shaped
// name (same rule as the server suites' fixtureApiKey helper).
const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");

async function createProject(page: Page, title: string) {
  await page.goto("/");
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: /create project/i }).click();
  await expect(page).toHaveURL(/\/projects\/[^/]+\/manuscript/);
}

test("owner setup, editing, AI proposal accept, search, and deep links", async ({ page }) => {
  test.setTimeout(120_000);

  // Fresh store: the entry probe renders the unified setup form with the
  // username prefilled and the new-password autocomplete contract.
  await page.goto("/");
  const versionResponse = await page.request.get("/version");
  expect(versionResponse.ok()).toBe(true);
  const productIdentity = (await versionResponse.json()) as { name: string; version: string };
  await expect(page.locator(".entry__brand")).toContainText(productIdentity.name);
  await expect(page.locator(".entry footer")).toHaveText(
    `${productIdentity.name} ${productIdentity.version}`,
  );
  await expect(page.getByRole("heading", { name: "Create the local owner" })).toBeVisible();
  await expect(page.getByLabel("Username")).toHaveValue("author");
  await expect(page.locator('input[type="password"]')).toHaveAttribute(
    "autocomplete",
    "new-password",
  );

  // Single submit creates the owner and establishes the session.
  await page.getByLabel("Password").fill(OWNER_PASSWORD);
  await page.getByRole("button", { name: "Create owner" }).click();
  await expect(page).toHaveURL(/\/projects$/);

  await createProject(page, "The Glass Harbor");
  const saveStatus = page.locator(".studio-editor .editor__save-state");
  await expect(saveStatus).toHaveText(/saved/i);

  // Volume hierarchy (#312): the manuscript navigation groups chapters under
  // volume headers, and a fresh project starts with its default volume.
  const chapterGroup = page.locator(".studio-nav__document-group", {
    has: page.getByRole("button", { name: "Add Manuscript" }),
  });
  await expect(chapterGroup.locator(".studio-nav__volume-header")).toHaveText("Default Volume");
  await expect(
    chapterGroup.locator(".volume-group .document-row", {
      hasText: "Chapter 1",
    }),
  ).toBeVisible();

  // Carried naming behavior: generated document names per kind.
  await page.getByRole("button", { name: "Add Outline" }).click();
  await expect(page.getByRole("textbox", { name: "Document title" })).toHaveValue("Outline 1");
  await page.getByRole("button", { name: "Add Characters" }).click();
  await expect(page.getByRole("textbox", { name: "Document title" })).toHaveValue("Characters 1");
  await page.getByRole("button", { name: "Chapter 1", exact: true }).click();

  // Carried autosave behavior: edits persist through the debounced save.
  const editor = page.locator(".cm-content");
  await editor.click();
  // ControlOrMeta resolves to the platform's select-all chord: CodeMirror maps
  // plain Control+A on macOS to line-start movement, not selection.
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.type("# Chapter 1\n\nThe harbor bell rang twice.");
  await expect(saveStatus).toHaveText(/saved/i, { timeout: 10_000 });

  // Full-text search runs against the TS FTS5 surface over the author text.
  await page.getByLabel("Search project").fill("harbor");
  await page.getByLabel("Search project").press("Enter");
  const results = page.getByLabel("Search results");
  await expect(results).toBeVisible();
  await expect(results.getByRole("button", { name: /Chapter 1/i })).toBeVisible();

  // Deterministic mock provider: proposal then accept through the terminal
  // job contract of the TS backend. Accepting replaces the chapter content
  // with the generated draft.
  await page.getByPlaceholder("Describe the change or direction...").fill("Bring in the storm.");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Proposed Markdown")).toBeVisible();
  await page.getByRole("button", { name: "Accept" }).click();
  await expect(page.getByText("Proposed Markdown")).toHaveCount(0);
  await expect(saveStatus).toHaveText(/saved/i);

  // Deep-link fallback: reloading a client route must serve the SPA shell
  // from the TS server and restore the studio from the persisted session.
  const projectUrl = page.url();
  await page.goto(projectUrl);
  await expect(page.locator(".studio-editor")).toBeVisible();
  await expect(editor).toContainText("Chapter 1");
});

test("owner login issues novel_engine cookies and the editor renders the real error envelope", async ({
  browser,
}) => {
  test.setTimeout(120_000);
  const context = await browser.newContext();
  const first = await context.newPage();

  // The owner from the previous test is configured: the login form renders
  // (username prefilled, current-password autocomplete).
  await first.goto("/");
  await expect(first.getByRole("heading", { name: "Open your writing studio" })).toBeVisible();
  await expect(first.getByLabel("Username")).toHaveValue("author");
  await expect(first.locator('input[type="password"]')).toHaveAttribute(
    "autocomplete",
    "current-password",
  );
  await first.getByLabel("Password").fill(OWNER_PASSWORD);
  await first.getByRole("button", { name: "Sign in" }).click();
  await expect(first).toHaveURL(/\/projects$/);

  // Cookie contract: both novel_engine_* cookies exist end-to-end; every
  // write below succeeds through the double-submit header read from
  // novel_engine_csrf.
  const cookieNames = (await context.cookies()).map((cookie) => cookie.name);
  expect(cookieNames).toContain("novel_engine_session");
  expect(cookieNames).toContain("novel_engine_csrf");
  expect(cookieNames).not.toContain("novel_studio_csrf");

  await createProject(first, "Conflict fixture");
  const editor = first.locator(".cm-content");
  await editor.click();
  await first.keyboard.press("ControlOrMeta+a");
  await first.keyboard.type("First tab draft.");
  await expect(first.locator(".studio-editor .editor__save-state")).toHaveText(/saved/i, {
    timeout: 10_000,
  });

  // A second tab in the same session saves a newer revision while the first
  // tab still holds the stale base: the real TS backend answers 409 with the
  // unified envelope and the editor renders that envelope message.
  const second = await context.newPage();
  await second.goto(first.url());
  await expect(second.locator(".cm-content")).toContainText("First tab draft.");
  await second.locator(".cm-content").click();
  await second.keyboard.press("ControlOrMeta+a");
  await second.keyboard.type("Second tab wins.");
  await expect(second.locator(".studio-editor .editor__save-state")).toHaveText(/saved/i, {
    timeout: 10_000,
  });

  await editor.click();
  await first.keyboard.press("ControlOrMeta+a");
  await first.keyboard.type("Stale tab overwrite.");
  const conflict = first.locator(".editor-conflict");
  await expect(conflict).toBeVisible({ timeout: 10_000 });
  await expect(conflict).toContainText("Document changed since the requested base revision.");
  await expect(first.getByRole("button", { name: "Load latest (discard local)" })).toBeVisible();
  await expect(first.getByRole("button", { name: "Keep local and retry overwrite" })).toBeVisible();

  // Conflict recovery: load latest resolves onto the newest revision.
  await first.getByRole("button", { name: "Load latest (discard local)" }).click();
  await expect(first.locator(".studio-editor .editor__save-state")).toHaveText(/saved/i, {
    timeout: 10_000,
  });
  await expect(first.locator(".cm-content")).toContainText("Second tab wins.");

  await context.close();
});

test("History loads bounded revision pages and keeps keyboard retry state", async ({ page }) => {
  test.setTimeout(180_000);

  await page.goto("/");
  await page.getByLabel("Password").fill(OWNER_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/projects$/);

  await createProject(page, "Bounded History Ledger");
  const projectId = page.url().match(/\/projects\/([^/]+)\/manuscript/)?.[1];
  expect(projectId).toBeTruthy();

  const projectResponse = await page.request.get(`/api/projects/${projectId}`);
  expect(projectResponse.status(), await projectResponse.text()).toBe(200);
  const project = (await projectResponse.json()) as {
    documents: Array<{
      id: string;
      kind: string;
      title: string;
      current_revision_id: string;
    }>;
  };
  const chapter = project.documents.find(
    (document) => document.kind === "chapter" && document.title === "Chapter 1",
  );
  expect(chapter).toBeTruthy();

  const csrfToken = (await page.context().cookies()).find(
    (cookie) => cookie.name === "novel_engine_csrf",
  )?.value;
  expect(csrfToken).toBeTruthy();

  let baseRevisionId = chapter?.current_revision_id ?? "";
  for (let revision = 2; revision <= 51; revision += 1) {
    const saveResponse = await page.request.put(
      `/api/projects/${projectId}/documents/${chapter?.id}`,
      {
        data: {
          content_markdown: `# Chapter 1\n\nRevision ${revision}.`,
          base_revision_id: baseRevisionId,
        },
        headers: { "x-csrf-token": csrfToken ?? "" },
      },
    );
    expect(saveResponse.status(), await saveResponse.text()).toBe(200);
    baseRevisionId = ((await saveResponse.json()) as { current_revision_id: string })
      .current_revision_id;
  }

  const revisionsPath = `/api/projects/${projectId}/documents/${chapter?.id}/revisions`;
  const firstPageResponsePromise = page.waitForResponse((response) => {
    const requestUrl = new URL(response.url());
    return requestUrl.pathname === revisionsPath && !requestUrl.searchParams.has("cursor");
  });
  await page.goto(`/projects/${projectId}/history`);

  const firstPageResponse = await firstPageResponsePromise;
  const firstPageUrl = new URL(firstPageResponse.url());
  expect(firstPageResponse.status()).toBe(200);
  expect([...firstPageUrl.searchParams.entries()]).toEqual([["limit", "50"]]);
  const firstPage = (await firstPageResponse.json()) as RevisionPage;
  expect(firstPage.revisions).toHaveLength(50);
  expect(firstPage.revisions.map((revision) => revision.revision_number)).toEqual(
    Array.from({ length: 50 }, (_, index) => 51 - index),
  );
  expect(firstPage.next_cursor).toBeTruthy();

  const revisionRows = page.locator(".studio-inspector__revision-list article");
  await expect(revisionRows).toHaveCount(50);
  const loadOlder = page.getByRole("button", { name: "Load older revisions" });
  await expect(loadOlder).toBeVisible();

  const olderCursor = firstPage.next_cursor ?? "";
  const isExactOlderRequest = (url: URL) =>
    url.pathname === revisionsPath &&
    [...url.searchParams.entries()].length === 2 &&
    url.searchParams.get("limit") === "50" &&
    url.searchParams.get("cursor") === olderCursor;
  let interceptedOlderRequests = 0;
  const failOlderPage = async (route: Route) => {
    interceptedOlderRequests += 1;
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "SERVICE_UNAVAILABLE",
          message: "Revision history is temporarily unavailable.",
        },
      }),
    });
  };
  await page.route(isExactOlderRequest, failOlderPage);

  await loadOlder.focus();
  const failedPageResponse = page.waitForResponse(
    (response) => isExactOlderRequest(new URL(response.url())) && response.status() === 503,
  );
  await page.keyboard.press("Enter");
  await failedPageResponse;
  expect(interceptedOlderRequests).toBe(1);
  await expect(revisionRows).toHaveCount(50);
  await expect(page.getByRole("alert")).toContainText(
    "Revision history is temporarily unavailable.",
  );
  await expect(loadOlder).toBeFocused();

  await page.unroute(isExactOlderRequest, failOlderPage);
  const terminalPageResponsePromise = page.waitForResponse(
    (response) => isExactOlderRequest(new URL(response.url())) && response.status() === 200,
  );
  await page.keyboard.press("Enter");
  const terminalPageResponse = await terminalPageResponsePromise;
  const terminalPage = (await terminalPageResponse.json()) as RevisionPage;
  expect(terminalPage.revisions).toHaveLength(1);
  expect(terminalPage.revisions[0]?.revision_number).toBe(1);
  expect(terminalPage.next_cursor).toBeNull();

  await expect(revisionRows).toHaveCount(51);
  const expectedRowIds = [...firstPage.revisions, ...terminalPage.revisions].map(({ id }) =>
    id.slice(0, 8),
  );
  const renderedRowIds = await revisionRows
    .locator("small")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent?.split("·").at(-1)?.trim() ?? ""));
  expect(new Set(renderedRowIds).size).toBe(51);
  expect(renderedRowIds).toEqual(expectedRowIds);
  await expect(page.getByText("All revisions loaded", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Revision history" })).toBeFocused();
});
