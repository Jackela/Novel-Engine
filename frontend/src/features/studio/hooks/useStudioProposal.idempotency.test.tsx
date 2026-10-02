import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProposalOutcomeUnknownError } from "@/app/proposalStream";
import {
  getOrCreateGenerateAttemptKey,
  recordRetryAttemptSession,
} from "@/app/retryAttemptRegistry";
import type { Session } from "@/app/types/studio";

import {
  baseProject,
  deferredStream,
  firstDocument,
  proposalJob,
  renderProposalHook,
} from "./useStudioProposal.test-harness";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();

  return {
    ...actual,
    api: {
      ...actual.api,
      acceptProposal: vi.fn<typeof actual.api.acceptProposal>(),
      document: vi.fn<typeof actual.api.document>(),
      project: vi.fn<typeof actual.api.project>(),
    },
  };
});

vi.mock("@/app/proposalStream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/proposalStream")>();

  return {
    ...actual,
    streamProposal: vi.fn<typeof actual.streamProposal>(),
  };
});

/**
 * DR-027: the client names each logical generation so a resend replays the
 * server's durable job instead of drafting — and billing — a second one. The
 * key survives an unknown outcome (a re-issue is the same operation) and is
 * cleared once the intent is spent (success or a definitive failure).
 */
const session: Session = {
  session_id: "session-idempotency",
  kind: "owner",
  owner_id: "owner-idempotency",
  expires_at: null,
};

async function startRun(harness: ReturnType<typeof renderProposalHook>): Promise<void> {
  await act(async () => {
    void harness.result().hook.runProposal("continue");
    await Promise.resolve();
  });
}

beforeEach(() => {
  sessionStorage.clear();
  recordRetryAttemptSession(session);
});

describe("useStudioProposal generation idempotency (DR-027)", () => {
  it("sends one generation key per intent and clears it once the proposal lands", async () => {
    const harness = renderProposalHook();
    const stream = deferredStream();

    await startRun(harness);
    const key = stream.requests[0]?.idempotencyKey;
    expect(typeof key).toBe("string");

    await stream.settle(proposalJob);
    await startRun(harness);

    expect(stream.requests[1]?.idempotencyKey).not.toBe(key);
  });

  it("keeps the key when the outcome is unknown so a resend is the same operation", async () => {
    const harness = renderProposalHook();
    const stream = deferredStream();

    await startRun(harness);
    const key = stream.requests[0]?.idempotencyKey;

    await stream.settle(proposalJob, new ProposalOutcomeUnknownError(new Error("lost socket")));

    expect(getOrCreateGenerateAttemptKey(baseProject.id, firstDocument.id, "continue")).toBe(key);
  });

  it("mints a new key after a definitive failure", async () => {
    const harness = renderProposalHook();
    const stream = deferredStream();

    await startRun(harness);
    const key = stream.requests[0]?.idempotencyKey;

    await stream.settle(proposalJob, new Error("provider exploded"));

    expect(getOrCreateGenerateAttemptKey(baseProject.id, firstDocument.id, "continue")).not.toBe(
      key,
    );
  });
});
