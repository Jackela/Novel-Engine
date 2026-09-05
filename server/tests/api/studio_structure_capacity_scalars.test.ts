import { eq } from "drizzle-orm";
import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import {
  STRUCTURE_CAPACITY_LIMITS,
  StructureCapacityExceededError,
} from "../../src/contexts/studio/domain/structure_capacity.js";
import { documentRevisions } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { jobs } from "../../src/shared/infrastructure/db/schema.js";
import { studioDatabase } from "./job_test_helpers.js";
import {
  buildStudioApp,
  type CookieJar,
  call,
  draftProposal,
  getDocument,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

/**
 * Scalar-capacity contract (#461): serialized settings/metadata byte budgets
 * and the outline-beat budget refuse the overflowing write with the stable
 * 422 envelope before any revision, row, or stored scalar changes.
 */
describe("authoring structure scalar capacity", () => {
  it("admits settings at exactly 16,384 serialized bytes and refuses one more", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Settings capacity");
      const exact = { pad: padTo(STRUCTURE_CAPACITY_LIMITS.project_settings_bytes, { pad: "" }) };
      const atLimit = await call(app, owner, "PATCH", `/api/projects/${project.id}`, {
        settings: exact,
      });
      expect(atLimit.statusCode).toBe(200);
      expect(atLimit.json().settings).toEqual(exact);

      const over = {
        pad: padTo(STRUCTURE_CAPACITY_LIMITS.project_settings_bytes + 1, { pad: "" }),
      };
      const refused = await call(app, owner, "PATCH", `/api/projects/${project.id}`, {
        settings: over,
      });
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.details).toEqual({
        resource: "project_settings_bytes",
        limit: STRUCTURE_CAPACITY_LIMITS.project_settings_bytes,
        observed: STRUCTURE_CAPACITY_LIMITS.project_settings_bytes + 1,
      });
      const reread = await call(app, owner, "GET", `/api/projects/${project.id}`);
      expect(reread.json().settings).toEqual(exact);
    } finally {
      await app.close();
    }
  });

  it("admits document metadata at exactly 16,384 bytes and refuses one more", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Metadata capacity");
      const atLimit = await call(app, owner, "POST", `/api/projects/${project.id}/documents`, {
        kind: "note",
        title: "At Limit",
        metadata: { pad: padTo(STRUCTURE_CAPACITY_LIMITS.document_metadata_bytes, { pad: "" }) },
      });
      expect(atLimit.statusCode).toBe(201);

      const refused = await call(app, owner, "POST", `/api/projects/${project.id}/documents`, {
        kind: "note",
        title: "Over Limit",
        metadata: {
          pad: padTo(STRUCTURE_CAPACITY_LIMITS.document_metadata_bytes + 1, { pad: "" }),
        },
      });
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.details.resource).toBe("document_metadata_bytes");
      const shell = await call(app, owner, "GET", `/api/projects/${project.id}`);
      expect(shell.json().documents).toHaveLength(2); // seed chapter + at-limit note
    } finally {
      await app.close();
    }
  });

  it("refuses an oversized metadata save without minting a revision", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Metadata save capacity");
      const document = await seedDocument(app, owner, project.id, {
        kind: "note",
        title: "Note",
        content_markdown: "body",
      });
      const refused = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/${document.id}`,
        {
          content_markdown: "body",
          base_revision_id: document.current_revision_id,
          metadata: {
            pad: padTo(STRUCTURE_CAPACITY_LIMITS.document_metadata_bytes + 1, { pad: "" }),
          },
        },
      );
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.details.resource).toBe("document_metadata_bytes");
      const reread = await getDocument(app, owner, project.id, document.id);
      expect(reread.metadata).toEqual({});
      expect(reread.current_revision_id).toBe(document.current_revision_id);
      expect(countRevisions(app, document.id)).toBe(1);
    } finally {
      await app.close();
    }
  });

  it("admits an outline at exactly 5,000 beats and refuses 5,001 on save", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Beat capacity");
      const outline = await seedDocument(app, owner, project.id, {
        kind: "outline",
        title: "Outline",
        content_markdown: beats(STRUCTURE_CAPACITY_LIMITS.outline_beats),
      });
      const refused = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/${outline.id}`,
        {
          content_markdown: beats(STRUCTURE_CAPACITY_LIMITS.outline_beats + 1),
          base_revision_id: outline.current_revision_id,
        },
      );
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.details).toEqual({
        resource: "outline_beats",
        limit: STRUCTURE_CAPACITY_LIMITS.outline_beats,
        observed: STRUCTURE_CAPACITY_LIMITS.outline_beats + 1,
      });
      const reread = await getDocument(app, owner, project.id, outline.id);
      expect(reread.current_revision_id).toBe(outline.current_revision_id);
      expect(countRevisions(app, outline.id)).toBe(1);
    } finally {
      await app.close();
    }
  });

  it("refuses an accepted proposal that would mint an over-budget outline", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Proposal beat capacity");
      const outline = await seedDocument(app, owner, project.id, {
        kind: "outline",
        title: "Outline",
        content_markdown: "small",
      });
      const job = await draftProposal(app, owner, project.id, outline.id, {
        operation: "generate",
        instruction: "",
        provider: "mock",
      });
      expect(job.status).toBe("completed");
      // Simulate a provider proposal beyond the beat budget: accepting it
      // would mint it as the outline's next revision.
      studioDatabase(app)
        .update(jobs)
        .set({
          result_json: JSON.stringify({
            ...job.result,
            proposal_markdown: beats(STRUCTURE_CAPACITY_LIMITS.outline_beats + 1),
          }),
        })
        .where(eq(jobs.id, job.id))
        .run();

      const refused = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/ai-proposals/${job.id}/accept`,
      );
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.details).toEqual({
        resource: "outline_beats",
        limit: STRUCTURE_CAPACITY_LIMITS.outline_beats,
        observed: STRUCTURE_CAPACITY_LIMITS.outline_beats + 1,
      });
      const reread = await getDocument(app, owner, project.id, outline.id);
      expect(reread.content_markdown).toBe("small");
      expect(reread.current_revision_id).toBe(outline.current_revision_id);
      expect(countRevisions(app, outline.id)).toBe(1);
    } finally {
      await app.close();
    }
  });

  it("keeps pre-limit over-budget outlines readable but refuses their restore", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Legacy beat capacity");
      const outline = await seedDocument(app, owner, project.id, {
        kind: "outline",
        title: "Outline",
        content_markdown: "small",
      });
      // Simulate pre-limit stored data: rewrite revision 1's content directly.
      const oversized = beats(STRUCTURE_CAPACITY_LIMITS.outline_beats + 1);
      studioDatabase(app)
        .update(documentRevisions)
        .set({ contentMarkdown: oversized })
        .where(eq(documentRevisions.id, outline.current_revision_id))
        .run();
      const readable = await getDocument(app, owner, project.id, outline.id);
      expect(readable.content_markdown).toBe(oversized);

      const advanced = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/${outline.id}`,
        { content_markdown: "smaller", base_revision_id: outline.current_revision_id },
      );
      expect(advanced.statusCode).toBe(200);

      const restored = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/documents/${outline.id}/revisions/${outline.current_revision_id}/restore`,
        { base_revision_id: advanced.json().current_revision_id },
      );
      expect(restored.statusCode).toBe(422);
      expect(restored.json().error.details.resource).toBe("outline_beats");
      expect(countRevisions(app, outline.id)).toBe(2);
    } finally {
      await app.close();
    }
  });

  it("rejects invalid capacity evidence at construction time", () => {
    expect(() => new StructureCapacityExceededError("project_documents", 2_500, 2_500)).toThrow(
      RangeError,
    );
    expect(() => new StructureCapacityExceededError("unknown_resource" as never, 1, 2)).toThrow(
      RangeError,
    );
  });
});

function beats(count: number): string {
  return "## beat\n".repeat(count);
}

/** Pad the serialized size of `{"pad": ...}` to exactly `target` UTF-8 bytes. */
function padTo(target: number, value: { pad: string }): string {
  const base = JSON.stringify(value).length;
  if (base >= target) throw new Error("target too small for the padding shape");
  return "x".repeat(target - base);
}

function countRevisions(app: FastifyInstance, documentId: string): number {
  const rows = studioDatabase(app)
    .select({ id: documentRevisions.id })
    .from(documentRevisions)
    .where(eq(documentRevisions.documentId, documentId))
    .all();
  return rows.length;
}
