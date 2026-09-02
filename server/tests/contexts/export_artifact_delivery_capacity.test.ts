import { EventEmitter } from "node:events";

import { describe, expect, it, vi } from "vitest";

import {
  type ExportArtifactGateway,
  SnapshotArtifactService,
} from "../../src/contexts/studio/application/export_artifact_service.js";
import type {
  ExportArtifactRecord,
  ExportOutcomeStore,
} from "../../src/contexts/studio/application/ports/export_store.js";
import {
  EXPORT_CAPACITY_LIMITS,
  ExportCapacityExceededError,
  NotFoundError,
  OperationCapacityExceededError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { sendWithinArtifactResponseLifetime } from "../../src/contexts/studio/interface/http/artifact_download_response_lifetime.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";

const principal: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};

function artifact(id: string, sizeBytes: number): ExportArtifactRecord {
  return {
    id,
    projectId: "project-1",
    snapshotId: "snapshot-1",
    format: "markdown",
    relativePath: `exports/project-1/${id}.md`,
    sizeBytes,
    checksumSha256: "a".repeat(64),
    createdAt: new Date(),
  };
}

function serviceFor(records: readonly ExportArtifactRecord[]) {
  const readArtifactBytes = vi.fn(async () => Buffer.from("safe"));
  const store = {
    findProjectArtifact(_scope: unknown, projectId: string, artifactId: string) {
      const record = records.find(
        (candidate) => candidate.projectId === projectId && candidate.id === artifactId,
      );
      if (record === undefined) throw new NotFoundError();
      return record;
    },
  } as ExportOutcomeStore;
  const gateway = { readArtifactBytes } as unknown as ExportArtifactGateway;
  return { service: new SnapshotArtifactService(store, gateway), readArtifactBytes };
}

describe("artifact delivery capacity ownership", () => {
  it("refuses a historical oversized artifact before reservation or file access", async () => {
    const { service, readArtifactBytes } = serviceFor([
      artifact("historical-oversized", EXPORT_CAPACITY_LIMITS.artifact_bytes + 1),
    ]);

    await expect(
      service.withArtifactDelivery(
        principal,
        "project-1",
        "historical-oversized",
        async () => undefined,
      ),
    ).rejects.toBeInstanceOf(ExportCapacityExceededError);
    expect(readArtifactBytes).not.toHaveBeenCalled();
  });

  it("holds byte reservations through consumers and releases them exactly once", async () => {
    const { service } = serviceFor([
      artifact("first", EXPORT_CAPACITY_LIMITS.artifact_bytes),
      artifact("second", EXPORT_CAPACITY_LIMITS.artifact_bytes),
      artifact("third", 1),
    ]);
    let finishFirst: (() => void) | undefined;
    let finishSecond: (() => void) | undefined;
    const first = service.withArtifactDelivery(
      principal,
      "project-1",
      "first",
      async () =>
        new Promise<void>((resolve) => {
          finishFirst = resolve;
        }),
    );
    const second = service.withArtifactDelivery(
      principal,
      "project-1",
      "second",
      async () =>
        new Promise<void>((resolve) => {
          finishSecond = resolve;
        }),
    );
    await expect.poll(() => finishFirst !== undefined && finishSecond !== undefined).toBe(true);

    await expect(
      service.withArtifactDelivery(principal, "project-1", "third", async () => undefined),
    ).rejects.toBeInstanceOf(OperationCapacityExceededError);
    finishFirst?.();
    await first;
    await expect(
      service.withArtifactDelivery(principal, "project-1", "third", async () => undefined),
    ).resolves.toBeUndefined();
    finishSecond?.();
    await second;
  });

  it("releases the reservation when the delivery consumer fails", async () => {
    const { service } = serviceFor([
      artifact("failed", EXPORT_CAPACITY_LIMITS.artifact_bytes),
      artifact("after-failure", EXPORT_CAPACITY_LIMITS.artifact_bytes),
    ]);
    const failure = new Error("delivery failed");

    await expect(
      service.withArtifactDelivery(principal, "project-1", "failed", async () => {
        throw failure;
      }),
    ).rejects.toBe(failure);
    await expect(
      service.withArtifactDelivery(principal, "project-1", "after-failure", async () => undefined),
    ).resolves.toBeUndefined();
  });

  it("releases when the client disconnects while verified bytes are still being read", async () => {
    const { service, readArtifactBytes } = serviceFor([
      artifact("disconnected", EXPORT_CAPACITY_LIMITS.artifact_bytes),
      artifact("after-disconnect", EXPORT_CAPACITY_LIMITS.artifact_bytes),
    ]);
    let finishRead: (() => void) | undefined;
    readArtifactBytes.mockImplementationOnce(async () => {
      await new Promise<void>((resolve) => {
        finishRead = resolve;
      });
      return Buffer.from("safe");
    });
    const response = Object.assign(new EventEmitter(), {
      writableFinished: false,
      destroyed: false,
    });
    const socket = Object.assign(new EventEmitter(), { destroyed: false });
    const disconnected = service.withArtifactDelivery(
      principal,
      "project-1",
      "disconnected",
      async () => sendWithinArtifactResponseLifetime({ response, socket, send: vi.fn() }),
    );
    await expect.poll(() => finishRead !== undefined).toBe(true);
    socket.destroyed = true;
    socket.emit("close");
    finishRead?.();

    await expect(disconnected).resolves.toBeUndefined();
    await expect(
      service.withArtifactDelivery(
        principal,
        "project-1",
        "after-disconnect",
        async () => undefined,
      ),
    ).resolves.toBeUndefined();
  });
});
