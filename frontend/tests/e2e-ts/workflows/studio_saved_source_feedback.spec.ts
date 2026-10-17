import { readFile } from "node:fs/promises";

import { type BrowserContext, expect, type Page, type Route, test } from "@playwright/test";

import { createProject, typeChapter } from "../project_document_helpers";

const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");
const SAVED_MARKER = "SAVED_SOURCE_BOUNDARY";
const UNSAVED_MARKER = "UNSAVED_DRAFT_BOUNDARY";

/** Reads the actual downloaded artifact; no export response is stubbed. */
async function downloadMarkdown(page: Page): Promise<string> {
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /^Markdown/ }).click(),
  ]);
  const path = await download.path();
  if (path === null) throw new Error("Markdown export produced no downloaded artifact.");
  return readFile(path, "utf8");
}

// Like the sibling workflow specs, wait for studio-ts.spec.ts to create the
// shared owner. This file never competes with that file's initial setup flow.
test.describe("saved source feedback", () => {
  let context: BrowserContext;
  let studio: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    studio = await context.newPage();
    await expect(async () => {
      await studio.goto("/");
      await expect(studio.getByRole("heading", { name: "Open your writing studio" })).toBeVisible();
    }).toPass({ timeout: 45_000 });
    await studio.getByLabel("Password").fill(OWNER_PASSWORD);
    await studio.getByRole("button", { name: "Sign in" }).click();
    await expect(studio).toHaveURL(/\/projects$/);
  });

  test.afterAll(async () => {
    await context?.close();
  });

  test("review and export keep using saved chapters while a local draft is pending or rejected", async () => {
    const projectId = await createProject(studio, "Saved source regression");
    const saved = `# Chapter 1\n\n${SAVED_MARKER}\n\n${"雨停以后，船工沿着旧码头缓缓前行，逐一核对船上的灯火，等待远处传来清晰的回声。".repeat(24)}`;
    await typeChapter(studio, saved);
    const saveStatus = studio.locator(".studio-editor .editor__save-state");
    await expect(saveStatus).toHaveText(/^saved$/i);
    // The current Document endpoint is discovered from the real shell; no
    // persistence internals or project-wide route glob are needed.
    const shell = await studio.request.get(`/api/projects/${projectId}`);
    expect(shell.ok()).toBe(true);
    const project = (await shell.json()) as { documents: Array<{ id: string; kind: string }> };
    const chapterId = project.documents.find((item) => item.kind === "chapter")?.id;
    if (chapterId === undefined) throw new Error("The project has no chapter to edit.");
    const documentPath = `**/api/projects/${projectId}/documents/${chapterId}`;
    let releaseSave!: () => void;
    const pendingSave = new Promise<void>((resolve) => {
      releaseSave = resolve;
    });
    const rejectSave = async (route: Route) => {
      if (route.request().method() !== "PUT") return route.fallback();
      await pendingSave;
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "VALIDATION_ERROR", message: "Save refused for this test." },
        }),
      });
    };
    await studio.route(documentPath, rejectSave);
    const sourceNotice = studio.locator(".studio-inspector__source-notice:visible");
    try {
      await studio.locator(".cm-content").click();
      await studio.keyboard.press("ControlOrMeta+a");
      await studio.keyboard.type(`${saved}\n\n${UNSAVED_MARKER}`);
      await expect(saveStatus).toHaveText(/^saving$/i);
      await studio.getByRole("tab", { name: "Review", exact: true }).click();
      await expect(
        studio.getByText(
          "Reviews use saved chapters and keep a snapshot without changing your manuscript.",
        ),
      ).toBeVisible();
      await expect(sourceNotice).toContainText("Your current chapter has unsaved changes.");
      const runReview = studio.getByRole("button", { name: "Run review", exact: true });
      await expect(runReview).toBeEnabled();
      await runReview.click();
      await expect(studio.getByText("This review reported no findings.")).toBeVisible();
      const reviewRow = studio.locator(".studio-inspector__history-row").first();
      await reviewRow.click();
      await expect(reviewRow).toHaveAttribute("aria-pressed", "true");
      await studio.getByRole("tab", { name: "Export", exact: true }).click();
      await expect(
        studio.getByText("Exports include saved chapters. Unsaved changes are not included."),
      ).toBeVisible();
      await expect(sourceNotice).toContainText("Review and export use saved text.");
      await expect(studio.getByRole("button", { name: /^Markdown/ })).toBeEnabled();
      const firstExport = await downloadMarkdown(studio);
      expect(firstExport).toContain(SAVED_MARKER);
      expect(firstExport).not.toContain(UNSAVED_MARKER);
      releaseSave();
      await expect(studio.getByRole("button", { name: "Retry save", exact: true })).toBeVisible();
      await expect(sourceNotice).toContainText("Your current chapter has unsaved changes.");
      await studio.getByRole("tab", { name: "Review", exact: true }).click();
      await expect(runReview).toBeEnabled();
      await expect(sourceNotice).toContainText("Your current chapter has unsaved changes.");
    } finally {
      releaseSave();
      await studio.unroute(documentPath, rejectSave);
    }
    await studio.keyboard.press("ControlOrMeta+s");
    await expect(saveStatus).toHaveText(/^saved$/i);
    await expect(sourceNotice).toHaveCount(0);
    await studio.getByRole("tab", { name: "Export", exact: true }).click();
    await expect(sourceNotice).toHaveCount(0);
    const savedExport = await downloadMarkdown(studio);
    expect(savedExport).toContain(SAVED_MARKER);
    expect(savedExport).toContain(UNSAVED_MARKER);
    // Longer saved-source copy must leave the Review command at its native
    // 44px target size in both languages and narrow viewports.
    for (const view of [
      { language: "en", theme: "light", width: 1440 },
      { language: "zh", theme: "dark", width: 390 },
      { language: "en", theme: "dark", width: 320 },
    ]) {
      await studio.setViewportSize({ width: view.width, height: 900 });
      await studio
        .locator(".ui-language-switch__option")
        .filter({
          has: studio.locator(`input[value="${view.language}"]`),
        })
        .click();
      await studio
        .locator(".ui-theme-switch__option")
        .filter({
          has: studio.locator(`input[value="${view.theme}"]`),
        })
        .click();
      await studio
        .getByRole("tab", {
          name: view.language === "zh" ? "评审" : "Review",
          exact: true,
        })
        .click();
      await expect(
        studio.getByRole("heading", {
          name: view.language === "zh" ? "评审发现" : "Review findings",
          exact: true,
        }),
      ).toBeVisible();
      const heading = studio.locator('[role="tabpanel"]:not([hidden]) .studio-inspector__heading');
      const geometry = await heading.evaluate((node) => {
        const command = node.querySelector("button");
        const copy = node.querySelector("div");
        if (!command || !copy) throw new Error("Review heading has no command or copy.");
        return {
          command: command.getBoundingClientRect().toJSON(),
          copy: copy.getBoundingClientRect().toJSON(),
        };
      });
      expect(geometry.command.width).toBeGreaterThanOrEqual(44);
      expect(geometry.command.height).toBeGreaterThanOrEqual(44);
      expect(geometry.copy.right).toBeLessThanOrEqual(geometry.command.left - 8);
    }
  });
});
