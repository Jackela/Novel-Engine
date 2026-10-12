import { expect, test } from "@playwright/test";

import { createProject, studioChapters, typeChapter } from "../project_document_helpers";

// This workflow sorts after studio-ts.spec.ts, which creates the shared
// store's Owner. The login poll waits for that existing setup to settle.
const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");

test("conflict preview reads the server revision without replacing or saving the local Draft", async ({
  browser,
}) => {
  test.setTimeout(120_000);
  const context = await browser.newContext();
  try {
    const first = await context.newPage();
    await expect(async () => {
      await first.goto("/");
      await expect(first.getByRole("heading", { name: "Open your writing studio" })).toBeVisible();
    }).toPass({ timeout: 60_000 });
    await first.getByLabel("Password").fill(OWNER_PASSWORD);
    await first.getByRole("button", { name: "Sign in" }).click();
    await expect(first).toHaveURL(/\/projects$/);

    const projectId = await createProject(first, "Conflict preview ledger");
    await typeChapter(first, "First tab draft.");
    const second = await context.newPage();
    await second.goto(first.url());
    await expect(second.locator(".cm-content")).toHaveText("First tab draft.");
    await typeChapter(second, "Second tab wins.");
    const [serverDocument] = await studioChapters(second, projectId);
    expect(serverDocument).toBeDefined();
    const documentPath = `/api/projects/${projectId}/documents/${serverDocument.id}`;

    // The stale first tab receives a real 409 from the TS backend, rather
    // than a route fixture that bypasses revision-conflict checking.
    const conflictResponse = first.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === documentPath &&
        response.request().method() === "PUT" &&
        response.status() === 409,
    );
    const editor = first.locator(".cm-content");
    await editor.click();
    await first.keyboard.press("ControlOrMeta+a");
    await first.keyboard.type("Stale tab overwrite.");
    await conflictResponse;
    const conflict = first.locator(".editor-conflict");
    const saveState = first.locator(".studio-editor .editor__save-state");
    await expect(conflict).toBeVisible();
    await expect(saveState).toHaveText(/conflict/i);
    const titleBefore = await first.getByRole("textbox", { name: "Document title" }).inputValue();

    const previewWrites: string[] = [];
    first.on("request", (request) => {
      if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
        previewWrites.push(`${request.method()} ${new URL(request.url()).pathname}`);
      }
    });
    const viewServer = first.getByRole("button", { name: "View server version (read-only)" });
    await expect(viewServer).toBeVisible();
    await viewServer.click();
    const preview = first.getByRole("region", { name: "Server version (read-only)" });
    await expect(preview).toBeVisible();
    await expect(preview.locator("pre")).toHaveText("Second tab wins.");
    await expect(preview).toContainText(serverDocument.current_revision_id.slice(0, 8));
    await expect(editor).toHaveText("Stale tab overwrite.");
    await expect(first.getByRole("textbox", { name: "Document title" })).toHaveValue(titleBefore);
    await expect(saveState).toHaveText(/conflict/i);

    await first.getByRole("button", { name: "Hide server version" }).click();
    await expect(preview).toBeHidden();
    await expect(
      first.getByRole("button", { name: "View server version (read-only)" }),
    ).toBeVisible();
    await expect(first.getByRole("button", { name: "Load latest (discard local)" })).toBeEnabled();
    await expect(
      first.getByRole("button", { name: "Keep local and retry overwrite" }),
    ).toBeEnabled();
    await expect(editor).toHaveText("Stale tab overwrite.");
    await expect(saveState).toHaveText(/conflict/i);

    // Wait past the ordinary autosave debounce: preview and hide must not
    // introduce a save, including a delayed one after returning to the Draft.
    await first.waitForTimeout(1_700);
    expect(previewWrites).toEqual([]);
    const [unchangedServer] = await studioChapters(second, projectId);
    expect(unchangedServer.current_revision_id).toBe(serverDocument.current_revision_id);
    expect(unchangedServer.content_markdown).toBe("Second tab wins.");
  } finally {
    await context.close();
  }
});
