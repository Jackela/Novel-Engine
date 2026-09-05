export type StructureCapacityResource =
  | "project_documents"
  | "project_volumes"
  | "volume_chapters"
  | "project_settings_bytes"
  | "document_metadata_bytes"
  | "outline_beats";

/**
 * Fixed inclusive authoring-structure budgets (#461): no request, environment,
 * or configuration input may relax them. The limits gate only writes that add
 * new structure or grow a bounded scalar; stored pre-limit data is never
 * revalidated (the export/generation capacity pattern).
 */
export const STRUCTURE_CAPACITY_LIMITS = {
  project_documents: 2_500,
  project_volumes: 100,
  volume_chapters: 2_000,
  project_settings_bytes: 16_384,
  document_metadata_bytes: 16_384,
  outline_beats: 5_000,
} as const satisfies Readonly<Record<StructureCapacityResource, number>>;

/** The closed resource catalog rendered inside every refusal envelope. */
export const STRUCTURE_CAPACITY_RESOURCES = Object.freeze(
  Object.keys(STRUCTURE_CAPACITY_LIMITS) as StructureCapacityResource[],
);

const STRUCTURE_CAPACITY_RESOURCE_SET: ReadonlySet<string> = new Set(STRUCTURE_CAPACITY_RESOURCES);

/**
 * A gated authoring-structure write would exceed one fixed budget. Permanent
 * for unchanged input: removing structure is the only remedy, so the refusal
 * carries no retry hint.
 */
export class StructureCapacityExceededError extends Error {
  readonly resource: StructureCapacityResource;
  readonly limit: number;
  readonly observed: number;

  constructor(resource: StructureCapacityResource, limit: number, observed: number) {
    if (
      !STRUCTURE_CAPACITY_RESOURCE_SET.has(resource) ||
      !Number.isSafeInteger(limit) ||
      limit < 0 ||
      limit >= Number.MAX_SAFE_INTEGER ||
      !Number.isSafeInteger(observed) ||
      observed <= limit
    ) {
      throw new RangeError(
        "Structure capacity resource and values must identify a bounded safe-integer excess.",
      );
    }
    super("Authoring structure capacity exceeded.");
    this.name = "StructureCapacityExceededError";
    this.resource = resource;
    this.limit = limit;
    this.observed = Math.min(observed, limit + 1);
  }
}

/**
 * Refuse a request-derived settings/metadata JSON scalar whose serialized
 * UTF-8 size exceeds its fixed structure-capacity budget (#461), before any
 * store call can persist it. Pure policy: `Buffer` is a Node global, so the
 * domain keeps zero imports.
 */
export function assertSerializedCapacity(
  resource: "project_settings_bytes" | "document_metadata_bytes",
  serialized: string,
): void {
  const limit = STRUCTURE_CAPACITY_LIMITS[resource];
  const observed = Buffer.byteLength(serialized, "utf8");
  if (observed > limit) {
    throw new StructureCapacityExceededError(resource, limit, observed);
  }
}
