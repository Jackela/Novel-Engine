import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { expect, type Page, test } from "@playwright/test";
import { isRecord } from "../../src/app/typeGuards";
import { createProject, typeChapter } from "../e2e-ts/project_document_helpers";

const ownerPassword = ["ts-e2e-owner", "password-1234"].join("-");
async function materialWriteCount() {
  const directory = process.env.NOVEL_ENGINE_ACP_E2E_MATERIALS_ROOT;
  if (!directory)
    throw new Error(
      "NOVEL_ENGINE_ACP_E2E_MATERIALS_ROOT must name the isolated fixture workspace.",
    );
  try {
    return (await readFile(join(directory, "notes.md"), "utf8"))
      .split("\n")
      .filter((line) => line === "Working copy tool completed").length;
  } catch (reason) {
    if (reason instanceof Error && "code" in reason && reason.code === "ENOENT") return 0;
    throw reason;
  }
}
async function documentState(page: Page, projectId: string) {
  const project: unknown = await (await page.request.get(`/api/projects/${projectId}`)).json();
  if (!isRecord(project) || !Array.isArray(project.documents))
    throw new Error("Invalid project shell");
  const chapter: unknown = project.documents.find(
    (entry: unknown) => isRecord(entry) && entry.kind === "chapter",
  );
  if (!isRecord(chapter) || typeof chapter.id !== "string") throw new Error("Missing chapter");
  const document: unknown = await (
    await page.request.get(`/api/projects/${projectId}/documents/${chapter.id}`)
  ).json();
  if (
    !isRecord(document) ||
    typeof document.content_markdown !== "string" ||
    typeof document.current_revision_id !== "string"
  )
    throw new Error("Invalid document");
  return { content: document.content_markdown, revision: document.current_revision_id };
}

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Password", { exact: true }).fill(ownerPassword);
  if (await page.getByRole("heading", { name: "Create the local owner" }).isVisible()) {
    await page.getByLabel("Confirm password", { exact: true }).fill(ownerPassword);
    await page.getByRole("button", { name: "Create owner" }).click();
  } else await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/projects$/);
}
async function acpProject(page: Page, title: string) {
  const projectId = await createProject(page, title);
  await typeChapter(page, "# Chapter 1\n\nMira kept a dry notebook beside the harbor lantern.");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByRole("combobox", { name: "Provider" }).selectOption("acp");
  await page.getByRole("button", { name: "Save settings" }).click();
  await expect(page.getByRole("button", { name: "Save settings" })).toBeEnabled();
  await page.goto(`/projects/${projectId}/manuscript`);
  return projectId;
}
async function allowTool(page: Page) {
  const tools = page.getByRole("region", { name: "Agent tools" });
  const completed = tools.getByText("Operation completed", { exact: true });
  const completedBefore = await completed.count();
  await expect(tools.getByText("Waiting for your decision", { exact: true })).toBeVisible();
  await expect(tools.getByRole("button", { name: "Allow once", exact: true })).toBeEnabled();
  await tools.getByRole("button", { name: "Allow once", exact: true }).click();
  await expect(completed).toHaveCount(completedBefore + 1);
}

test.describe
  .serial("coupled ACP tools through the real Studio API", () => {
    test.beforeEach(async ({ page }) => signIn(page));

    test("observes all four steps, sends permission choices, and changes the manuscript only after acceptance", async ({
      page,
    }) => {
      const projectId = await acpProject(page, "ACP Four Steps");
      const writesBefore = await materialWriteCount();
      const savedBefore = await documentState(page, projectId);
      const requests: { path: string; method: string; operationId?: string }[] = [];
      page.on("request", (request) => {
        const path = new URL(request.url()).pathname;
        if (path.startsWith(`/api/projects/${projectId}/`))
          requests.push({
            path,
            method: request.method(),
            operationId: request.headers()["x-ai-operation-id"],
          });
      });
      const editor = page.locator(".cm-content");
      const original = (await editor.textContent()) ?? "";
      await page.getByRole("button", { name: "Continue", exact: true }).click();
      await allowTool(page);
      await expect(page.getByText("Proposed Markdown", { exact: true })).toBeVisible();
      await expect(editor).toHaveText(original);
      expect(await documentState(page, projectId)).toEqual(savedBefore);
      await page.getByRole("button", { name: "Accept", exact: true }).click();
      await expect(page.getByText("Proposed Markdown", { exact: true })).toHaveCount(0);
      await expect(editor).not.toHaveText(original);
      const accepted = await documentState(page, projectId);
      expect(accepted.content).not.toEqual(savedBefore.content);
      expect(accepted.revision).not.toEqual(savedBefore.revision);
      await page.getByRole("button", { name: "Rewrite", exact: true }).click();
      await allowTool(page);
      await expect(page.getByText("Proposed Markdown", { exact: true })).toBeVisible();

      await page.goto(`/projects/${projectId}/review`);
      await page.getByRole("button", { name: "Run review", exact: true }).click();
      await allowTool(page);
      await expect(page.getByRole("button", { name: "Run review", exact: true })).toBeEnabled();
      await page.goto(`/projects/${projectId}/manuscript?inspector=lore`);
      await page
        .getByRole("textbox", { name: "Paste a draft segment" })
        .fill("Mira keeps the lantern notebook at the harbor.");
      await page.getByRole("button", { name: "Extract segment", exact: true }).click();
      await allowTool(page);
      await expect(page.getByRole("region", { name: "Suggested lore entries" })).toBeVisible();
      expect(await materialWriteCount()).toBe(writesBefore + 4);
      expect(await documentState(page, projectId)).toEqual(accepted);
      const response: unknown = await (
        await page.request.get(`/api/projects/${projectId}/jobs`)
      ).json();
      if (!isRecord(response) || !Array.isArray(response.jobs)) throw new Error("Invalid jobs");
      expect(
        response.jobs.filter(
          (value: unknown) =>
            isRecord(value) && value.provider === "acp" && value.status === "completed",
        ),
      ).toHaveLength(4);

      const mutations = requests.filter(
        (request) =>
          request.method === "POST" &&
          (request.path.endsWith("/ai-proposals/stream") ||
            request.path.endsWith("/reviews") ||
            request.path.endsWith("/lore-extractions")),
      );
      expect(mutations).toHaveLength(4);
      for (const mutation of mutations) {
        expect(mutation.operationId).toMatch(/^[0-9a-f-]{36}$/);
        const observed = requests.findIndex(
          (request) =>
            request.method === "GET" &&
            request.path.endsWith(`/ai-operations/${mutation.operationId}/events`),
        );
        expect(observed).toBeGreaterThanOrEqual(0);
        expect(observed).toBeLessThan(requests.indexOf(mutation));
      }
      await page.reload();
      await expect(page.locator(".cm-content")).not.toHaveText(original);
    });

    test("Stop keeps file-effect evidence and navigation discards pending permission controls", async ({
      page,
    }) => {
      const projectId = await acpProject(page, "ACP Cancellation");
      const writesBefore = await materialWriteCount();
      const savedBefore = await documentState(page, projectId);
      const editor = page.locator(".cm-content");
      const original = (await editor.textContent()) ?? "";
      await page.getByRole("button", { name: "Continue", exact: true }).click();
      const tools = page.getByRole("region", { name: "Agent tools" });
      await expect(tools.getByRole("button", { name: "Allow once", exact: true })).toBeVisible();
      await tools.getByRole("button", { name: "Stop operation", exact: true }).click();
      await expect(tools.getByText("Operation stopped", { exact: true })).toBeVisible();
      await expect(
        tools.getByText(/Review your working folder before running this operation again/),
      ).toBeVisible();
      await expect(editor).toHaveText(original);
      await page.getByRole("tab", { name: "Jobs", exact: true }).click();
      await page.getByRole("button", { name: "Refresh jobs", exact: true }).click();
      await expect(
        page.getByRole("button", { name: "View tool activity", exact: true }),
      ).toBeVisible();
      await page.getByRole("button", { name: "View tool activity", exact: true }).click();
      await expect(
        page.getByText(/Review your working folder before running this operation again/),
      ).toHaveCount(2);

      await page.getByRole("button", { name: "Back to projects", exact: true }).click();
      const navigationProjectId = await acpProject(page, "ACP Navigation");
      const navigationSaved = await documentState(page, navigationProjectId);
      await page.getByRole("button", { name: "Continue", exact: true }).click();
      await expect(page.getByRole("button", { name: "Allow once", exact: true })).toBeVisible();
      await page.getByRole("button", { name: "Back to projects", exact: true }).click();
      await expect(page.getByRole("button", { name: "Allow once", exact: true })).toHaveCount(0);
      await page.goto(`/projects/${navigationProjectId}/manuscript`);
      await expect(page.locator(".cm-content")).toHaveText(original);
      await expect(page.getByRole("region", { name: "Agent tools" })).toHaveCount(0);
      expect(await documentState(page, projectId)).toEqual(savedBefore);
      expect(await documentState(page, navigationProjectId)).toEqual(navigationSaved);
      expect(await materialWriteCount()).toBe(writesBefore);
    });
  });
