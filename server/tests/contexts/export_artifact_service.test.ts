import { mkdtemp, readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type * as A from "../../src/contexts/studio/application/export_artifact_service.js";
import { SnapshotArtifactService } from "../../src/contexts/studio/application/export_artifact_service.js";
import type * as E from "../../src/contexts/studio/application/ports/export_store.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";

const principal: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};

class FakeExportStore implements E.ExportOutcomeStore {
  readonly appended: E.ExportArtifactRecord[] = [];

  constructor(
    private readonly documents: readonly E.ExportSourceDocument[],
    private readonly recordFailure: Error | undefined = undefined,
  ) {}

  readExportSource(_scope: ProjectScope, projectId: string, capturedAt: Date): E.ExportSource {
    return {
      projectId,
      projectTitle: "Ashfall",
      capturedAt,
      reuseSnapshotId: "snapshot-1",
      documents: this.documents,
    };
  }

  recordCompletedExportJob(
    _scope: ProjectScope,
    input: E.PreparedExportArtifact,
  ): E.ExportCompletionRecord {
    if (this.recordFailure !== undefined) throw this.recordFailure;
    const artifact = artifactRecord(input);
    this.appended.push(artifact);
    return { artifact, job: completedJob(artifact) };
  }

  completeExportRetryJob(): E.ExportCompletionRecord {
    throw new Error("Unexpected export retry write.");
  }

  listProjectArtifacts(): E.ExportArtifactRecord[] {
    return [...this.appended];
  }

  findProjectArtifact(
    _scope: ProjectScope,
    _projectId: string,
    artifactId: string,
  ): E.ExportArtifactRecord {
    const record = this.appended.find((item) => item.id === artifactId);
    if (record === undefined) throw new NotFoundError();
    return record;
  }
}

function artifactRecord(input: E.PreparedExportArtifact): E.ExportArtifactRecord {
  return {
    id: input.id,
    projectId: input.source.projectId,
    snapshotId: input.source.reuseSnapshotId ?? "snapshot-1",
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
    resultJson: JSON.stringify({ export_id: artifact.id, snapshot_id: artifact.snapshotId }),
    error: null,
    retryOfJobId: null,
    createdAt: artifact.createdAt,
    updatedAt: artifact.createdAt,
    events: [],
  };
}

class RecordingGateway implements A.ExportArtifactGateway {
  readonly writes: A.ArtifactWriteRequest[] = [];
  readonly reads: A.ArtifactReadRequest[] = [];

  async writeSnapshotArtifact(
    requestValue: A.ArtifactWriteRequest,
  ): Promise<A.ArtifactFileEvidence> {
    this.writes.push(requestValue);
    const extension = requestValue.format === "markdown" ? "md" : requestValue.format;
    return {
      relativePath: `exports/${requestValue.projectId}/${requestValue.artifactId}.${extension}`,
      sizeBytes: 1,
      checksumSha256: "a".repeat(64),
      rollback: async () => undefined,
    };
  }

  async readArtifactBytes(input: A.ArtifactReadRequest): Promise<Buffer> {
    this.reads.push(input);
    return Buffer.from("safe");
  }
}

function snapshotDocument(id: string, kind: string, title: string): E.ExportSourceDocument {
  return {
    documentId: id,
    revisionId: `revision-${id}`,
    kind,
    title,
    contentMarkdown: `${title} content`,
    metadataJson: "{}",
    position: 1,
  };
}

function writeRequest(
  format: A.ArtifactWriteRequest["format"],
  artifactId: string,
  projectId = "project-1",
): A.ArtifactWriteRequest {
  return {
    projectId,
    artifactId,
    format,
    projectTitle: "Ashfall",
    chapters: [{ title: "Chapter", contentMarkdown: "Chapter content" }],
  };
}

function readRequest(
  evidence: Pick<A.ArtifactFileEvidence, "relativePath" | "sizeBytes" | "checksumSha256">,
  artifactId: string,
  format: A.ArtifactWriteRequest["format"],
): A.ArtifactReadRequest {
  const { relativePath, sizeBytes, checksumSha256 } = evidence;
  return {
    projectId: "project-1",
    artifactId,
    format,
    relativePath,
    sizeBytes,
    checksumSha256,
  };
}

describe("SnapshotArtifactService", () => {
  it("renders frozen chapters and forwards all authorized evidence for buffer delivery", async () => {
    const store = new FakeExportStore([
      snapshotDocument("outline", "outline", "Outline"),
      snapshotDocument("second", "chapter", "Second"),
      snapshotDocument("first", "chapter", "First"),
    ]);
    const gateway = new RecordingGateway();
    let sequence = 0;
    const service = new SnapshotArtifactService(store, gateway, {
      now: () => new Date("2026-08-25T00:00:00.000Z"),
      newId: () => `artifact-${++sequence}`,
    });
    const completions = await Promise.all(
      (["markdown", "docx", "epub"] as const).map((format) =>
        service.recordCompletedExportJob(principal, "project-1", format),
      ),
    );
    const records = completions.map((completion) => completion.artifact);
    expect(
      gateway.writes.every(
        (write) => write.chapters.map((chapter) => chapter.title).join() === "Second,First",
      ),
    ).toBe(true);
    expect(records.every((record) => record.snapshotId === "snapshot-1")).toBe(true);
    await expect(service.readArtifactBytes(principal, "project-1", "artifact-1")).resolves.toEqual(
      Buffer.from("safe"),
    );
    const [firstRecord] = records;
    if (firstRecord === undefined) throw new Error("Expected the first artifact record.");
    expect(gateway.reads).toEqual([readRequest(firstRecord, "artifact-1", "markdown")]);
  });

  it("refuses cross-project path substitution even when the other file is in root", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const other = await gateway.writeSnapshotArtifact(
      writeRequest("markdown", "shared", "project-2"),
    );
    const store = new FakeExportStore([]);
    store.appended.push({
      id: "shared",
      projectId: "project-1",
      snapshotId: "snapshot-1",
      format: "markdown",
      ...other,
      createdAt: new Date(),
    });
    await expect(
      new SnapshotArtifactService(store, gateway).readArtifactBytes(
        principal,
        "project-1",
        "shared",
      ),
    ).rejects.toThrow(NotFoundError);
  });

  it("rolls a new publication back when artifact persistence fails", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const store = new FakeExportStore(
      [snapshotDocument("chapter", "chapter", "Chapter")],
      new Error("append failed"),
    );
    const service = new SnapshotArtifactService(store, gateway, { newId: () => "orphan" });
    await expect(
      service.recordCompletedExportJob(principal, "project-1", "markdown"),
    ).rejects.toThrow("append failed");
    expect(await readdir(join(directory, "exports", "project-1"))).toEqual([]);
  });

  it("reports one rollback failure without replacing the persistence error", async () => {
    const persistenceFailure = new Error("atomic landing failed");
    const cleanupFailure = new Error("artifact cleanup failed");
    const store = new FakeExportStore(
      [snapshotDocument("chapter", "chapter", "Chapter")],
      persistenceFailure,
    );
    let rollbackCalls = 0;
    const gateway: A.ExportArtifactGateway = {
      async writeSnapshotArtifact() {
        return {
          relativePath: "exports/project-1/orphan.md",
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          rollback: async () => {
            rollbackCalls += 1;
            throw cleanupFailure;
          },
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected artifact read.");
      },
    };
    const reported: unknown[] = [];
    const service = new SnapshotArtifactService(store, gateway, { newId: () => "orphan" });

    await expect(
      service.recordCompletedExportJob(principal, "project-1", "markdown", {
        reportCleanupFailure: (failure) => {
          reported.push(failure);
          throw new Error("reporter failed too");
        },
      }),
    ).rejects.toBe(persistenceFailure);
    expect(rollbackCalls).toBe(1);
    expect(reported).toEqual([cleanupFailure]);
  });

  it("rejects snapshots without chapters before a file or record is written", async () => {
    const store = new FakeExportStore([snapshotDocument("outline", "outline", "Outline")]);
    const gateway = new RecordingGateway();
    await expect(
      new SnapshotArtifactService(store, gateway).recordCompletedExportJob(
        principal,
        "project-1",
        "markdown",
      ),
    ).rejects.toThrow(InvalidOperationError);
    expect(gateway.writes).toEqual([]);
    expect(store.appended).toEqual([]);
  });
});
