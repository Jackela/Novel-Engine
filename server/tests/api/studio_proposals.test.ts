import { describe, expect, it } from "vitest";
import { wordCount } from "../../src/contexts/studio/application/payloads.js";
import { FORBIDDEN_PROSE_PHRASES } from "../../src/contexts/studio/application/sanitization.js";
import {
  admitProposal,
  buildStudioApp,
  call,
  type DocumentPayload,
  draftProposal,
  getProject,
  listRevisions,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

function assertIsProse(markdown: string): void {
  expect(markdown.length).toBeGreaterThan(400);
  expect(() => JSON.parse(markdown)).toThrow();
  expect(markdown.toLowerCase()).not.toContain("echo");
  expect(markdown).not.toContain('"result"');
  for (const phrase of FORBIDDEN_PROSE_PHRASES) {
    expect(markdown.toLowerCase()).not.toContain(phrase.toLowerCase());
  }
}

describe("proposal flow", () => {
  it("drafts prose from the deterministic provider and leaves the manuscript untouched", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Prose");
      const document = project.documents[0] as DocumentPayload;
      const before = (await getProject(app, jar, project.id)).documents[0] as DocumentPayload;

      const job = await draftProposal(app, jar, project.id, document.id, {
        operation: "continue",
        instruction: "Tighten the chase.",
        provider: "mock",
      });

      expect(job.kind).toBe("proposal");
      expect(job.status).toBe("completed");
      expect(job.operation).toBe("continue");
      expect(job.provider).toBe("mock");
      expect(job.model).toBe("deterministic-story-v1");
      expect(job.request).toEqual({
        operation: "continue",
        instruction: "Tighten the chase.",
        base_revision_id: document.current_revision_id,
      });
      expect(job.result.base_revision_id).toBe(document.current_revision_id);
      expect(job.result.accepted_revision_id).toBeNull();
      assertIsProse(job.result.proposal_markdown as string);
      expect(job.events.map((event) => event.status)).toEqual(["completed"]);
      expect(job.events[0]!.details).toEqual({ proposal_only: true });

      // No acceptance yet: the document still points at revision A, nothing new exists.
      const after = (await getProject(app, jar, project.id)).documents[0] as DocumentPayload;
      expect(after.current_revision_id).toBe(before.current_revision_id);
      expect(after.content_markdown).toBe(before.content_markdown);
      expect(await listRevisions(app, jar, project.id, document.id)).toHaveLength(1);
    } finally {
      await app.close();
    }
  });

  it("reflects each document's own title and chapter number", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Mirrors");
      const first = project.documents[0] as DocumentPayload;
      const second = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "The Crossing",
      });

      const firstJob = await draftProposal(app, jar, project.id, first.id, {
        operation: "generate",
        instruction: "",
      });
      const secondJob = await draftProposal(app, jar, project.id, second.id, {
        operation: "generate",
        instruction: "",
      });

      const firstProse = firstJob.result.proposal_markdown as string;
      const secondProse = secondJob.result.proposal_markdown as string;
      expect(firstProse).not.toBe(secondProse);
      expect(firstProse).toContain("Chapter 1");
      expect(secondProse).toContain("Chapter 2");
      expect(secondProse).toContain("The Crossing");
    } finally {
      await app.close();
    }
  });

  it("accepts a completed proposal into an ai-accepted revision", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Accept");
      const document = project.documents[0] as DocumentPayload;
      const job = await draftProposal(app, jar, project.id, document.id, { operation: "rewrite" });

      const accepted = await admitProposal(app, jar, project.id, job.id);
      const acceptedRevisionId = accepted.result.accepted_revision_id as string;
      expect(acceptedRevisionId).not.toBeNull();

      const revisions = await listRevisions(app, jar, project.id, document.id);
      expect(revisions).toHaveLength(2);
      const acceptedRevision = revisions.find((revision) => revision.id === acceptedRevisionId);
      expect(acceptedRevision!.source).toBe("ai-accepted");
      expect(acceptedRevision!.metadata.ai_job_id).toBe(job.id);
      expect(acceptedRevision!.content_markdown).toBe(job.result.proposal_markdown);

      const after = (await getProject(app, jar, project.id)).documents[0] as DocumentPayload;
      expect(after.current_revision_id).toBe(acceptedRevisionId);
      expect(wordCount(after.content_markdown)).toBeGreaterThan(50);
    } finally {
      await app.close();
    }
  });

  it("is idempotent when acceptance is requested again", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Idempotent");
      const document = project.documents[0] as DocumentPayload;
      const job = await draftProposal(app, jar, project.id, document.id, { operation: "continue" });

      const first = await admitProposal(app, jar, project.id, job.id);
      const second = await admitProposal(app, jar, project.id, job.id);

      expect(second).toEqual(first);
      expect(second.result.accepted_revision_id).toBe(first.result.accepted_revision_id);
      expect(await listRevisions(app, jar, project.id, document.id)).toHaveLength(2);
    } finally {
      await app.close();
    }
  });

  it("rejects acceptance of a failed job without creating revisions", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Gated");
      const document = project.documents[0] as DocumentPayload;

      const failed = await draftProposal(app, jar, project.id, document.id, {
        operation: "continue",
        provider: "dashscope",
      });
      expect(failed.status).toBe("failed");
      const failedAccept = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/ai-proposals/${failed.id}/accept`,
      );
      expect(failedAccept.statusCode).toBe(422);
      expect(failedAccept.json().error.code).toBe("INVALID_OPERATION");

      expect(await listRevisions(app, jar, project.id, document.id)).toHaveLength(1);
    } finally {
      await app.close();
    }
  });
});
