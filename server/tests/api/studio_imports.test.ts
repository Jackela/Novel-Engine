import { realpathSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { buildApp } from "../../src/apps/api/app.js";
import { runLegacyImportCommand } from "../../src/apps/cli/legacy_import_command.js";
import {
  directoryFingerprint,
  type LegacyChapterInput,
  makeLegacyWorkspace,
} from "../legacy_workspace_fixtures.js";
import { TEST_SESSION_SECRET } from "./auth_helpers.js";
import {
  buildStudioApp,
  call,
  getDocument,
  getProject,
  monotonicClock,
  ownerJar,
} from "./studio_helpers.js";

const CHAPTERS: LegacyChapterInput[] = [
  { filename: "chapter-001.md", content: "# One\n\nThe lamp on the pier.\n" },
  { filename: "chapter-002.md", content: "# Two\n\nThe keeper looked away.\n" },
  { filename: "chapter-003.md", content: "# Three\n\nThe light returned.\n" },
];

/** App whose data directory carries one importable legacy workspace. */
async function buildImportApp() {
  const { app, directory } = await buildStudioApp(monotonicClock());
  const source = makeLegacyWorkspace(join(directory, "imports", "legacy-story"), {
    title: "Imported Story",
    premise: "A precise migration.",
    chapters: CHAPTERS,
  });
  return { app, directory, source };
}

/** Reopen the same data directory after a CLI run to inspect it over HTTP. */
async function reopenApp(directory: string) {
  const app = await buildApp({
    logger: false,
    databasePath: join(directory, "novel-engine.sqlite3"),
    sessionSecret: TEST_SESSION_SECRET,
  });
  return app;
}

describe("legacy import surface", () => {
  it("previews a legacy workspace without touching it", async () => {
    const { app, source } = await buildImportApp();
    try {
      const before = directoryFingerprint(source);
      const jar = await ownerJar(app);
      const response = await call(app, jar, "POST", "/api/imports/preview", {
        source: "legacy-story",
      });
      expect(response.statusCode, response.body).toBe(200);
      const body = response.json();
      expect(body.source).toBe(realpathSync(source));
      expect(body.title).toBe("Imported Story");
      expect(body.description).toBe("A precise migration.");
      expect(body.chapter_count).toBe(3);
      expect(body.chapters).toEqual(
        CHAPTERS.map((chapter) => ({
          filename: chapter.filename,
          bytes: Buffer.byteLength(chapter.content, "utf8"),
        })),
      );
      expect(body.source_hash).toMatch(/^[0-9a-f]{64}$/);
      expect(directoryFingerprint(source)).toBe(before);
    } finally {
      await app.close();
    }
  });

  it("imports chapters as Chapter 1..N by filename order with no extra documents", async () => {
    const { app, directory } = await buildImportApp();
    await ownerJar(app);
    // The CLI takes an explicit local path: unlike the web surface it is not
    // confined to data/imports, so the workspace lives beside it.
    const source = makeLegacyWorkspace(join(directory, "cli-source"), {
      title: "Imported Story",
      premise: "A precise migration.",
      chapters: CHAPTERS,
    });
    await app.close();
    const before = directoryFingerprint(source);

    const imported = await runLegacyImportCommand({
      databasePath: join(directory, "novel-engine.sqlite3"),
      source,
      owner: "owner",
    });

    expect(imported).toEqual({
      project_id: expect.any(String),
      title: "Imported Story",
      description: "A precise migration.",
      import_hash: expect.stringMatching(/^[0-9a-f]{64}$/),
      chapter_count: CHAPTERS.length,
      created: true,
    });
    expect(directoryFingerprint(source)).toBe(before);

    const reopened = await reopenApp(directory);
    try {
      const jar = await ownerJar(reopened);
      const project = await getProject(reopened, jar, imported.project_id);
      expect(project.documents).toHaveLength(CHAPTERS.length);
      for (const [index, chapter] of CHAPTERS.entries()) {
        const summary = project.documents[index];
        if (summary === undefined) throw new Error("expected imported document summary");
        const document = await getDocument(reopened, jar, project.id, summary.id);
        expect(summary.kind).toBe("chapter");
        expect(summary.title).toBe(`Chapter ${index + 1}`);
        expect(summary.position).toBe(index + 1);
        expect(document.content_markdown).toBe(chapter.content);
        expect(document.metadata).toEqual({ legacy_filename: chapter.filename });
        expect(document.current_revision_id).toBe(summary.current_revision_id);
        expect(document.revision_source).toBe("author");
      }
      const list = await call(reopened, jar, "GET", "/api/projects");
      expect(list.statusCode, list.body).toBe(200);
      expect(list.json().projects).toHaveLength(1);
    } finally {
      await reopened.close();
    }
  });

  it("re-importing the same source returns the existing project without duplication", async () => {
    const { app, directory } = await buildImportApp();
    await ownerJar(app);
    const source = makeLegacyWorkspace(join(directory, "cli-source"), {
      title: "Imported Story",
      premise: "A precise migration.",
      chapters: CHAPTERS,
    });
    await app.close();
    const before = directoryFingerprint(source);

    const first = await runLegacyImportCommand({
      databasePath: join(directory, "novel-engine.sqlite3"),
      source,
      owner: "owner",
    });
    const second = await runLegacyImportCommand({
      databasePath: join(directory, "novel-engine.sqlite3"),
      source,
      owner: "owner",
    });

    expect(first.created).toBe(true);
    expect(second.created).toBe(false);
    expect(second.project_id).toBe(first.project_id);
    expect(second.import_hash).toBe(first.import_hash);
    expect(directoryFingerprint(source)).toBe(before);

    const reopened = await reopenApp(directory);
    try {
      const jar = await ownerJar(reopened);
      const list = await call(reopened, jar, "GET", "/api/projects");
      expect(list.statusCode, list.body).toBe(200);
      expect(list.json().projects).toHaveLength(1);
    } finally {
      await reopened.close();
    }
  });
});
