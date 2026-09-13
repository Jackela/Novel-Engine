import { expect, type Page } from "@playwright/test";

export interface ChapterDocument {
  id: string;
  kind: string;
  title: string;
  position: number;
  current_revision_id: string;
  content_markdown: string;
  revision_source: string;
}

interface ChapterSummary {
  id: string;
  kind: "chapter";
  title: string;
  position: number;
  current_revision_id: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireString(record: Record<string, unknown>, key: string, endpoint: string): string {
  const value = record[key];
  if (typeof value !== "string") {
    throw new Error(`${endpoint} returned a document with an invalid ${key}.`);
  }
  return value;
}

function requireInteger(record: Record<string, unknown>, key: string, endpoint: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new Error(`${endpoint} returned a document with an invalid ${key}.`);
  }
  return value;
}

function parseChapterSummaries(payload: unknown, endpoint: string): ChapterSummary[] {
  if (!isRecord(payload) || !Array.isArray(payload.documents)) {
    throw new Error(`${endpoint} returned an invalid project shell.`);
  }
  const summaries: Array<{ summary: ChapterSummary; shellIndex: number }> = [];
  for (const [shellIndex, candidate] of payload.documents.entries()) {
    if (!isRecord(candidate)) {
      throw new Error(`${endpoint} returned an invalid document summary at index ${shellIndex}.`);
    }
    const kind = requireString(candidate, "kind", endpoint);
    if (kind !== "chapter") continue;
    summaries.push({
      summary: {
        id: requireString(candidate, "id", endpoint),
        kind,
        title: requireString(candidate, "title", endpoint),
        position: requireInteger(candidate, "position", endpoint),
        current_revision_id: requireString(candidate, "current_revision_id", endpoint),
      },
      shellIndex,
    });
  }
  return summaries
    .sort(
      (left, right) =>
        left.summary.position - right.summary.position || left.shellIndex - right.shellIndex,
    )
    .map(({ summary }) => summary);
}

function parseChapterDocument(
  payload: unknown,
  summary: ChapterSummary,
  projectId: string,
  endpoint: string,
): ChapterDocument {
  if (!isRecord(payload)) {
    throw new Error(`${endpoint} returned an invalid document payload.`);
  }
  const document: ChapterDocument = {
    id: requireString(payload, "id", endpoint),
    kind: requireString(payload, "kind", endpoint),
    title: requireString(payload, "title", endpoint),
    position: requireInteger(payload, "position", endpoint),
    current_revision_id: requireString(payload, "current_revision_id", endpoint),
    content_markdown: requireString(payload, "content_markdown", endpoint),
    revision_source: requireString(payload, "revision_source", endpoint),
  };
  const documentProjectId = requireString(payload, "project_id", endpoint);
  if (
    documentProjectId !== projectId ||
    document.id !== summary.id ||
    document.kind !== summary.kind ||
    document.title !== summary.title ||
    document.position !== summary.position ||
    document.current_revision_id !== summary.current_revision_id
  ) {
    throw new Error(`${endpoint} did not match its project-shell summary.`);
  }
  return document;
}

export async function studioChapters(page: Page, projectId: string): Promise<ChapterDocument[]> {
  const projectEndpoint = `/api/projects/${encodeURIComponent(projectId)}`;
  const projectResponse = await page.request.get(projectEndpoint);
  const projectText = await projectResponse.text();
  if (projectResponse.status() !== 200) {
    throw new Error(`${projectEndpoint} returned ${projectResponse.status()}: ${projectText}`);
  }

  let projectPayload: unknown;
  try {
    projectPayload = JSON.parse(projectText);
  } catch (error) {
    throw new Error(`${projectEndpoint} returned invalid JSON.`, { cause: error });
  }
  const summaries = parseChapterSummaries(projectPayload, projectEndpoint);

  return Promise.all(
    summaries.map(async (summary) => {
      const documentEndpoint = `${projectEndpoint}/documents/${encodeURIComponent(summary.id)}`;
      const documentResponse = await page.request.get(documentEndpoint);
      const documentText = await documentResponse.text();
      if (documentResponse.status() !== 200) {
        throw new Error(
          `${documentEndpoint} returned ${documentResponse.status()}: ${documentText}`,
        );
      }
      let documentPayload: unknown;
      try {
        documentPayload = JSON.parse(documentText);
      } catch (error) {
        throw new Error(`${documentEndpoint} returned invalid JSON.`, { cause: error });
      }
      return parseChapterDocument(documentPayload, summary, projectId, documentEndpoint);
    }),
  );
}

export async function createProject(page: Page, title: string): Promise<string> {
  await page.goto("/");
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: /create project/i }).click();
  await expect(page).toHaveURL(/\/projects\/([^/]+)\/manuscript/);
  return page.url().match(/\/projects\/([^/]+)\/manuscript/)?.[1] ?? "";
}

export async function typeChapter(page: Page, markdown: string): Promise<void> {
  const editor = page.locator(".cm-content");
  await editor.click();
  // ControlOrMeta resolves to the platform's select-all chord: CodeMirror maps
  // Mod-A to selectAll, so the typed chapter replaces the seed content.
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.type(markdown);
  await expect(page.locator(".studio-editor .editor__save-state")).toHaveText(/saved/i, {
    timeout: 15_000,
  });
}
