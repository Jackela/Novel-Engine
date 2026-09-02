import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearRetryAttempt,
  clearRetryAttemptSession,
  getOrCreateRetryAttemptKey,
  recordRetryAttemptSession,
} from "./retryAttemptRegistry";
import type { Session } from "./types/studio";

const session: Session = {
  session_id: "session-a",
  kind: "owner",
  owner_id: "owner-a",
  expires_at: null,
};

beforeEach(() => {
  sessionStorage.clear();
  recordRetryAttemptSession(session);
  vi.spyOn(crypto, "randomUUID")
    .mockReturnValueOnce("00000000-0000-4000-8000-000000000001")
    .mockReturnValueOnce("00000000-0000-4000-8000-000000000002");
});

describe("retry attempt registry", () => {
  it("reuses one synchronously generated key across project navigation and reload", () => {
    expect(getOrCreateRetryAttemptKey("project-a", "job-a")).toBe(
      "00000000-0000-4000-8000-000000000001",
    );
    expect(getOrCreateRetryAttemptKey("project-b", "job-a")).toBe(
      "00000000-0000-4000-8000-000000000002",
    );
    expect(getOrCreateRetryAttemptKey("project-a", "job-a")).toBe(
      "00000000-0000-4000-8000-000000000001",
    );
    expect(crypto.randomUUID).toHaveBeenCalledTimes(2);
  });

  it("clears only the matching attempt and gives the next intent a new key", () => {
    const first = getOrCreateRetryAttemptKey("project-a", "job-a");

    clearRetryAttempt("project-a", "job-a", "a-late-unrelated-key");
    expect(getOrCreateRetryAttemptKey("project-a", "job-a")).toBe(first);

    clearRetryAttempt("project-a", "job-a", first);
    expect(getOrCreateRetryAttemptKey("project-a", "job-a")).toBe(
      "00000000-0000-4000-8000-000000000002",
    );
  });

  it("drops every retained attempt when the authenticated session changes", () => {
    getOrCreateRetryAttemptKey("project-a", "job-a");

    recordRetryAttemptSession({ ...session, session_id: "session-b" });
    expect(getOrCreateRetryAttemptKey("project-a", "job-a")).toBe(
      "00000000-0000-4000-8000-000000000002",
    );

    clearRetryAttemptSession();
    expect(() => getOrCreateRetryAttemptKey("project-a", "job-a")).toThrow(
      "Retry session identity is unavailable.",
    );
  });
});
