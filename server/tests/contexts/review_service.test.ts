import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { DocumentService } from "../../src/contexts/studio/application/document_service.js";
import { ProjectService } from "../../src/contexts/studio/application/project_service.js";
import {
  type EditorialAssessment,
  ReviewService,
} from "../../src/contexts/studio/application/review_service.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

function monotonicClock(): () => Date {
  let milliseconds = Date.parse("2026-08-24T00:00:00.000Z");
  return () => {
    milliseconds += 1;
    return new Date(milliseconds);
  };
}

function words(count: number): string {
  return Array.from({ length: count }, () => "word").join(" ");
}

function assessmentCodes(assessment: EditorialAssessment): string[] {
  return assessment.issues.map((issue) => `${issue.severity}:${issue.code}`);
}

describe("ReviewService", () => {
  it("evaluates frozen chapters, skips non-chapters, and lists newest assessments first", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-review-service-"));
    const studio = await openStudioDatabase(directory);
    try {
      const clock = monotonicClock();
      const store = new DrizzleStudioStore({ database: studio.db, dataDirectory: directory });
      const projects = new ProjectService(store, clock);
      const documents = new DocumentService(store, clock);
      const auth = new AuthService({
        store: new DrizzleAuthStore(studio.db),
        sessionSecret: "review-service-test-secret",
        now: clock,
      });
      await auth.configureOwner("reviewer", "long-test-password");
      const principal = (await auth.createOwnerSession("reviewer", "long-test-password")).principal;
      const reviewAssessments = new ReviewService(store, {
        now: clock,
        provenance: { provider: "mock", model: "deterministic-story-v1" },
      });
      const project = projects.newProject(principal, { title: "Frozen editorial evidence" }) as {
        id: string;
        documents: Array<{ id: string; current_revision_id: string }>;
      };
      const seed = project.documents[0];
      if (seed === undefined) {
        throw new Error("Project creation must provide its seed document.");
      }

      documents.storeDocument(principal, project.id, seed.id, {
        baseRevisionId: seed.current_revision_id,
        contentMarkdown: words(250),
      });
      const emptyChapter = documents.newDocument(principal, project.id, {
        kind: "chapter",
        title: "Empty room",
      }) as { id: string; current_revision_id: string };
      const thinChapter = documents.newDocument(principal, project.id, {
        kind: "chapter",
        title: "Short crossing",
        contentMarkdown: "two words",
      }) as { id: string };
      documents.newDocument(principal, project.id, {
        kind: "character",
        title: "Unreviewed character",
      });

      const first = reviewAssessments.evaluateProject(principal, project.id);

      expect(first.provider).toBe("mock");
      expect(first.model).toBe("deterministic-story-v1");
      expect(first.summary).toBe("Editorial checks completed without modifying the manuscript.");
      expect(assessmentCodes(first)).toEqual([
        "blocker:empty_chapter",
        "warning:thin_chapter",
        "warning:thin_chapter",
      ]);
      expect(first.issues.map((issue) => issue.documentId).sort()).toEqual(
        [emptyChapter.id, emptyChapter.id, thinChapter.id].sort(),
      );
      const thinFinding = first.issues.find(
        (issue) => issue.documentId === thinChapter.id && issue.code === "thin_chapter",
      );
      if (thinFinding === undefined) {
        throw new Error("The persisted assessment must retain the thin-chapter finding.");
      }
      expect(thinFinding.evidence).toEqual({ word_count: 2 });

      documents.storeDocument(principal, project.id, emptyChapter.id, {
        baseRevisionId: emptyChapter.current_revision_id,
        contentMarkdown: words(250),
      });
      const second = reviewAssessments.evaluateProject(principal, project.id);
      const listed = reviewAssessments.listEditorialAssessments(principal, project.id);

      expect(listed.map((assessment) => assessment.id)).toEqual([second.id, first.id]);
      const latest = listed[0];
      const original = listed[1];
      if (latest === undefined || original === undefined) {
        throw new Error("Both persisted assessments must be listed.");
      }
      expect(assessmentCodes(latest)).toEqual(["warning:thin_chapter"]);
      expect(assessmentCodes(original)).toEqual([
        "blocker:empty_chapter",
        "warning:thin_chapter",
        "warning:thin_chapter",
      ]);
    } finally {
      studio.close();
    }
  });
});
