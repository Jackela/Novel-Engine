/**
 * Shared harness for the payload drift guards (`payload_schema_guard*.test.ts`):
 * the AJV bridge that compiles the TypeBox payload SSOT exactly as the routes
 * hand it to fast-json-stringify, plus the store-record fixtures the guard
 * files build their payloads from. Kept outside the vitest test-file glob on
 * purpose; the file-size gate measures each test file separately (#440).
 *
 * Strictness contract:
 * - Resource objects are strict (`additionalProperties: false`): extra keys
 *   fail via AJV itself, alongside missing/mistyped fields (no coercion).
 * - OpenAPI-3.0 `nullable: true` is mapped to a draft-07 `["<type>", "null"]`
 *   union before compiling (see `toAjvSchema`); dropping `nullable` from a
 *   schema therefore also turns red via the null-bearing fixtures.
 * - `date-time` (review/export `created_at`, #440) is registered as a
 *   pass-through format: the HTTP layer validates formats via Fastify's AJV
 *   with `ajv-formats`; this guard pins shape drift, not format semantics.
 */

import { Ajv, type ValidateFunction } from "ajv";
import type {
  DocumentMatchRecord,
  DocumentSummaryRecord,
  DocumentWithCurrent,
  JobRecord,
  RevisionRecord,
} from "../../src/contexts/studio/application/ports/studio_store.js";
import type { VolumeRecord } from "../../src/contexts/studio/application/ports/volume_store.js";

export type SchemaNode = Record<string, unknown>;

export const NOW = new Date("2026-01-15T10:30:00.000Z");

export function revisionFixture(): RevisionRecord {
  return {
    id: "rev-1",
    documentId: "doc-1",
    parentRevisionId: "rev-0",
    revisionNumber: 2,
    contentMarkdown: "# Chapter One\n\nThe harbour wakes.",
    metadataJson: JSON.stringify({ pov: "Ada" }),
    source: "author",
    wordCount: 5,
    createdAt: NOW,
  };
}

export function documentFixture(): DocumentWithCurrent {
  return {
    id: "doc-1",
    projectId: "proj-1",
    kind: "chapter",
    title: "Chapter One",
    position: 3,
    volumeId: "vol-1",
    beatRef: "beat-7",
    loreAliasesJson: "[]",
    loreStatus: "stable",
    currentRevisionId: "rev-1",
    createdAt: NOW,
    updatedAt: NOW,
    currentRevision: revisionFixture(),
  };
}

export function documentSummaryFixture(): DocumentSummaryRecord {
  const document = documentFixture();
  return {
    id: document.id,
    projectId: document.projectId,
    kind: document.kind,
    title: document.title,
    position: document.position,
    volumeId: document.volumeId,
    beatRef: document.beatRef,
    loreStatus: document.loreStatus,
    currentRevisionId: "rev-1",
    revisionSource: "author",
    wordCount: 5,
    createdAt: document.createdAt,
    updatedAt: document.updatedAt,
  };
}

export function volumeFixture(): VolumeRecord {
  return {
    id: "vol-1",
    projectId: "proj-1",
    title: "Act One",
    position: 1,
    createdAt: NOW,
    updatedAt: NOW,
  };
}

export function matchFixture(): DocumentMatchRecord {
  return { documentId: "doc-1", title: "Chapter One", excerpt: "the harbour wakes" };
}

export function jobFixture(): JobRecord {
  return {
    id: "job-1",
    projectId: "proj-1",
    documentId: "doc-1",
    kind: "proposal",
    operation: "chapter-draft",
    status: "succeeded",
    provider: "mock",
    model: "mock-small",
    requestJson: JSON.stringify({ brief: "draft it" }),
    resultJson: JSON.stringify({ revision_id: "rev-1" }),
    error: null,
    retryOfJobId: null,
    createdAt: NOW,
    updatedAt: NOW,
    events: [
      {
        id: "evt-1",
        jobId: "job-1",
        status: "succeeded",
        detailsJson: JSON.stringify({ note: "done" }),
        createdAt: NOW,
      },
    ],
  };
}

export function projectFixture() {
  return {
    id: "proj-1",
    title: "Harbour Lights",
    description: "A novel about tides.",
    settingsJson: JSON.stringify({ genre: "literary" }),
    importHash: null,
    createdAt: NOW,
    updatedAt: NOW,
  };
}

/** Map OpenAPI-3.0 `nullable` onto a draft-07 union type, recursively. */
function toAjvSchema(node: unknown): unknown {
  if (Array.isArray(node)) return node.map(toAjvSchema);
  if (node === null || typeof node !== "object") return node;
  const mapped: SchemaNode = {};
  for (const [key, value] of Object.entries(node)) mapped[key] = toAjvSchema(value);
  if (mapped.nullable === true && typeof mapped.type === "string") {
    mapped.type = [mapped.type, "null"];
    // Nullable enum members (#444 `lore_status`): OpenAPI 3.0 semantics make
    // null a legal value alongside the closed set, so the draft-07 projection
    // must admit it or every null-bearing fixture turns red.
    if (Array.isArray(mapped.enum) && !mapped.enum.includes(null)) {
      mapped.enum = [...mapped.enum, null];
    }
    delete mapped.nullable;
  }
  return mapped;
}

const ajv = new Ajv({ allErrors: true, formats: { "date-time": true } });
const compiled = new WeakMap<SchemaNode, ValidateFunction>();

/** Compile (once per schema) and run the AJV strictness checks. */
function validateAgainstSchema(
  payload: Record<string, unknown>,
  schema: SchemaNode,
): ValidateFunction["errors"] {
  const cached = compiled.get(schema);
  const validate = cached ?? ajv.compile(toAjvSchema(schema) as SchemaNode);
  if (cached === undefined) compiled.set(schema, validate);
  return validate(payload) ? null : validate.errors;
}

/** Full strict validation of a builder payload against its SSOT schema. */
export function assertConforms(payload: Record<string, unknown>, schema: SchemaNode): void {
  const errors = validateAgainstSchema(payload, schema);
  if (errors !== null && errors !== undefined) {
    throw new Error(ajv.errorsText(errors, { dataVar: "payload" }));
  }
}

/** First schema-required key; every guarded schema requires at least one. */
export function firstRequired(schema: SchemaNode): string {
  const required = schema.required as string[] | undefined;
  const key = required?.[0];
  if (key === undefined) throw new Error("schema declares no required fields");
  return key;
}
