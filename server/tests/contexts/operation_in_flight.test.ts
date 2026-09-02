import { describe, expect, it } from "vitest";

import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import {
  type OperationCapacityExceededError,
  OperationInFlightError,
} from "../../src/contexts/studio/domain/exceptions.js";

describe("in-flight operation admission", () => {
  it("applies the default project limit before the application limit", () => {
    const guard = new InFlightOperationGuard();
    const first = guard.acquire({
      projectId: "project-1",
      documentId: "document-1",
      operation: "continue",
    });
    const second = guard.acquire({
      projectId: "project-1",
      documentId: "document-2",
      operation: "rewrite",
    });

    expect(() =>
      guard.acquire({ projectId: "project-1", documentId: "document-3", operation: "polish" }),
    ).toThrow(
      expect.objectContaining<Partial<OperationCapacityExceededError>>({
        scope: "project",
        limit: 2,
        inFlight: 2,
        projectId: "project-1",
        retryAfterSeconds: 5,
      }),
    );

    const third = guard.acquire({ projectId: "project-2", documentId: null, operation: "review" });
    const fourth = guard.acquire({
      projectId: "project-3",
      documentId: null,
      operation: "export (markdown)",
    });
    expect(() =>
      guard.acquire({ projectId: "project-4", documentId: null, operation: "review" }),
    ).toThrow(
      expect.objectContaining<Partial<OperationCapacityExceededError>>({
        scope: "application",
        limit: 4,
        inFlight: 4,
        projectId: "project-4",
        retryAfterSeconds: 5,
      }),
    );

    first.release();
    second.release();
    third.release();
    fourth.release();
  });

  it("applies injected limits without mutating state on a refused acquisition", () => {
    const guard = new InFlightOperationGuard({ applicationLimit: 2, projectLimit: 1 });
    const first = guard.acquire({ projectId: "project-1", documentId: null, operation: "review" });

    expect(() =>
      guard.acquire({ projectId: "project-1", documentId: null, operation: "export (markdown)" }),
    ).toThrow(expect.objectContaining({ scope: "project", limit: 1, inFlight: 1 }));

    const second = guard.acquire({ projectId: "project-2", documentId: null, operation: "review" });
    expect(() =>
      guard.acquire({ projectId: "project-3", documentId: null, operation: "review" }),
    ).toThrow(expect.objectContaining({ scope: "application", limit: 2, inFlight: 2 }));

    first.release();
    const replacement = guard.acquire({
      projectId: "project-3",
      documentId: null,
      operation: "review",
    });
    replacement.release();
    second.release();
  });

  it("reports deletion and identical-target conflicts before exhausted capacity", () => {
    const guard = new InFlightOperationGuard({ applicationLimit: 1, projectLimit: 1 });
    const active = guard.acquire({
      projectId: "project-1",
      documentId: "document-1",
      operation: "continue",
    });

    expect(() =>
      guard.acquire({ projectId: "project-1", documentId: "document-1", operation: "continue" }),
    ).toThrow(OperationInFlightError);

    const deleting = guard.acquireProjectExclusive("project-2", "project deletion");
    expect(() =>
      guard.acquire({ projectId: "project-2", documentId: null, operation: "review" }),
    ).toThrow(
      expect.objectContaining<Partial<OperationInFlightError>>({
        projectId: "project-2",
        documentId: null,
        operation: "project deletion",
      }),
    );

    deleting.release();
    active.release();
  });

  it("lets an idle project acquire deletion ownership while another project fills capacity", () => {
    const guard = new InFlightOperationGuard({ applicationLimit: 1, projectLimit: 1 });
    const active = guard.acquire({ projectId: "project-1", documentId: null, operation: "review" });
    const deleting = guard.acquireProjectExclusive("project-2", "project deletion");

    expect(() => guard.acquireProjectExclusive("project-1", "project deletion")).toThrow(
      expect.objectContaining<Partial<OperationInFlightError>>({ operation: "review" }),
    );

    deleting.release();
    active.release();
  });

  it("keeps later operation and deletion owners safe from stale permit release", () => {
    const guard = new InFlightOperationGuard({ applicationLimit: 1, projectLimit: 1 });
    const oldOperation = guard.acquire({
      projectId: "project-1",
      documentId: null,
      operation: "review",
    });
    oldOperation.release();
    const currentOperation = guard.acquire({
      projectId: "project-1",
      documentId: null,
      operation: "review",
    });
    oldOperation.release();
    expect(() =>
      guard.acquire({ projectId: "project-1", documentId: null, operation: "review" }),
    ).toThrow(OperationInFlightError);
    currentOperation.release();

    const oldDeletion = guard.acquireProjectExclusive("project-1", "project deletion");
    oldDeletion.release();
    const currentDeletion = guard.acquireProjectExclusive("project-1", "project deletion");
    oldDeletion.release();
    expect(() =>
      guard.acquire({ projectId: "project-1", documentId: null, operation: "review" }),
    ).toThrow(OperationInFlightError);
    currentDeletion.release();
  });
});
