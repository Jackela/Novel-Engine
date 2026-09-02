import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import {
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ExportArtifactGateway } from "../../src/contexts/studio/application/export_artifact_service.js";
import { ExportArtifactWriteError } from "../../src/contexts/studio/domain/exceptions.js";
import {
  exports as exportRecords,
  projectSnapshots,
  reviewIssues,
  reviews,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { firstDocument, seedProjectWithChapter, studioDatabase } from "./job_test_helpers.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import {
  buildStudioApp,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

type ExportOutcome = "completed" | "failed";

function trackedExportGateway(outcome: ExportOutcome): {
  readonly gateway: ExportArtifactGateway;
  readonly writes: () => number;
} {
  let writes = 0;
  return {
    gateway: {
      async writeSnapshotArtifact(request) {
        writes += 1;
        if (outcome === "failed") throw new ExportArtifactWriteError();
        return {
          relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
          sizeBytes: 17,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => undefined,
          rollback: async () => undefined,
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected artifact read.");
      },
    },
    writes: () => writes,
  };
}

function seedInterruptedExport(app: FastifyInstance, projectId: string, id: string): void {
  const createdAt = new Date("2026-09-02T08:00:00.000Z");
  studioDatabase(app)
    .insert(jobs)
    .values({
      id,
      project_id: projectId,
      document_id: null,
      kind: "export",
      operation: "export",
      status: "interrupted",
      provider: "studio",
      model: "",
      request_json: JSON.stringify({ format: "markdown" }),
      result_json: JSON.stringify({}),
      error: "Job lost its execution lease during process restart.",
      created_at: createdAt,
      updated_at: createdAt,
    })
    .run();
}

function retryEvidence(app: FastifyInstance) {
  const database = studioDatabase(app);
  return {
    snapshots: database.select().from(projectSnapshots).all(),
    snapshotDocuments: database.select().from(snapshotDocuments).all(),
    reviews: database.select().from(reviews).all(),
    issues: database.select().from(reviewIssues).all(),
    exports: database.select().from(exportRecords).all(),
    jobs: database.select().from(jobs).all(),
    events: database.select().from(jobEvents).all(),
  };
}

describe("review and export retry terminal replay evidence", () => {
  it.each([
    { outcome: "completed", key: "completed-review-replay-key-0001" },
    { outcome: "failed", key: "failed-review-replay-key-0001" },
  ] as const)(
    "replays a terminal $outcome review without repeating provider work or evidence",
    async ({ outcome, key }) => {
      let providerCalls = 0;
      let reviewedDocumentId = "";
      const providerFactory: TextGenerationProviderFactory = (provider) => ({
        generateStructured: async (task) => {
          providerCalls += 1;
          if (providerCalls === 1 || outcome === "failed") {
            throw new TextGenerationProviderError(`fail review call ${providerCalls}`);
          }
          const content = {
            findings: [
              {
                document_id: reviewedDocumentId,
                severity: "warning",
                dimension: "pacing",
                message: "The crossing is over too fast.",
                suggestion: "Let the scene breathe.",
              },
            ],
          };
          return {
            step: task.step,
            provider,
            model: "review-replay-model",
            rawText: JSON.stringify(content),
            content,
            promptTokens: null,
            completionTokens: null,
          };
        },
      });
      const { app } = await buildStudioApp(monotonicClock(), {
        textProviderFactory: providerFactory,
      });
      try {
        const owner = await ownerJar(app);
        const project = await seedProject(app, owner, `${outcome} review replay`);
        reviewedDocumentId = firstDocument(project).id;
        const sourceResponse = await call(
          app,
          owner,
          "POST",
          `/api/projects/${project.id}/reviews`,
        );
        expect(sourceResponse.statusCode, sourceResponse.body).toBe(201);
        const source = sourceResponse.json<JobPayload>();
        expect(source.status).toBe("failed");

        const url = `/api/projects/${project.id}/jobs/${source.id}/retry`;
        const first = await retryJobRequest(app, owner, url, key);
        expect(first.statusCode, first.body).toBe(200);
        const terminal = first.json<JobPayload>();
        expect(terminal).toMatchObject({ status: outcome, retry_of_job_id: source.id });
        expect(providerCalls).toBe(2);

        const beforeReplay = retryEvidence(app);
        if (outcome === "completed") {
          expect(beforeReplay).toMatchObject({
            snapshots: [{ reason: "review" }],
            reviews: [{ model: "review-replay-model" }],
            issues: [{ documentId: reviewedDocumentId }],
          });
          expect(beforeReplay.snapshotDocuments.length).toBeGreaterThan(0);
        } else {
          expect(beforeReplay.snapshots).toHaveLength(0);
          expect(beforeReplay.snapshotDocuments).toHaveLength(0);
          expect(beforeReplay.reviews).toHaveLength(0);
          expect(beforeReplay.issues).toHaveLength(0);
        }
        expect(beforeReplay.exports).toHaveLength(0);
        expect(beforeReplay.jobs).toHaveLength(2);
        expect(beforeReplay.events).toHaveLength(3);

        const replay = await retryJobRequest(app, owner, url, key);
        expect(replay.statusCode, replay.body).toBe(200);
        expect(replay.body).toBe(first.body);
        expect(replay.json<JobPayload>()).toEqual(terminal);
        expect(providerCalls).toBe(2);
        expect(retryEvidence(app)).toEqual(beforeReplay);
      } finally {
        await app.close();
      }
    },
  );

  it.each([
    { outcome: "completed", key: "completed-export-replay-key-0001" },
    { outcome: "failed", key: "failed-export-replay-key-0001" },
  ] as const)(
    "replays a terminal $outcome export without repeating artifact work or evidence",
    async ({ outcome, key }) => {
      const artifact = trackedExportGateway(outcome);
      const { app } = await buildStudioApp(monotonicClock(), {
        exportArtifactGateway: artifact.gateway,
      });
      try {
        const owner = await ownerJar(app);
        const projectId = await seedProjectWithChapter(app, owner, `${outcome} export replay`);
        const sourceId = `${outcome}-export-replay-source`;
        seedInterruptedExport(app, projectId, sourceId);
        const url = `/api/projects/${projectId}/jobs/${sourceId}/retry`;

        const first = await retryJobRequest(app, owner, url, key);
        expect(first.statusCode, first.body).toBe(200);
        const terminal = first.json<JobPayload>();
        expect(terminal).toMatchObject({ status: outcome, retry_of_job_id: sourceId });
        expect(artifact.writes()).toBe(1);

        const beforeReplay = retryEvidence(app);
        expect(beforeReplay.jobs).toHaveLength(2);
        expect(beforeReplay.events).toHaveLength(2);
        if (outcome === "completed") {
          expect(beforeReplay.snapshots).toMatchObject([{ reason: "export" }]);
          expect(beforeReplay.snapshotDocuments.length).toBeGreaterThan(0);
          expect(beforeReplay.exports).toHaveLength(1);
        } else {
          expect(beforeReplay.snapshots).toHaveLength(0);
          expect(beforeReplay.snapshotDocuments).toHaveLength(0);
          expect(beforeReplay.exports).toHaveLength(0);
        }
        expect(beforeReplay.reviews).toHaveLength(0);
        expect(beforeReplay.issues).toHaveLength(0);

        const replay = await retryJobRequest(app, owner, url, key);
        expect(replay.statusCode, replay.body).toBe(200);
        expect(replay.body).toBe(first.body);
        expect(replay.json<JobPayload>()).toEqual(terminal);
        expect(artifact.writes()).toBe(1);
        expect(retryEvidence(app)).toEqual(beforeReplay);
      } finally {
        await app.close();
      }
    },
  );
});
