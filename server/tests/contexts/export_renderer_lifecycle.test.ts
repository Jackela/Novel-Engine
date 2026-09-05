import { describe, expect, it } from "vitest";

import type * as A from "../../src/contexts/studio/application/export_artifact_service.js";
import { SnapshotArtifactService } from "../../src/contexts/studio/application/export_artifact_service.js";
import type * as E from "../../src/contexts/studio/application/ports/export_store.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { OperationCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";

const principal: Principal = {
  sessionId: "session",
  kind: "owner",
  ownerId: "owner",
  expiresAt: null,
};

describe("SnapshotArtifactService renderer ownership", () => {
  it("refuses a second render before source capture and holds ownership through acknowledgement", async () => {
    const store = new LifecycleStore();
    const acknowledgement = deferred<void>();
    let acknowledgements = 0;
    const gateway: A.ExportArtifactGateway = {
      async writeSnapshotArtifact(request) {
        return {
          relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => {
            acknowledgements += 1;
            await acknowledgement.promise;
          },
          rollback: async () => undefined,
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected read.");
      },
    };
    const service = new SnapshotArtifactService(store, gateway, { newId: () => "artifact" });

    const first = service.recordCompletedExportJob(principal, "project-1", "markdown");
    await waitUntil(() => acknowledgements === 1);
    await expect(
      service.recordCompletedExportJob(principal, "project-2", "markdown"),
    ).rejects.toBeInstanceOf(OperationCapacityExceededError);
    expect(store.sourceReads).toBe(1);

    acknowledgement.resolve();
    await expect(first).resolves.toBeDefined();
    await expect(
      service.recordCompletedExportJob(principal, "project-2", "markdown"),
    ).resolves.toBeDefined();
  });

  it("holds ownership through rollback and releases after cleanup completes", async () => {
    const landingFailure = new Error("landing failed");
    const store = new LifecycleStore(landingFailure);
    const rollback = deferred<void>();
    let rollbacks = 0;
    const gateway: A.ExportArtifactGateway = {
      async writeSnapshotArtifact(request) {
        return {
          relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => undefined,
          rollback: async () => {
            rollbacks += 1;
            await rollback.promise;
          },
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected read.");
      },
    };
    const service = new SnapshotArtifactService(store, gateway, { newId: () => "artifact" });

    const first = service.recordCompletedExportJob(principal, "project-1", "markdown");
    await waitUntil(() => rollbacks === 1);
    await expect(
      service.recordCompletedExportJob(principal, "project-2", "markdown"),
    ).rejects.toBeInstanceOf(OperationCapacityExceededError);
    rollback.resolve();
    await expect(first).rejects.toBe(landingFailure);
    await expect(service.recordCompletedExportJob(principal, "project-2", "markdown")).rejects.toBe(
      landingFailure,
    );
    expect(rollbacks).toBe(2);
  });
});

class LifecycleStore implements E.ExportOutcomeStore {
  sourceReads = 0;

  constructor(private readonly recordFailure?: Error) {}

  readExportSource(_scope: ProjectScope, projectId: string, capturedAt: Date): E.ExportSource {
    this.sourceReads += 1;
    return {
      projectId,
      projectTitle: "Bounded",
      capturedAt,
      reuseSnapshotId: "snapshot",
      documents: [
        {
          documentId: "chapter",
          revisionId: "revision",
          kind: "chapter",
          title: "Chapter",
          contentMarkdown: "Content",
          metadataJson: "{}",
          position: 1,
        },
      ],
    };
  }

  recordCompletedExportJob(_scope: ProjectScope, input: E.PreparedExportArtifact) {
    if (this.recordFailure !== undefined) throw this.recordFailure;
    const artifact = artifactRecord(input);
    return { artifact, job: completedJob(artifact) };
  }

  completeExportRetryJob(): E.ExportCompletionRecord {
    throw new Error("Unexpected retry.");
  }

  listProjectArtifacts(): E.ExportArtifactRecord[] {
    return [];
  }

  findProjectArtifact(): E.ExportArtifactRecord {
    throw new Error("Unexpected artifact lookup.");
  }
}

function artifactRecord(input: E.PreparedExportArtifact): E.ExportArtifactRecord {
  return {
    id: input.id,
    projectId: input.source.projectId,
    snapshotId: "snapshot",
    format: input.format,
    relativePath: input.relativePath,
    sizeBytes: input.sizeBytes,
    checksumSha256: input.checksumSha256,
    createdAt: input.createdAt,
  };
}

function completedJob(artifact: E.ExportArtifactRecord): E.ExportCompletionRecord["job"] {
  return {
    id: `job-${artifact.id}`,
    projectId: artifact.projectId,
    documentId: null,
    kind: "export",
    operation: "export",
    status: "completed",
    provider: "studio",
    model: "",
    requestJson: JSON.stringify({ format: artifact.format }),
    resultJson: JSON.stringify({ export_id: artifact.id }),
    error: null,
    retryOfJobId: null,
    createdAt: artifact.createdAt,
    updatedAt: artifact.createdAt,
    events: [],
  };
}

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

async function waitUntil(predicate: () => boolean): Promise<void> {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
  throw new Error("Timed out waiting for renderer lifecycle evidence.");
}
