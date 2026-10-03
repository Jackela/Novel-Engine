import { describe, expect, it } from "vitest";

import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { wordCount } from "../../src/contexts/studio/application/payloads.js";
import { usageEvents } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { capturingFactory, propose, validProposalProse } from "./proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

/**
 * DR-028: the usage ledger must label how every token count was obtained
 * (`provider` / `estimated` / `unreported`) and must record failed provider
 * attempts instead of hiding them behind a completed-only ledger.
 */

/** A provider factory whose every generation fails after reaching the provider. */
function failingFactory(message: string) {
  return () => ({
    async generateStructured(): Promise<never> {
      throw new TextGenerationProviderError(message);
    },
  });
}

function usageRows(app: Awaited<ReturnType<typeof buildStudioApp>>["app"]) {
  const db = app.studioDb?.db;
  if (db === undefined) throw new Error("expected studio database handle");
  return db.select().from(usageEvents).all();
}

describe("usage provenance and failed attempts (DR-028)", () => {
  it("labels the word-count fallback as an estimate and the provider counts as provider", async () => {
    const estimate = capturingFactory({});
    const counts = capturingFactory({ promptTokens: 21, completionTokens: 34 });
    const { app } = await buildStudioApp(undefined, { textProviderFactory: estimate.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Estimated tokens");
      const document = project.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const instruction = "Tighten the harbor scene.";

      await propose(app, jar, project.id, document.id, { operation: "continue", instruction });

      const [row] = usageRows(app);
      if (row === undefined) throw new Error("expected a usage row");
      expect(row.token_source).toBe("estimated");
      expect(row.outcome).toBe("completed");
      expect(row.prompt_tokens).toBe(wordCount(instruction));
      expect(row.completion_tokens).toBe(wordCount(validProposalProse));

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(200);
      expect(response.json()).toMatchObject({
        request_count: 1,
        estimated_requests: 1,
        failed_attempt_count: 0,
        prompt_tokens: wordCount(instruction),
        completion_tokens: wordCount(validProposalProse),
      });

      // A provider that reports its own counts is labelled `provider`, and the
      // project then has no estimated rows at all.
      const reported = await buildStudioApp(undefined, { textProviderFactory: counts.factory });
      try {
        const reportedJar = await ownerJar(reported.app);
        const reportedProject = await seedProject(reported.app, reportedJar, "Reported tokens");
        const reportedDocument = reportedProject.documents[0];
        if (reportedDocument === undefined) throw new Error("expected seeded document");
        await propose(reported.app, reportedJar, reportedProject.id, reportedDocument.id, {
          operation: "continue",
        });

        const reportedRows = usageRows(reported.app);
        expect(reportedRows).toHaveLength(1);
        expect(reportedRows[0]?.token_source).toBe("provider");
        expect(reportedRows[0]?.prompt_tokens).toBe(21);
        const reportedUsage = await call(
          reported.app,
          reportedJar,
          "GET",
          `/api/projects/${reportedProject.id}/usage`,
        );
        expect(reportedUsage.json()).toMatchObject({
          request_count: 1,
          estimated_requests: 0,
          failed_attempt_count: 0,
          prompt_tokens: 21,
          completion_tokens: 34,
        });
      } finally {
        await reported.app.close();
      }
    } finally {
      await app.close();
    }
  });

  it("records a failed provider attempt as an unreported zero-token usage row", async () => {
    const factory = failingFactory("provider transport failed");
    const { app } = await buildStudioApp(undefined, { textProviderFactory: factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Failed attempt");
      const document = project.documents[0];
      if (document === undefined) throw new Error("expected seeded document");

      const proposal = await propose(app, jar, project.id, document.id, {
        operation: "continue",
        instruction: "Any instruction.",
      });
      expect(proposal.statusCode).toBe(200);
      const job = proposal.json();
      expect(job.status).toBe("failed");

      const rows = usageRows(app);
      expect(rows).toHaveLength(1);
      expect(rows[0]).toMatchObject({
        job_id: job.id,
        outcome: "failed",
        token_source: "unreported",
        prompt_tokens: 0,
        completion_tokens: 0,
      });

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(200);
      expect(response.json()).toMatchObject({
        request_count: 0,
        failed_attempt_count: 1,
        estimated_requests: 0,
        prompt_tokens: 0,
        completion_tokens: 0,
      });
    } finally {
      await app.close();
    }
  });
});
