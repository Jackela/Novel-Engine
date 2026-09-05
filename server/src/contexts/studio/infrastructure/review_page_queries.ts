import { and, desc, eq, sql } from "drizzle-orm";

import type { ReviewPageInput } from "../application/ports/review_outcome_store.js";
import { reviews } from "./db/schema.js";
import type { Tx } from "./db/studio_query_helpers.js";

/** Build the exact keyset query executed by the review-history listing. */
export function buildReviewSummariesQuery(tx: Tx, projectId: string, input: ReviewPageInput) {
  const cursorRange =
    input.cursor === undefined
      ? undefined
      : sql`(${reviews.createdAt}, ${reviews.id}) < (${input.cursor.createdAtMs}, ${input.cursor.id})`;
  return tx
    .select({
      id: reviews.id,
      projectId: reviews.projectId,
      snapshotId: reviews.snapshotId,
      provider: reviews.provider,
      model: reviews.model,
      summary: reviews.summary,
      createdAt: reviews.createdAt,
    })
    .from(reviews)
    .where(and(eq(reviews.projectId, projectId), cursorRange))
    .orderBy(desc(reviews.createdAt), desc(reviews.id))
    .limit(input.limit + 1);
}
