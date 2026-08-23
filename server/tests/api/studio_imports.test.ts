import { realpathSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  directoryFingerprint,
  makeLegacyWorkspace,
  type LegacyChapterInput,
} from "../legacy_workspace_fixtures.js";
import { buildStudioApp, call, monotonicClock, ownerJar } from "./studio_helpers.js";

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
  return { app, source };
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
    const { app, source } = await buildImportApp();
    try {
      const before = directoryFingerprint(source);
      const jar = await ownerJar(app);
      const response = await call(app, jar, "POST", "/api/imports", {
        source: "legacy-story",
      });
      expect(response.statusCode, response.body).toBe(201);
      const body = response.json();
      expect(body.title).toBe("Imported Story");
      expect(body.description).toBe("A precise migration.");
      expect(body.settings).toEqual({ provider: "mock" });
      expect(body.import_hash).toMatch(/^[0-9a-f]{64}$/);
      expect(body.documents).toHaveLength(CHAPTERS.length);
      for (const [index, chapter] of CHAPTERS.entries()) {
        const document = body.documents[index];
        expect(document.kind).toBe("chapter");
        expect(document.title).toBe(`Chapter ${index + 1}`);
        expect(document.position).toBe(index + 1);
        expect(document.content_markdown).toBe(chapter.content);
        expect(document.metadata).toEqual({ legacy_filename: chapter.filename });
        expect(document.current_revision_id).toBeTruthy();
        expect(document.revision_source).toBe("author");
      }
      expect(directoryFingerprint(source)).toBe(before);
    } finally {
      await app.close();
    }
  });

  it("re-importing the same source returns the existing project without duplication", async () => {
    const { app, source } = await buildImportApp();
    try {
      const before = directoryFingerprint(source);
      const jar = await ownerJar(app);
      const first = await call(app, jar, "POST", "/api/imports", { source: "legacy-story" });
      expect(first.statusCode, first.body).toBe(201);
      const second = await call(app, jar, "POST", "/api/imports", { source: "legacy-story" });
      expect(second.statusCode, second.body).toBe(201);
      expect(second.json().id).toBe(first.json().id);
      expect(second.json().import_hash).toBe(first.json().import_hash);

      const list = await call(app, jar, "GET", "/api/projects");
      expect(list.statusCode).toBe(200);
      expect(list.json().projects).toHaveLength(1);
      expect(directoryFingerprint(source)).toBe(before);
    } finally {
      await app.close();
    }
  });
});
