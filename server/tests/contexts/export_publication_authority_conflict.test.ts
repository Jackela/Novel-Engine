import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";
import {
  exports as exportArtifacts,
  projectSnapshots,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { reconcileExportPublications } from "../../src/contexts/studio/infrastructure/export_publication_recovery.js";
import {
  cleanupRecoveryHarnesses,
  openRecoveryHarness,
  RECOVERY_NOW,
} from "./export_publication_recovery_fixture.js";

afterEach(cleanupRecoveryHarnesses);

describe("export publication authority conflicts", () => {
  it("preserves a missing-project tree when a committed artifact still references it", async () => {
    const value = await openRecoveryHarness();
    const projectId = "orphan-project-with-evidence";
    const snapshotId = "orphan-snapshot-with-evidence";
    const artifactId = "orphan-artifact-with-evidence";
    const bytes = Buffer.from("committed bytes outlive a corrupt project row");
    const directory = join(value.directory, "exports", projectId);
    const target = join(directory, `${artifactId}.md`);
    await mkdir(directory, { recursive: true });
    await writeFile(target, bytes);
    value.studio.raw.pragma("foreign_keys = OFF");
    try {
      value.studio.db
        .insert(projectSnapshots)
        .values({ id: snapshotId, projectId, reason: "export", createdAt: RECOVERY_NOW })
        .run();
      value.studio.db
        .insert(exportArtifacts)
        .values({
          id: artifactId,
          projectId,
          snapshotId,
          format: "markdown",
          relativePath: `exports/${projectId}/${artifactId}.md`,
          sizeBytes: bytes.length,
          checksumSha256: createHash("sha256").update(bytes).digest("hex"),
          createdAt: RECOVERY_NOW,
        })
        .run();
    } finally {
      value.studio.raw.pragma("foreign_keys = ON");
    }

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /committed export evidence references missing project/i,
    );
    await expect(readFile(target)).resolves.toEqual(bytes);
  });
});
