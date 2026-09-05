import type { ProjectScope } from "./studio_store.js";

/** Project-row shapes for the bounded owner catalog (#458). */

/**
 * Lightweight catalog item; settings and import metadata stay on the
 * project shell/detail surface and never enter the list read.
 */
export interface ProjectCatalogSummaryRecord {
  id: string;
  title: string;
  description: string;
  createdAt: Date;
  updatedAt: Date;
}

/** The validated row budget of one bounded project catalog page. */
export type ProjectPageLimit = number & { readonly __projectPageLimit: unique symbol };

/** Inclusive application/store boundary for one catalog page. */
export const MIN_PROJECT_PAGE_LIMIT = 1;
export const MAX_PROJECT_PAGE_LIMIT = 100;

/** Validate and narrow a catalog-page budget before persistence. */
export function projectPageLimit(value: number): ProjectPageLimit {
  if (
    !Number.isInteger(value) ||
    value < MIN_PROJECT_PAGE_LIMIT ||
    value > MAX_PROJECT_PAGE_LIMIT
  ) {
    throw new RangeError(
      `Project page limit must be an integer from ${MIN_PROJECT_PAGE_LIMIT} through ${MAX_PROJECT_PAGE_LIMIT}.`,
    );
  }
  return value as ProjectPageLimit;
}

/** Persistence-neutral exclusive position in `(updated_at DESC, id DESC)` order. */
export interface ProjectPageCursor {
  readonly updatedAtMs: number;
  readonly id: string;
}

/** One typed keyset request; the first page omits its exclusive cursor. */
export interface ProjectPageInput {
  readonly limit: ProjectPageLimit;
  readonly cursor?: ProjectPageCursor | undefined;
}

/** One bounded page and the exclusive position required to continue it. */
export interface ProjectCatalogPage {
  readonly projects: ProjectCatalogSummaryRecord[];
  readonly nextCursor: ProjectPageCursor | null;
}

/** The owner-scoped catalog read surface of the studio store. */
export interface ProjectCatalogStore {
  findProjectCatalogSummaries(scope: ProjectScope, input: ProjectPageInput): ProjectCatalogPage;
}
