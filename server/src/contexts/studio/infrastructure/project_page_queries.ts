import { and, desc, eq, sql } from "drizzle-orm";

import type { ProjectPageInput } from "../application/ports/project_catalog_store.js";
import type { ProjectScope } from "../application/ports/studio_store.js";
import { projects } from "./db/schema.js";
import type { Tx } from "./db/studio_query_helpers.js";

/** Summary-only keyset query; settings/import metadata stay server authority. */
export function buildProjectCatalogSummariesQuery(
  tx: Tx,
  scope: ProjectScope,
  input: ProjectPageInput,
) {
  const cursorRange =
    input.cursor === undefined
      ? undefined
      : sql`(${projects.updatedAt}, ${projects.id}) < (${input.cursor.updatedAtMs}, ${input.cursor.id})`;
  return tx
    .select({
      id: projects.id,
      title: projects.title,
      description: projects.description,
      createdAt: projects.createdAt,
      updatedAt: projects.updatedAt,
    })
    .from(projects)
    .where(and(eq(projects.ownerId, scope.ownerId), cursorRange))
    .orderBy(desc(projects.updatedAt), desc(projects.id))
    .limit(input.limit + 1);
}
