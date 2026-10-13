import { OperationCapacityExceededError } from "../domain/exceptions.js";

export const ARTIFACT_DOWNLOAD_POOL_BYTES = 134_217_728;

interface ArtifactDownloadPermit {
  release(): void;
}

/** App-local, byte-weighted ownership for artifact response Buffers. */
export class ArtifactDownloadCapacity {
  private reservedBytes = 0;

  acquire(projectId: string, sizeBytes: number): ArtifactDownloadPermit {
    if (!Number.isSafeInteger(sizeBytes) || sizeBytes < 0) {
      throw new RangeError("Artifact download size must be a non-negative safe integer.");
    }
    if (
      sizeBytes > 0 &&
      (this.reservedBytes > ARTIFACT_DOWNLOAD_POOL_BYTES - sizeBytes ||
        sizeBytes > ARTIFACT_DOWNLOAD_POOL_BYTES)
    ) {
      throw new OperationCapacityExceededError(
        "application",
        ARTIFACT_DOWNLOAD_POOL_BYTES,
        this.reservedBytes,
        projectId,
      );
    }
    this.reservedBytes += sizeBytes;
    let released = false;
    return {
      release: () => {
        if (released) return;
        released = true;
        this.reservedBytes -= sizeBytes;
      },
    };
  }
}
