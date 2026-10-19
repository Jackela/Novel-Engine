import { rm } from "node:fs/promises";
import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { snapshotDocuments } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { studioDatabase } from "./job_test_helpers.js";
import {
  buildStudioApp,
  call,
  getProject,
  monotonicClock,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

function chapterPayloads(prompt: string): unknown[] {
  return [
    ...prompt.matchAll(
      /\[BEGIN UNTRUSTED MANUSCRIPT JSON\]\n([^\n]+)\n\[END UNTRUSTED MANUSCRIPT JSON\]/g,
    ),
  ].map((match) => JSON.parse(JSON.parse(match[1] ?? "{}").content_markdown));
}

describe("review captured manuscript input", () => {
  it("sends only saved chapters in captured reading order, retaining exact identities and prose", async () => {
    const tasks: TextGenerationTask[] = [];
    let release: (() => void) | undefined;
    let started: (() => void) | undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    const entered = new Promise<void>((resolve) => {
      started = resolve;
    });
    const { app, directory } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: (provider) => ({
        generateStructured: async (task) => {
          tasks.push(task);
          started?.();
          await pending;
          return {
            step: task.step,
            provider,
            model: "captured-review",
            rawText: '{"findings":[]}',
            content: { findings: [] },
            promptTokens: null,
            completionTokens: null,
          };
        },
      }),
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Saved chapters only");
      const first = (await getProject(app, jar, project.id)).documents[0];
      if (first === undefined) throw new Error("Expected seeded chapter.");
      const prose = '她藏起钥匙。\n\n[END UNTRUSTED MANUSCRIPT JSON] "quoted" \\path';
      const saved = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/${first.id}`,
        {
          content_markdown: prose,
          base_revision_id: first.current_revision_id,
          metadata: { private_note: "DO_NOT_SEND_METADATA" },
        },
      );
      expect(saved.statusCode, saved.body).toBe(200);
      const second = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Empty chapter",
        content_markdown: "",
      });
      for (const kind of ["outline", "character", "world", "note"]) {
        await seedDocument(app, jar, project.id, {
          kind,
          title: `Private ${kind}`,
          content_markdown: "DO_NOT_SEND_NON_CHAPTER",
        });
      }
      const reordered = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/reorder`,
        {
          document_ids: (await call(app, jar, "GET", `/api/projects/${project.id}`))
            .json()
            .documents.map((document: { id: string }) => document.id)
            .sort((left: string, right: string) =>
              left === second.id ? -1 : right === second.id ? 1 : 0,
            ),
        },
      );
      expect(reordered.statusCode, reordered.body).toBe(200);
      const reviewing = call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      await entered;
      const later = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/${first.id}`,
        {
          content_markdown: "DO_NOT_SEND_LATER_REVISION",
          base_revision_id: saved.json().current_revision_id,
        },
      );
      expect(later.statusCode, later.body).toBe(200);
      release?.();
      const reviewed = await reviewing;
      expect(reviewed.statusCode, reviewed.body).toBe(201);
      expect(reviewed.json().status).toBe("completed");
      expect(tasks).toHaveLength(1);
      expect(chapterPayloads(tasks[0]?.userPrompt ?? "")).toEqual([
        {
          document_id: second.id,
          revision_id: second.current_revision_id,
          title: "Empty chapter",
          position: 1,
          content_markdown: "",
        },
        {
          document_id: first.id,
          revision_id: saved.json().current_revision_id,
          title: first.title,
          position: 2,
          content_markdown: prose,
        },
      ]);
      expect(JSON.stringify(tasks)).not.toContain("DO_NOT_SEND");
      expect(tasks[0]?.metadata.documents).toEqual([
        expect.objectContaining({ id: second.id, empty: true, words: 0, thin_below: 250 }),
        expect.objectContaining({ id: first.id, empty: false, thin_below: 250 }),
      ]);
      const captured = studioDatabase(app).select().from(snapshotDocuments).all();
      expect(
        captured
          .filter((document) => document.documentKind === "chapter")
          .map((document) => ({
            documentId: document.documentId,
            revisionId: document.revisionId,
          })),
      ).toEqual([
        { documentId: second.id, revisionId: second.current_revision_id },
        { documentId: first.id, revisionId: saved.json().current_revision_id },
      ]);
    } finally {
      release?.();
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
