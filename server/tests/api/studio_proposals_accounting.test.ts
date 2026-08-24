import { describe, expect, it } from "vitest";

import { wordCount } from "../../src/contexts/studio/application/payloads.js";
import { jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { capturingFactory, propose, validProposalProse } from "./proposal_test_helpers.js";
import {
  buildStudioApp,
  call,
  getProject,
  guestJar,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

describe("proposal accounting and scoping", () => {
  it("records usage with the word-count fallback", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Usage");
      const document = project.documents[0]!;
      const instruction = "Tighten the chase through the archive."; // 6 words by the shared counter

      const response = await propose(app, jar, project.id, document.id, {
        operation: "continue",
        instruction,
      });
      const job = response.json();
      const documentPayload = (await getProject(app, jar, project.id)).documents[0]!;
      const usage = app.studioDb!.db.select().from(usageEvents).all();
      expect(usage).toHaveLength(1);
      expect(usage[0]!.job_id).toBe(job.id);
      expect(usage[0]!.provider).toBe("mock");
      expect(usage[0]!.model).toBe("deterministic-story-v1");
      expect(usage[0]!.prompt_tokens).toBe(wordCount(instruction));
      expect(usage[0]!.completion_tokens).toBe(wordCount(job.result.proposal_markdown));
      expect(JSON.parse(usage[0]!.request_evidence_json)).toEqual({
        operation: "continue",
        base_revision_id: documentPayload.current_revision_id,
      });
    } finally {
      await app.close();
    }
  });

  it("prefers provider-reported token counts over the fallback", async () => {
    const capture = capturingFactory({
      markdown: validProposalProse,
      promptTokens: 11,
      completionTokens: 13,
    });
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Counted");
      const document = project.documents[0]!;
      await propose(app, jar, project.id, document.id, { operation: "generate" });

      const usage = app.studioDb!.db.select().from(usageEvents).all();
      expect(usage).toHaveLength(1);
      expect(usage[0]!.prompt_tokens).toBe(11);
      expect(usage[0]!.completion_tokens).toBe(13);
      expect(usage[0]!.model).toBe("captured-model");
    } finally {
      await app.close();
    }
  });

  it("hides proposal jobs from other principals", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Scoped");
      const document = project.documents[0]!;
      const created = await propose(app, jar, project.id, document.id, { operation: "continue" });
      const job = created.json();

      const guest = await guestJar(app);
      const foreign = await call(
        app,
        guest,
        "POST",
        `/api/projects/${project.id}/ai-proposals/${job.id}/accept`,
      );
      expect(foreign.statusCode).toBe(404);
    } finally {
      await app.close();
    }
  });

  it("answers 404 when the job id names a job of another kind", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "WrongKind");
      const now = new Date();
      app
        .studioDb!.db.insert(jobs)
        .values({
          id: "job-export-1",
          project_id: project.id,
          kind: "export",
          operation: "export",
          status: "completed",
          created_at: now,
          updated_at: now,
        })
        .run();

      const response = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/ai-proposals/job-export-1/accept`,
      );
      expect(response.statusCode).toBe(404);
      expect(response.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});
