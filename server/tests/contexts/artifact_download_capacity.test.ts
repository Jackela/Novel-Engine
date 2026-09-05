import { describe, expect, it } from "vitest";

import {
  ARTIFACT_DOWNLOAD_POOL_BYTES,
  ArtifactDownloadCapacity,
} from "../../src/contexts/studio/application/artifact_download_capacity.js";
import { EXPORT_CAPACITY_LIMITS } from "../../src/contexts/studio/domain/exceptions.js";

describe("artifact download byte capacity", () => {
  it.each([-1, 0.5, Number.POSITIVE_INFINITY, Number.MAX_SAFE_INTEGER + 1])(
    "rejects invalid reservation size %s before changing capacity",
    (invalidSize) => {
      const capacity = new ArtifactDownloadCapacity();

      expect(() => capacity.acquire("project-invalid", invalidSize)).toThrow(RangeError);

      const full = capacity.acquire("project-valid", ARTIFACT_DOWNLOAD_POOL_BYTES);
      full.release();
    },
  );

  it("holds two maximum artifacts, admits zero, and rejects the next positive byte", () => {
    const capacity = new ArtifactDownloadCapacity();
    const first = capacity.acquire("project-1", EXPORT_CAPACITY_LIMITS.artifact_bytes);
    const second = capacity.acquire("project-2", EXPORT_CAPACITY_LIMITS.artifact_bytes);
    const zero = capacity.acquire("project-3", 0);

    expect(ARTIFACT_DOWNLOAD_POOL_BYTES).toBe(2 * EXPORT_CAPACITY_LIMITS.artifact_bytes);
    expect(() => capacity.acquire("project-3", 1)).toThrowError(
      expect.objectContaining({
        scope: "application",
        limit: ARTIFACT_DOWNLOAD_POOL_BYTES,
        inFlight: ARTIFACT_DOWNLOAD_POOL_BYTES,
        projectId: "project-3",
      }),
    );

    zero.release();
    first.release();
    first.release();
    expect(() => capacity.acquire("project-3", 1)).not.toThrow();
    second.release();
  });

  it("uses generation-safe ownership when old permits release repeatedly", () => {
    const capacity = new ArtifactDownloadCapacity();
    const old = capacity.acquire("project-1", ARTIFACT_DOWNLOAD_POOL_BYTES);
    old.release();
    const current = capacity.acquire("project-2", ARTIFACT_DOWNLOAD_POOL_BYTES);

    old.release();
    expect(() => capacity.acquire("project-3", 1)).toThrow();
    current.release();
    expect(() => capacity.acquire("project-3", 1)).not.toThrow();
  });
});
