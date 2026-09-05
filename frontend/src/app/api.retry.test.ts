import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";
import { getOrCreateRetryAttemptKey, recordRetryAttemptSession } from "./retryAttemptRegistry";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Studio retry API client", () => {
  it("sends retry identity without adding a request body or losing write headers", async () => {
    vi.stubGlobal("document", { cookie: "novel_engine_csrf=test-csrf-token" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "retry-1",
          project_id: "project-1",
          document_id: null,
          kind: "review",
          operation: "review",
          status: "failed",
          provider: "mock",
          model: "deterministic-story-v1",
          request: {},
          result: {},
          error: "failed",
          retry_of_job_id: "job-1",
          created_at: "2026-09-02T00:00:00.000Z",
          updated_at: "2026-09-02T00:00:01.000Z",
          events: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.retryJob("project-1", "job-1", "attempt-key-0001");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/jobs/job-1/retry",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: expect.objectContaining({
          "Idempotency-Key": "attempt-key-0001",
          "X-CSRF-Token": "test-csrf-token",
        }),
      }),
    );
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(init?.body).toBeUndefined();
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.["Content-Type"]).toBeUndefined();
  });

  it("clears retry recovery state when logout starts even if its response is lost", async () => {
    recordRetryAttemptSession({
      session_id: "session-1",
      kind: "owner",
      owner_id: "owner-1",
      expires_at: null,
    });
    getOrCreateRetryAttemptKey("project-1", "job-1");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("response lost")));

    await expect(api.logout()).rejects.toThrow();

    expect(() => getOrCreateRetryAttemptKey("project-1", "job-1")).toThrow(
      "Retry session identity is unavailable.",
    );
  });
});
