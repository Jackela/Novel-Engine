import cookie from "@fastify/cookie";
import Fastify, { type FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";
import type {
  ReviewPageInput,
  ReviewSummaryPage,
} from "../../src/contexts/studio/application/ports/review_outcome_store.js";
import type { EditorialAssessment } from "../../src/contexts/studio/application/review_service.js";
import type { StudioServices } from "../../src/contexts/studio/application/studio_services.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import { reviewRoutes } from "../../src/contexts/studio/interface/http/review_routes.js";
import { AuthService, type IssuedSession } from "../../src/shared/application/auth_service.js";
import type {
  AuthStore,
  CreateSessionInput,
  OwnerRecord,
  SessionRecord,
} from "../../src/shared/application/ports/auth.js";
import { registerErrorEnvelope } from "../../src/shared/interface/http/error_envelope.js";
import {
  CSRF_COOKIE,
  CSRF_HEADER,
  SESSION_COOKIE,
} from "../../src/shared/interface/http/session_cookies.js";

class MemoryAuthStore implements AuthStore {
  private readonly sessionByHash = new Map<string, SessionRecord>();
  private owner: OwnerRecord | null = null;

  ownerExists(): boolean {
    return this.owner !== null;
  }

  getOwnerByUsername(username: string): OwnerRecord | null {
    return this.owner?.username === username ? this.owner : null;
  }

  getFirstOwner(): OwnerRecord | null {
    return this.owner;
  }

  createOwner(username: string, passwordHash: string): OwnerRecord {
    const owner: OwnerRecord = {
      id: "owner-1",
      username,
      passwordHash,
      createdAt: new Date("2026-08-24T00:00:00.000Z"),
    };
    this.owner = owner;
    return owner;
  }

  createSession(input: CreateSessionInput): SessionRecord {
    const record: SessionRecord = {
      id: `session-${this.sessionByHash.size + 1}`,
      kind: input.kind,
      ownerId: input.ownerId,
      tokenHash: input.tokenHash,
      csrfToken: input.csrfToken,
      createdAt: input.createdAt,
      expiresAt: input.expiresAt,
      lastSeenAt: input.lastSeenAt,
    };
    this.sessionByHash.set(record.tokenHash, record);
    return record;
  }

  getSessionByTokenHash(tokenHash: string): SessionRecord | null {
    return this.sessionByHash.get(tokenHash) ?? null;
  }

  deleteSession(sessionId: string): void {
    for (const [tokenHash, record] of this.sessionByHash) {
      if (record.id === sessionId) {
        this.sessionByHash.delete(tokenHash);
      }
    }
  }

  updateSessionLastSeen(sessionId: string, lastSeenAt: Date): void {
    for (const record of this.sessionByHash.values()) {
      if (record.id === sessionId) {
        record.lastSeenAt = lastSeenAt;
      }
    }
  }
}

class ReviewServiceDouble {
  readonly evaluatedProjectIds: string[] = [];
  readonly listedProjectIds: string[] = [];

  async evaluateProject(
    _principal: unknown,
    projectId: string,
    reportCleanupFailure?: (failure: unknown) => void,
  ): Promise<EditorialAssessment> {
    this.evaluatedProjectIds.push(projectId);
    void reportCleanupFailure;
    return assessmentFor(projectId);
  }

  collectProjectReviewSummaries(
    _principal: unknown,
    projectId: string,
    _input: ReviewPageInput,
  ): ReviewSummaryPage {
    this.listedProjectIds.push(projectId);
    if (projectId === "missing-project") {
      throw new NotFoundError("Project does not exist.");
    }
    const { issues, ...summary } = assessmentFor(projectId);
    return { reviews: [{ ...summary, issueCount: issues.length }], nextCursor: null };
  }
}

class JobHistoryDouble {
  readonly recordedReviewProjectIds: string[] = [];

  recordReviewJob(_principal: unknown, projectId: string): Record<string, unknown> {
    this.recordedReviewProjectIds.push(projectId);
    return {
      id: "job-review-1",
      project_id: projectId,
      document_id: null,
      kind: "review",
      operation: "review",
      status: "completed",
      provider: "mock",
      model: "deterministic-story-v1",
      request: {},
      result: { review_id: "review-1", snapshot_id: "snapshot-1", summary: "Assessed." },
      error: null,
      retry_of_job_id: null,
      events: [
        { id: "event-1", status: "completed", details: { review_id: "review-1" }, created_at: 0 },
      ],
      created_at: 0,
      updated_at: 0,
    };
  }
}

function assessmentFor(projectId: string): EditorialAssessment {
  return {
    id: "review-1",
    projectId,
    snapshotId: "snapshot-1",
    provider: "mock",
    model: "deterministic-story-v1",
    summary: "Editorial checks completed without modifying the manuscript.",
    createdAt: new Date("2026-08-24T12:34:56.000Z"),
    issues: [
      {
        id: "issue-1",
        documentId: "document-1",
        severity: "warning",
        code: "thin_chapter",
        message: "Chapter 1 contains only 2 words.",
        suggestion: "Develop the scene turn, consequence, and sensory detail.",
        evidence: { word_count: 2 },
      },
    ],
  };
}

function reviewOnlyServices(
  reviewAssessments: ReviewServiceDouble,
  jobHistory: JobHistoryDouble,
): StudioServices {
  // This route seam reaches only the review/job services; the production app
  // wires the remaining services in its composition root.
  return { reviewAssessments, jobHistory } as unknown as StudioServices;
}

function sessionCookies(session: IssuedSession, includeCsrf = true): string {
  const values = [`${SESSION_COOKIE}=${session.token}`];
  if (includeCsrf) {
    values.push(`${CSRF_COOKIE}=${session.csrfToken}`);
  }
  return values.join("; ");
}

async function buildReviewRouteApp(): Promise<{
  app: FastifyInstance;
  reviewService: ReviewServiceDouble;
  jobHistory: JobHistoryDouble;
  session: IssuedSession;
}> {
  const app = Fastify({ logger: false });
  const authService = new AuthService({
    store: new MemoryAuthStore(),
    sessionSecret: "review-route-seam-test-secret",
  });
  const reviewService = new ReviewServiceDouble();
  const jobHistory = new JobHistoryDouble();
  registerErrorEnvelope(app);
  await app.register(cookie);
  await app.register(reviewRoutes, {
    authService,
    services: reviewOnlyServices(reviewService, jobHistory),
  });
  await authService.configureOwner("reviewer", "correct horse battery");
  const session = await authService.createOwnerSession("reviewer", "correct horse battery");
  return { app, reviewService, jobHistory, session };
}

describe("review HTTP surface", () => {
  it("answers POST with the terminal review job", async () => {
    const { app, reviewService, jobHistory, session } = await buildReviewRouteApp();
    try {
      const headers = {
        cookie: sessionCookies(session),
        [CSRF_HEADER]: session.csrfToken,
      };
      const created = await app.inject({
        method: "POST",
        url: "/api/projects/project-1/reviews",
        headers,
      });

      expect(created.statusCode, created.body).toBe(201);
      const job = created.json();
      expect(job).toMatchObject({
        id: "job-review-1",
        project_id: "project-1",
        kind: "review",
        operation: "review",
        status: "completed",
        provider: "mock",
        model: "deterministic-story-v1",
        retry_of_job_id: null,
        result: { review_id: "review-1", snapshot_id: "snapshot-1" },
      });
      expect(job.events[0].details).toEqual({ review_id: "review-1" });
      expect(jobHistory.recordedReviewProjectIds).toEqual(["project-1"]);
      expect(reviewService.listedProjectIds).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("requires an authenticated principal to list reviews", async () => {
    const { app, reviewService } = await buildReviewRouteApp();
    try {
      const response = await app.inject({
        method: "GET",
        url: "/api/projects/project-1/reviews",
      });

      expect(response.statusCode).toBe(401);
      expect(response.json()).toEqual({
        error: { code: "UNAUTHORIZED", message: "Owner session required." },
      });
      expect(reviewService.listedProjectIds).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("requires CSRF double-submit before creating a review job", async () => {
    const { app, jobHistory, session } = await buildReviewRouteApp();
    try {
      const response = await app.inject({
        method: "POST",
        url: "/api/projects/project-1/reviews",
        headers: { cookie: sessionCookies(session, false) },
      });

      expect(response.statusCode).toBe(403);
      // The envelope names the double-submit headers so a client can recover.
      expect(response.json().error.code).toBe("CSRF_TOKEN_MISSING");
      expect(response.json().error.message).toContain("x-csrf-token");
      expect(jobHistory.recordedReviewProjectIds).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("rejects client-selected provider or model fields before invoking the review job", async () => {
    const { app, jobHistory, session } = await buildReviewRouteApp();
    try {
      const response = await app.inject({
        method: "POST",
        url: "/api/projects/project-1/reviews",
        headers: {
          cookie: sessionCookies(session),
          [CSRF_HEADER]: session.csrfToken,
          "content-type": "application/json",
        },
        payload: JSON.stringify({ provider: "dashscope", model: "attacker-selected-model" }),
      });

      expect(response.statusCode).toBe(422);
      expect(response.json().error.code).toBe("VALIDATION_ERROR");
      expect(jobHistory.recordedReviewProjectIds).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("maps absent projects through the unified not-found envelope", async () => {
    const { app, session } = await buildReviewRouteApp();
    try {
      const response = await app.inject({
        method: "GET",
        url: "/api/projects/missing-project/reviews",
        headers: { cookie: sessionCookies(session) },
      });

      expect(response.statusCode).toBe(404);
      expect(response.json()).toEqual({
        error: { code: "NOT_FOUND", message: "Project does not exist." },
      });
      expect(response.json()).not.toHaveProperty("detail");
    } finally {
      await app.close();
    }
  });
});
