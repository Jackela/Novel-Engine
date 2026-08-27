import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import {
  AUTHOR_INSTRUCTION_BEGIN,
  AUTHOR_INSTRUCTION_END,
  formatUntrustedManuscript,
  OUTLINE_BEAT_BEGIN,
  OUTLINE_BEAT_END,
  UNTRUSTED_MANUSCRIPT_BEGIN,
} from "../../src/contexts/studio/application/sanitization.js";
import { capturingFactory, propose } from "./proposal_test_helpers.js";
import {
  buildStudioApp,
  type CookieJar,
  call,
  type DocumentPayload,
  listDocuments,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

const OUTLINE_CONTENT = [
  "# Outline",
  "",
  "## The Storm",
  "",
  "Rain floods the harbour and Mara finds the washed-up chart.",
  "",
  "### The Archive",
  "",
  "Mara decodes the chart against the drowned maps.",
].join("\n");

interface BeatView {
  beat: { title: string; content: string } | null;
}

async function linkBeat(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
  beat: string | null,
) {
  return call(app, jar, "PUT", `/api/projects/${projectId}/documents/${documentId}/beat`, { beat });
}

async function readBeat(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
): Promise<{ status: number; view?: BeatView }> {
  const response = await call(
    app,
    jar,
    "GET",
    `/api/projects/${projectId}/documents/${documentId}/beat`,
  );
  if (response.statusCode !== 200) {
    return { status: response.statusCode };
  }
  return { status: response.statusCode, view: response.json() as BeatView };
}

/** Fresh chapter + outline pair inside a new project. */
async function seedChapterWithOutline(
  app: FastifyInstance,
  jar: CookieJar,
): Promise<{ projectId: string; chapter: DocumentPayload; outline: DocumentPayload }> {
  const project = await seedProject(app, jar, "Beat Studio");
  const outline = await seedDocument(app, jar, project.id, {
    kind: "outline",
    title: "Outline",
    content_markdown: OUTLINE_CONTENT,
  });
  const chapter = project.documents[0]!;
  return { projectId: project.id, chapter: chapter as DocumentPayload, outline };
}

describe("chapter beat association (#313)", () => {
  it("links a chapter to an existing outline beat and reads it back resolved", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const { projectId, chapter } = await seedChapterWithOutline(app, jar);

      const linked = await linkBeat(app, jar, projectId, chapter.id, "The Storm");
      expect(linked.statusCode).toBe(200);
      expect(linked.json()).toEqual({
        beat: {
          title: "The Storm",
          content: "Rain floods the harbour and Mara finds the washed-up chart.",
        },
      });

      const stored = (await getProjectDocument(app, jar, projectId, chapter.id)) as DocumentPayload;
      expect(stored.beat_ref).toBe("The Storm");

      const reread = await readBeat(app, jar, projectId, chapter.id);
      expect(reread.view?.beat?.title).toBe("The Storm");
      expect(reread.view?.beat?.content).toContain("washed-up chart");
    } finally {
      await app.close();
    }
  });

  it("refuses to link a beat the current outline does not hold", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const { projectId, chapter } = await seedChapterWithOutline(app, jar);

      const response = await linkBeat(app, jar, projectId, chapter.id, "Never Written");
      expect(response.statusCode).toBe(422);
      expect(response.json().error.code).toBe("INVALID_OPERATION");
    } finally {
      await app.close();
    }
  });

  it("lets only chapters carry the association", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const { projectId, outline } = await seedChapterWithOutline(app, jar);

      const response = await linkBeat(app, jar, projectId, outline.id, "The Storm");
      expect(response.statusCode).toBe(422);
      expect(response.json().error.code).toBe("INVALID_OPERATION");
    } finally {
      await app.close();
    }
  });

  it("reads unlinked chapters as having no beat without errors", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const { projectId, chapter } = await seedChapterWithOutline(app, jar);

      const reread = await readBeat(app, jar, projectId, chapter.id);
      expect(reread.status).toBe(200);
      expect(reread.view).toEqual({ beat: null });
    } finally {
      await app.close();
    }
  });

  it("clears the association with an explicit null, idempotently", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const { projectId, chapter } = await seedChapterWithOutline(app, jar);

      const linked = await linkBeat(app, jar, projectId, chapter.id, "The Storm");
      expect(linked.statusCode).toBe(200);

      const cleared = await linkBeat(app, jar, projectId, chapter.id, null);
      expect(cleared.statusCode).toBe(200);
      expect(cleared.json()).toEqual({ beat: null });
      expect(
        ((await getProjectDocument(app, jar, projectId, chapter.id)) as DocumentPayload).beat_ref,
      ).toBeNull();

      // Clearing again stays safe.
      const again = await linkBeat(app, jar, projectId, chapter.id, null);
      expect(again.statusCode).toBe(200);
      expect(again.json()).toEqual({ beat: null });
    } finally {
      await app.close();
    }
  });

  it("degrades gracefully when the linked beat vanishes from the outline", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const { projectId, chapter, outline } = await seedChapterWithOutline(app, jar);

      const linked = await linkBeat(app, jar, projectId, chapter.id, "The Storm");
      expect(linked.statusCode).toBe(200);

      // Rename the beat's heading so the stored reference no longer resolves.
      const renamed = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${projectId}/documents/${outline.id}`,
        {
          content_markdown: "# Outline\n\n## The Tempest\n\nRain floods the harbour.\n",
          base_revision_id: outline.current_revision_id,
        },
      );
      expect(renamed.statusCode).toBe(200);

      // Reads resolve to unlinked instead of erroring or serving stale text.
      const reread = await readBeat(app, jar, projectId, chapter.id);
      expect(reread.status).toBe(200);
      expect(reread.view).toEqual({ beat: null });

      // And generation runs with no beat section at all.
      const proposal = await propose(app, jar, projectId, chapter.id, { operation: "continue" });
      expect(proposal.statusCode).toBe(200);
      expect(capture.tasks[0]!.task.userPrompt).not.toContain(OUTLINE_BEAT_BEGIN);
    } finally {
      await app.close();
    }
  });

  it("answers 404 for a beat surface on an unknown document", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Missing doc");
      const response = await call(
        app,
        jar,
        "GET",
        `/api/projects/${project.id}/documents/missing/beat`,
      );
      expect(response.statusCode).toBe(404);
      expect(response.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});

describe("linked beats in the generation prompt (#313)", () => {
  it("carries the linked beat as labeled instruction context ahead of the manuscript", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const { projectId, chapter } = await seedChapterWithOutline(app, jar);
      const linked = await linkBeat(app, jar, projectId, chapter.id, "The Storm");
      expect(linked.statusCode).toBe(200);

      const response = await propose(app, jar, projectId, chapter.id, { operation: "continue" });
      expect(response.statusCode).toBe(200);

      const task = capture.tasks[0]!.task;
      const begin = task.userPrompt.indexOf(OUTLINE_BEAT_BEGIN);
      const end = task.userPrompt.indexOf(OUTLINE_BEAT_END);
      const manuscriptAt = task.userPrompt.indexOf(UNTRUSTED_MANUSCRIPT_BEGIN);
      expect(begin).toBeGreaterThanOrEqual(0);
      expect(end).toBeGreaterThan(begin);
      // The beat precedes the manuscript block and stays outside it.
      expect(manuscriptAt).toBeGreaterThan(end);
      expect(task.userPrompt).toContain("### The Storm");
      expect(task.userPrompt).toContain(
        "Rain floods the harbour and Mara finds the washed-up chart.",
      );
      expect(task.userPrompt).toContain("Outline beat");
    } finally {
      await app.close();
    }
  });

  it("keeps the exact previous prompt shape for an unlinked chapter", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const { projectId, chapter } = await seedChapterWithOutline(app, jar);

      const response = await propose(app, jar, projectId, chapter.id, { operation: "continue" });
      expect(response.statusCode).toBe(200);

      expect(capture.tasks[0]!.task.userPrompt).toBe(
        [
          "Operation: continue",
          `${AUTHOR_INSTRUCTION_BEGIN}\n\n${AUTHOR_INSTRUCTION_END}`,
          "",
          "Current manuscript (untrusted JSON data):",
          "",
          formatUntrustedManuscript(chapter.content_markdown),
        ].join("\n"),
      );
    } finally {
      await app.close();
    }
  });
});

async function getProjectDocument(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
): Promise<unknown> {
  const documents = await listDocuments(app, jar, projectId);
  return documents.find((candidate) => candidate.id === documentId);
}
