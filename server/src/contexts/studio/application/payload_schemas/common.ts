import { Type } from "@fastify/type-provider-typebox";

/**
 * TypeBox single source of truth for studio HTTP payload shapes (#433): every
 * core resource payload (document, revision, project, job, volume) and its
 * nested forms is declared once here; `payloads.ts` builders type their
 * return values with `Static` and the interface layer declares the same
 * objects as response schemas, so builder and schema can no longer drift.
 *
 * Primitives shared by the per-resource schema modules live below.
 */

/**
 * Free-form stored JSON (document/revision metadata, project settings, job
 * request/result, job-event details). These are genuinely dynamic payloads,
 * so they keep `additionalProperties: true`; every declared resource object
 * itself is strict (`additionalProperties: false`).
 */
export const freeFormObject = Type.Unsafe<Record<string, unknown>>({
  type: "object",
  additionalProperties: true,
});

/**
 * The OpenAPI-3.0 `nullable: true` representation (#405 precedent): kept as
 * the literal schema shape instead of a `Type.Union` with `Type.Null()`, so
 * fast-json-stringify and the frozen snapshot see the exact same JSON Schema
 * as before and coercing AJV cannot reinterpret explicit nulls.
 */
export const nullableString = Type.Unsafe<string | null>({
  type: "string",
  nullable: true,
});
