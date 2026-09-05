import { and, desc, eq, sql } from "drizzle-orm";

import type { ExportPageInput } from "../application/ports/export_store.js";
import { exports as exportArtifacts } from "./db/schema.js";
import type { Tx } from "./db/studio_query_helpers.js";

/** Build the exact keyset query executed by the export catalog listing. */
export function buildProjectArtifactPageQuery(tx: Tx, projectId: string, input: ExportPageInput) {
  const cursorRange =
    input.cursor === undefined
      ? undefined
      : sql`(${exportArtifacts.createdAt}, ${exportArtifacts.id}) < (${input.cursor.createdAtMs}, ${input.cursor.id})`;
  return tx
    .select({
      id: exportArtifacts.id,
      projectId: exportArtifacts.projectId,
      snapshotId: exportArtifacts.snapshotId,
      format: exportArtifacts.format,
      relativePath: exportArtifacts.relativePath,
      sizeBytes: exportArtifacts.sizeBytes,
      checksumSha256: exportArtifacts.checksumSha256,
      createdAt: exportArtifacts.createdAt,
    })
    .from(exportArtifacts)
    .where(and(eq(exportArtifacts.projectId, projectId), cursorRange))
    .orderBy(desc(exportArtifacts.createdAt), desc(exportArtifacts.id))
    .limit(input.limit + 1);
}
