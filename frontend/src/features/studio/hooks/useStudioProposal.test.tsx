import { act } from "react";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { ProposalOutcomeUnknownError } from "@/app/proposalStream";
import { summarizeDocument } from "./projectState";
import {
  baseProject,
  deferredStream,
  firstDocument,
  proposalJob,
  renderProposalHook,
  secondDocument,
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

describe("useStudioProposal", () => {
  it("streams the proposal into the preview and lands the job on the done frame", async () => {
    // Given
    const harness = renderProposalHook();
    const deferred = deferredStream();
    act(() => {
      harness.result().hook.setInstruction("Expand the scene");
    });
    let running: Promise<void> | undefined;
    act(() => {
      running = harness.result().hook.runProposal("continue");
    });
    if (running === undefined) throw new Error("Expected runProposal to start.");
    await act(async () => {
      deferred.requests[0]?.onDelta("A generated");
    });
    expect(harness.result().hook.streamingText).toBe("A generated");
    await act(async () => {
      deferred.requests[0]?.onDelta(" continuation.");
    });
    expect(harness.result().hook.streamingText).toBe("A generated continuation.");

    // When
    await deferred.settle(proposalJob);
    await act(async () => {
      await running;
    });

    // Then
    const request = deferred.requests[0];
    expect(request).toMatchObject({
      projectId: baseProject.id,
      documentId: firstDocument.id,
      operation: "continue",
      instruction: "Expand the scene",
      provider: "mock",
    });
    expect(request?.signal).toBeInstanceOf(AbortSignal);
    expect(harness.result().hook.proposal).toEqual(proposalJob);
    expect(harness.result().hook.streamingText).toBeNull();
    expect(harness.result().hook.isRunningProposal).toBe(false);
    expect(harness.result().inspector).toBe("history");
    expect(harness.result().error).toBeNull();
  });

  it("stops client preview without publishing a stale terminal error", async () => {
    // Given
    const harness = renderProposalHook();
    const deferred = deferredStream();
    await act(async () => {
      void harness.result().hook.runProposal("continue");
      await Promise.resolve();
    });

    // When
    act(() => {
      harness.result().hook.stopProposal();
    });
    const signal = deferred.requests[0]?.signal;
    await deferred.settle(proposalJob, new Error("Request cancelled."));

    // Then
    expect(signal?.aborted).toBe(true);
    expect(harness.result().hook.proposal).toBeNull();
    expect(harness.result().hook.streamingText).toBeNull();
    expect(harness.result().hook.isRunningProposal).toBe(false);
    expect(harness.result().error).toBeNull();
  });

  it("keeps the received text readable when the author stops the stream", async () => {
    // Given
    const harness = renderProposalHook();
    const deferred = deferredStream();
    let running: Promise<void> | undefined;
    act(() => {
      running = harness.result().hook.runProposal("continue");
    });
    if (running === undefined) throw new Error("Expected runProposal to start.");
    await act(async () => {
      deferred.requests[0]?.onDelta("Stopped mid-sentence");
    });

    // When the author stops and the cancelled request settles.
    act(() => {
      harness.result().hook.stopProposal();
    });
    await deferred.settle(
      proposalJob,
      new ProposalOutcomeUnknownError(new Error("Request cancelled.")),
    );
    await act(async () => {
      await running;
    });

    // Then the received deltas stay readable as a stopped preview.
    expect(deferred.requests[0]?.signal?.aborted).toBe(true);
    expect(harness.result().hook.proposal).toBeNull();
    expect(harness.result().hook.streamingText).toBe("Stopped mid-sentence");
    expect(harness.result().hook.streamingStopped).toBe(true);
    expect(harness.result().hook.streamingInterrupted).toBe(false);
    expect(harness.result().hook.isRunningProposal).toBe(false);
    expect(harness.result().error).toBeNull();
  });

  it("keeps the interrupted preview and surfaces the stream failure", async () => {
    // Given
    const harness = renderProposalHook();
    const deferred = deferredStream();
    await act(async () => {
      void harness.result().hook.runProposal("rewrite");
      await Promise.resolve();
    });
    await act(async () => {
      deferred.requests[0]?.onDelta("A partial scene");
    });

    // When
    await deferred.settle(proposalJob, new Error("provider exploded"));

    // Then
    expect(harness.result().error).toBe("provider exploded");
    expect(harness.result().hook.proposal).toBeNull();
    // DR-006: a mid-stream failure keeps the text the author already has.
    expect(harness.result().hook.streamingText).toBe("A partial scene");
    expect(harness.result().hook.streamingInterrupted).toBe(true);
  });

  it("leaves no preview to interrupt when the stream fails before any text", async () => {
    // Given
    const harness = renderProposalHook();
    const deferred = deferredStream();
    await act(async () => {
      void harness.result().hook.runProposal("continue");
      await Promise.resolve();
    });

    // When
    await deferred.settle(proposalJob, new Error("provider exploded"));

    // Then
    expect(harness.result().hook.streamingText).toBeNull();
    expect(harness.result().hook.streamingInterrupted).toBe(false);
  });

  it("refreshes project state and the accepted document after accepting a proposal", async () => {
    // Given
    const acceptedDocument = {
      ...firstDocument,
      current_revision_id: "revision-accepted",
      content_markdown: "Accepted continuation",
    };
    const refreshedProject = {
      ...baseProject,
      documents: [acceptedDocument, secondDocument],
    };
    vi.mocked(api.acceptProposal).mockResolvedValue(proposalJob);
    vi.mocked(api.project).mockResolvedValue(refreshedProject);
    vi.mocked(api.document).mockResolvedValue(acceptedDocument);
    const harness = renderProposalHook();
    act(() => {
      harness.result().hook.setProposal(proposalJob);
    });

    // When
    await act(async () => {
      await harness.result().hook.acceptProposal();
    });

    // Then
    expect(harness.result().project).toEqual({
      ...refreshedProject,
      documents: [summarizeDocument(acceptedDocument), secondDocument],
    });
    expect(harness.result().accepted).toEqual(acceptedDocument);
    expect(harness.result().hook.proposal).toBeNull();
    expect(harness.loadJobs).toHaveBeenCalledWith();
  });

  it("reports a committed acceptance truthfully when the aggregate refresh fails", async () => {
    vi.mocked(api.acceptProposal).mockResolvedValue(proposalJob);
    vi.mocked(api.project).mockRejectedValue(new Error("refresh unavailable"));
    const harness = renderProposalHook();
    act(() => harness.result().hook.setProposal(proposalJob));

    await act(async () => {
      await harness.result().hook.acceptProposal();
    });

    expect(harness.result().hook.proposal).toBeNull();
    expect(harness.result().error).toBe(
      "Proposal was accepted, but refreshing the project failed. Reload the project to sync.",
    );
    expect(harness.loadJobs).not.toHaveBeenCalled();
  });

  it("clears a stale proposal when the active document changes", () => {
    // Given
    const harness = renderProposalHook();
    act(() => {
      harness.result().hook.setProposal(proposalJob);
    });
    expect(harness.result().hook.proposal).toEqual(proposalJob);

    // When
    harness.rerender(secondDocument);

    // Then
    expect(harness.result().hook.proposal).toBeNull();
  });
});
