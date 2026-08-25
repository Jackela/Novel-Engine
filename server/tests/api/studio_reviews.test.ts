import cookie from "@fastify/cookie";
import Fastify, { type FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

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

  evaluateProject(_principal: unknown, projectId: string): EditorialAssessment {
    this.evaluatedProjectIds.push(projectId);
    return assessmentFor(projectId);
  }

  listEditorialAssessments(_principal: unknown, projectId: string): EditorialAssessment[] {
    this.listedProjectIds.push(projectId);
    if (projectId === "missing-project") {
      throw new NotFoundError("Project does not exist.");
    }
    return [assessmentFor(projectId)];
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

function reviewOnlyServices(reviewAssessments: ReviewServiceDouble): StudioServices {
  // This route seam reaches only reviewAssessments; the production app wires
  // the remaining services in its later composition-root segment.
  return { reviewAssessments } as unknown as StudioServices;
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
  session: IssuedSession;
}> {
  const app = Fastify({ logger: false });
  const authService = new AuthService({
    store: new MemoryAuthStore(),
    sessionSecret: "review-route-seam-test-secret",
  });
  const reviewService = new ReviewServiceDouble();
  registerErrorEnvelope(app);
  await app.register(cookie);
  await app.register(reviewRoutes, {
    authService,
    services: reviewOnlyServices(reviewService),
  });
  return { app, reviewService, session: authService.createGuestSession() };
}

describe("review HTTP surface", () => {
  it("creates and lists server-derived snapshot assessments in the frontend contract", async () => {
    const { app, reviewService, session } = await buildReviewRouteApp();
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
      expect(created.json()).toEqual({
        id: "review-1",
        project_id: "project-1",
        snapshot_id: "snapshot-1",
        provider: "mock",
        model: "deterministic-story-v1",
        summary: "Editorial checks completed without modifying the manuscript.",
        created_at: "2026-08-24T12:34:56.000Z",
        issues: [
          {
            id: "issue-1",
            document_id: "document-1",
            severity: "warning",
            code: "thin_chapter",
            message: "Chapter 1 contains only 2 words.",
            suggestion: "Develop the scene turn, consequence, and sensory detail.",
            evidence: { word_count: 2 },
          },
        ],
      });
      expect(reviewService.evaluatedProjectIds).toEqual(["project-1"]);

      const listed = await app.inject({
        method: "GET",
        url: "/api/projects/project-1/reviews",
        headers: { cookie: sessionCookies(session) },
      });

      expect(listed.statusCode, listed.body).toBe(200);
      expect(listed.json().reviews).toHaveLength(1);
      expect(listed.json().reviews[0]).toMatchObject({
        project_id: "project-1",
        created_at: "2026-08-24T12:34:56.000Z",
      });
      expect(listed.json().reviews[0].issues[0].document_id).toBe("document-1");
      expect(reviewService.listedProjectIds).toEqual(["project-1"]);
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
        error: { code: "UNAUTHORIZED", message: "Owner or guest session required." },
      });
      expect(reviewService.listedProjectIds).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("requires CSRF double-submit before creating a review", async () => {
    const { app, reviewService, session } = await buildReviewRouteApp();
    try {
      const response = await app.inject({
        method: "POST",
        url: "/api/projects/project-1/reviews",
        headers: { cookie: sessionCookies(session, false) },
      });

      expect(response.statusCode).toBe(403);
      expect(response.json()).toEqual({
        error: { code: "CSRF_TOKEN_MISSING", message: "CSRF token missing." },
      });
      expect(reviewService.evaluatedProjectIds).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("rejects client-selected provider or model fields before invoking the review service", async () => {
    const { app, reviewService, session } = await buildReviewRouteApp();
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
      expect(reviewService.evaluatedProjectIds).toEqual([]);
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
