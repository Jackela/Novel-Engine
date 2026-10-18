import { rm } from "node:fs/promises";
import { describe, expect, it } from "vitest";

import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ReviewPayload } from "../../src/contexts/studio/application/payload_schemas/review.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import {
  buildStudioApp,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

describe("review chapter finding boundary", () => {
  it.each([
    { retry: false, validChapter: true },
    { retry: true, validChapter: true },
    { retry: false, validChapter: false },
    { retry: true, validChapter: false },
  ])(
    "persists chapter findings on retry=$retry with validChapter=$validChapter",
    async ({ retry, validChapter }) => {
      let firstAttempt = true;
      let findings: Record<string, unknown>[] = [];
      const { app, directory } = await buildStudioApp(monotonicClock(), {
        textProviderFactory: (provider) => ({
          generateStructured: async () => {
            if (retry && firstAttempt) {
              firstAttempt = false;
              throw new TextGenerationProviderError("temporary review failure");
            }
            const content = { findings };
            return {
              step: "editorial_review",
              provider,
              model: "chapter-boundary-model",
              rawText: JSON.stringify(content),
              content,
              promptTokens: null,
              completionTokens: null,
            };
          },
        }),
      });
      try {
        const jar = await ownerJar(app);
        const project = await seedProject(app, jar, "Chapter-only findings");
        const chapter = project.documents[0];
        if (chapter === undefined) throw new Error("Expected seeded chapter.");
        const otherProject = await seedProject(app, jar, "Unrelated manuscript");
        const otherChapter = otherProject.documents[0];
        if (otherChapter === undefined) throw new Error("Expected unrelated chapter.");
        const rejectedIds = ["unknown-document", otherChapter.id];
        for (const kind of ["outline", "character", "world", "note"]) {
          const document = await seedDocument(app, jar, project.id, {
            kind,
            title: `Captured ${kind}`,
            content_markdown: "Non-chapter source material.",
          });
          rejectedIds.push(document.id);
        }
        findings = rejectedIds.map((documentId) => ({
          document_id: documentId,
          severity: "blocker",
          dimension: "continuity",
          message: "This must not become a chapter finding.",
        }));
        if (validChapter) {
          findings.push({
            document_id: chapter.id,
            severity: "warning",
            dimension: "Pacing",
            message: "The opening slows before the decision.",
            suggestion: "Shorten the arrival.",
          });
        }
        const expectedIssues = validChapter
          ? [
              {
                id: expect.any(String),
                document_id: chapter.id,
                severity: "warning",
                code: "pacing",
                message: "The opening slows before the decision.",
                suggestion: "Shorten the arrival.",
                evidence: {},
              },
            ]
          : [];

        let response = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
        expect(response.statusCode, response.body).toBe(201);
        if (retry) {
          const failed = response.json<JobPayload>();
          expect(failed.status).toBe("failed");
          response = await retryJobRequest(
            app,
            jar,
            `/api/projects/${project.id}/jobs/${failed.id}/retry`,
            `chapter-findings-retry-${validChapter}-0001`,
          );
          expect(response.statusCode, response.body).toBe(200);
          expect(response.json<JobPayload>().retry_of_job_id).toBe(failed.id);
        }
        const completed = response.json<JobPayload>();
        expect(completed).toMatchObject({
          status: "completed",
          provider: "mock",
          model: "chapter-boundary-model",
          error: null,
          result: { review_id: expect.any(String), snapshot_id: expect.any(String) },
        });
        const detail = await call(
          app,
          jar,
          "GET",
          `/api/projects/${project.id}/reviews/${completed.result.review_id}`,
        );
        expect(detail.statusCode, detail.body).toBe(200);
        expect(detail.json<ReviewPayload>().issues).toEqual(expectedIssues);
        expect(detail.json<ReviewPayload>().snapshot_id).toBe(completed.result.snapshot_id);
        const listed = await call(app, jar, "GET", `/api/projects/${project.id}/reviews`);
        expect(listed.statusCode, listed.body).toBe(200);
        expect(listed.json().reviews).toMatchObject([
          { id: completed.result.review_id, issue_count: validChapter ? 1 : 0 },
        ]);
        expect(listed.json().reviews).toHaveLength(1);
        const job = await call(app, jar, "GET", `/api/projects/${project.id}/jobs/${completed.id}`);
        expect(job.statusCode, job.body).toBe(200);
        expect(job.json<JobPayload>().result).toEqual(completed.result);
      } finally {
        await app.close();
        await rm(directory, { recursive: true, force: true });
      }
    },
  );
});
