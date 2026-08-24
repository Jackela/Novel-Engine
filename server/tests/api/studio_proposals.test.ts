import { describe, expect, it } from "vitest";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { wordCount } from "../../src/contexts/studio/application/payloads.js";
import { isProposalMarkdownProse } from "../../src/contexts/studio/application/sanitization.js";
import { usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { capturingFactory, validProposalProse } from "./proposal_test_helpers.js";
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
  expect(isProposalMarkdownProse(markdown)).toBe(true);
}

describe("proposal flow", () => {
  it("records known factory failures while preserving unexpected factory failures", async () => {
    const knownFailure = new TextGenerationProviderError(
      "OpenAI-compatible API base must be an absolute URL",
    );
    const known = await buildStudioApp(undefined, {
      textProviderFactory: () => {
        throw knownFailure;
      },
    });
    try {
      const jar = await ownerJar(known.app);
      const project = await seedProject(known.app, jar, "Known factory failure");
      const document = project.documents[0];
      if (document === undefined) {
        throw new Error("Known factory failure fixture must create a default document.");
      }
      const response = await call(
        known.app,
        jar,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", instruction: "Continue.", provider: "openai_compatible" },
      );

      expect(response.statusCode, response.body).toBe(200);
      expect(response.json()).toMatchObject({
        status: "failed",
        provider: "openai_compatible",
        error: knownFailure.message,
        result: { proposal_markdown: "" },
      });
    } finally {
      await known.app.close();
    }

    const unexpected = await buildStudioApp(undefined, {
      textProviderFactory: () => {
        throw new Error("factory implementation secret");
      },
    });
    try {
      const jar = await ownerJar(unexpected.app);
      const project = await seedProject(unexpected.app, jar, "Unexpected factory failure");
      const document = project.documents[0];
      if (document === undefined) {
        throw new Error("Unexpected factory failure fixture must create a default document.");
      }
      const response = await call(
        unexpected.app,
        jar,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", instruction: "Continue.", provider: "openai_compatible" },
      );

      expect(response.statusCode, response.body).toBe(500);
      const body = response.json();
      expect(body.error).toMatchObject({ code: "INTERNAL_ERROR" });
      expect(JSON.stringify(body)).not.toContain("factory implementation secret");
    } finally {
      await unexpected.app.close();
    }
  });

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

  it("keeps narrative echo and result prose while rejecting key-shaped provider scaffolding", async () => {
    const cases = [
      {
        markdown: `${validProposalProse}\n\nThe corridor echoed at dawn, and the result was a promise Mara could finally trust.`,
        status: "completed",
      },
      { markdown: `${validProposalProse}\n\nEcho: raw scaffold echo`, status: "failed" },
      { markdown: `${validProposalProse}\n\n'EcHo' = raw scaffold echo`, status: "failed" },
      { markdown: `${validProposalProse}\n\n{"RESULT": "raw scaffold echo"}`, status: "failed" },
      {
        markdown: `${validProposalProse}\n\n{"meta": {}, "result": "raw scaffold echo"}`,
        status: "failed",
      },
      {
        markdown: `${validProposalProse}\n\n{"meta":[},\t"\\u0072esult" = "raw scaffold echo"}`,
        status: "failed",
      },
      { markdown: `${validProposalProse}\n\n\`result\`: raw scaffold echo`, status: "failed" },
      { markdown: `${validProposalProse}\n\n  - "ReSuLt" = raw scaffold echo`, status: "failed" },
      { markdown: `${validProposalProse}\n\n  1) 'ECHO': raw scaffold echo`, status: "failed" },
    ] as const;

    for (const { markdown, status } of cases) {
      const capture = capturingFactory({ markdown });
      const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
      try {
        const database = app.studioDb?.db;
        if (database === undefined) throw new Error("Studio test app must expose its database.");
        const jar = await ownerJar(app);
        const project = await seedProject(app, jar, "Prose guard");
        const document = project.documents[0] as DocumentPayload;
        const job = await draftProposal(app, jar, project.id, document.id, {
          operation: "continue",
          provider: "mock",
        });

        expect(job.status).toBe(status);
        if (status === "completed") {
          expect(job.result.proposal_markdown).toBe(markdown);
          expect(database.select().from(usageEvents).all()).toHaveLength(1);
          continue;
        }
        expect(job.result.proposal_markdown).toBe("");
        expect(JSON.stringify(job)).not.toContain("raw scaffold echo");
        expect(await listRevisions(app, jar, project.id, document.id)).toHaveLength(1);
        expect(database.select().from(usageEvents).all()).toHaveLength(0);
      } finally {
        await app.close();
      }
    }
  }, 15_000);

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
