import { mkdtemp, readdir, truncate } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import type { ArtifactWriteRequest } from "../../src/contexts/studio/application/export_artifact_service.js";
import {
  EXPORT_CAPACITY_LIMITS,
  ExportCapacityExceededError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";

describe("export publication capacity", () => {
  it("rejects an oversized staged descriptor before manifest or final publication", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-publication-capacity-"));
    const gateway = new FilesystemExportArtifactGateway(directory, {
      afterStageWrite: async (stage) => {
        await truncate(stage, EXPORT_CAPACITY_LIMITS.artifact_bytes + 1);
      },
    });

    await expect(gateway.writeSnapshotArtifact(request())).rejects.toBeInstanceOf(
      ExportCapacityExceededError,
    );
    const projectDirectory = join(directory, "exports", "project-1");
    expect(await readdir(projectDirectory)).toEqual([".staging"]);
    expect(await readdir(join(projectDirectory, ".staging"))).toEqual([]);
  });
});

function request(): ArtifactWriteRequest {
  return {
    projectId: "project-1",
    artifactId: "oversized-stage",
    format: "markdown",
    projectTitle: "Bounded",
    chapters: [{ title: "Chapter", contentMarkdown: "content" }],
  };
}
