import { Readable } from "node:stream";

import { describe, expect, it } from "vitest";

import {
  EXPORT_CAPACITY_LIMITS,
  ExportCapacityExceededError,
} from "../../src/contexts/studio/domain/exceptions.js";
import {
  assertArtifactByteLength,
  collectBoundedArtifactStream,
} from "../../src/contexts/studio/infrastructure/bounded_export_rendering.js";

describe("bounded export rendering", () => {
  it.each(["markdown", "docx", "epub"] as const)(
    "accepts the exact artifact limit and rejects the next %s byte",
    (format) => {
      expect(() =>
        assertArtifactByteLength(format, EXPORT_CAPACITY_LIMITS.artifact_bytes),
      ).not.toThrow();
      expect(() =>
        assertArtifactByteLength(format, EXPORT_CAPACITY_LIMITS.artifact_bytes + 1),
      ).toThrow(
        expect.objectContaining({
          resource: "artifact_bytes",
          limit: EXPORT_CAPACITY_LIMITS.artifact_bytes,
          observed: EXPORT_CAPACITY_LIMITS.artifact_bytes + 1,
        }),
      );
    },
  );

  it("stops a stream at the first byte beyond its sink budget without truncating", async () => {
    const accepted = await collectBoundedArtifactStream(Readable.from(["ab", "中"]), 5);
    expect(accepted).toEqual(Buffer.from("ab中"));

    await expect(
      collectBoundedArtifactStream(Readable.from(["ab", "中", "x"]), 5),
    ).rejects.toBeInstanceOf(ExportCapacityExceededError);
  });
});
