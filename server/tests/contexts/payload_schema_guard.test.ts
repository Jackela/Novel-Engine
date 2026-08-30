/**
 * Payload drift guard (#426): every builder in `payloads.ts` is validated
 * against the response schema its HTTP surface declares. Response schemas are
 * read directly from the current route schema modules (no snapshot baseline):
 * a builder that drops a field, retypes one, or grows an undeclared key turns
 * red here instead of drifting silently through fast-json-stringify, which
 * only serializes responses and never validates them.
 *
 * Strictness contract:
 * - Missing fields and mistyped fields fail via AJV (no coercion).
 * - OpenAPI-3.0 `nullable: true` is mapped to a draft-07 `["<type>", "null"]`
 *   union before compiling (see `toAjvSchema`); dropping `nullable` from a
 *   schema therefore also turns red via the null-bearing fixtures.
 * - `additionalProperties` keeps its current per-schema behavior; extra keys
 *   are caught by the explicit key-set guard `assertKeysDeclared`, because the
 *   hand-written resource schemas intentionally declare
 *   `additionalProperties: true` for forward compatibility.
 */

import { Ajv, type ValidateFunction } from "ajv";
import { describe, expect, it } from "vitest";

import {
  documentMatchPayload,
  documentPayload,
  jobPayload,
  projectPayload,
  revisionPayload,
  volumePayload,
} from "../../src/contexts/studio/application/payloads.js";
import type {
  DocumentMatchRecord,
  DocumentWithCurrent,
  JobRecord,
  RevisionRecord,
} from "../../src/contexts/studio/application/ports/studio_store.js";
import type { VolumeRecord } from "../../src/contexts/studio/application/ports/volume_store.js";
import { jobResponseSchema } from "../../src/contexts/studio/interface/http/job_schemas.js";
import {
  documentResponseSchema,
  matchResultSchema,
  projectDetailResponseSchema,
  projectResponseSchema,
  revisionResponseSchema,
} from "../../src/contexts/studio/interface/http/studio_schemas.js";
import { volumeResponseSchema } from "../../src/contexts/studio/interface/http/volume_schemas.js";

type SchemaNode = Record<string, unknown>;

const NOW = new Date("2026-01-15T10:30:00.000Z");

function revisionFixture(): RevisionRecord {
  return {
    id: "rev-1",
    documentId: "doc-1",
    parentRevisionId: "rev-0",
    revisionNumber: 2,
    contentMarkdown: "# Chapter One\n\nThe harbour wakes.",
    metadataJson: JSON.stringify({ pov: "Ada" }),
    source: "author",
    createdAt: NOW,
  };
}

function documentFixture(): DocumentWithCurrent {
  return {
    id: "doc-1",
    projectId: "proj-1",
    kind: "chapter",
    title: "Chapter One",
    position: 3,
    volumeId: "vol-1",
    beatRef: "beat-7",
    loreAliasesJson: "[]",
    currentRevisionId: "rev-1",
    createdAt: NOW,
    updatedAt: NOW,
    currentRevision: revisionFixture(),
  };
}

function volumeFixture(): VolumeRecord {
  return {
    id: "vol-1",
    projectId: "proj-1",
    title: "Act One",
    position: 1,
    createdAt: NOW,
    updatedAt: NOW,
  };
}

function matchFixture(): DocumentMatchRecord {
  return { documentId: "doc-1", title: "Chapter One", excerpt: "the harbour wakes" };
}

function jobFixture(): JobRecord {
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

function projectFixture() {
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
    delete mapped.nullable;
  }
  return mapped;
}

const ajv = new Ajv({ allErrors: true });
const compiled = new WeakMap<SchemaNode, ValidateFunction>();

/**
 * Extra-key guard: every emitted key must be declared in the schema's
 * `properties` (recursing through arrays and nested objects); objects without
 * declared properties (settings/metadata/request/result) stay free-form.
 */
function assertKeysDeclared(value: unknown, schema: SchemaNode, path: string): void {
  if (Array.isArray(value)) {
    const items = schema.items as SchemaNode | undefined;
    if (items === undefined) return;
    value.forEach((item, index) => {
      assertKeysDeclared(item, items, `${path}[${index}]`);
    });
    return;
  }
  if (value === null || typeof value !== "object") return;
  const properties = schema.properties as Record<string, SchemaNode> | undefined;
  if (properties === undefined) return;
  for (const [key, child] of Object.entries(value)) {
    const childSchema = properties[key];
    if (childSchema === undefined) {
      throw new Error(`Undeclared payload key at ${path}.${key} (drift against schema)`);
    }
    assertKeysDeclared(child, childSchema, `${path}.${key}`);
  }
}

/** Compile (once per schema) and run the AJV type/required/enum checks. */
function validateAgainstSchema(
  payload: Record<string, unknown>,
  schema: SchemaNode,
): ValidateFunction["errors"] {
  const cached = compiled.get(schema);
  const validate = cached ?? ajv.compile(toAjvSchema(schema) as SchemaNode);
  if (cached === undefined) compiled.set(schema, validate);
  return validate(payload) ? null : validate.errors;
}

/** Full strict validation: declared keys plus AJV type/required/enum checks. */
function assertConforms(payload: Record<string, unknown>, schema: SchemaNode): void {
  assertKeysDeclared(payload, schema, "$");
  const errors = validateAgainstSchema(payload, schema);
  if (errors !== null && errors !== undefined) {
    throw new Error(ajv.errorsText(errors, { dataVar: "payload" }));
  }
}

const CASES: Array<{ name: string; build: () => Record<string, unknown>; schema: SchemaNode }> = [
  {
    name: "projectPayload (list form) -> projectResponseSchema",
    build: () => projectPayload(projectFixture()),
    schema: projectResponseSchema as SchemaNode,
  },
  {
    name: "projectPayload (detail form) -> projectDetailResponseSchema",
    build: () => projectPayload(projectFixture(), [documentFixture()], [volumeFixture()]),
    schema: projectDetailResponseSchema as SchemaNode,
  },
  {
    name: "documentPayload (in volume) -> documentResponseSchema",
    build: () => documentPayload(documentFixture()),
    schema: documentResponseSchema as SchemaNode,
  },
  {
    name: "documentPayload (volumeless nulls) -> documentResponseSchema",
    build: () => documentPayload({ ...documentFixture(), volumeId: null, beatRef: null }),
    schema: documentResponseSchema as SchemaNode,
  },
  {
    name: "volumePayload -> volumeResponseSchema",
    build: () => volumePayload(volumeFixture()),
    schema: volumeResponseSchema as SchemaNode,
  },
  {
    name: "documentMatchPayload -> matchResultSchema",
    build: () => documentMatchPayload(matchFixture()),
    schema: matchResultSchema as SchemaNode,
  },
  {
    name: "revisionPayload -> revisionResponseSchema",
    build: () => revisionPayload(revisionFixture()),
    schema: revisionResponseSchema as SchemaNode,
  },
  {
    name: "jobPayload -> jobResponseSchema",
    build: () => jobPayload(jobFixture()),
    schema: jobResponseSchema as SchemaNode,
  },
];

describe("payload builders conform to their response schemas", () => {
  it.each(CASES)("validates $name", ({ build, schema }) => {
    expect(() => assertConforms(build(), schema)).not.toThrow();
  });
});

/** First schema-required key; every guarded schema requires at least one. */
function firstRequired(schema: SchemaNode): string {
  const required = schema.required as string[] | undefined;
  const key = required?.[0];
  if (key === undefined) throw new Error("schema declares no required fields");
  return key;
}

describe("payload drift guard trips on every drift class", () => {
  it.each(CASES)("rejects an undeclared extra field in $name", ({ build, schema }) => {
    const drifted = { ...build(), drift_extra_field: true };
    expect(() => assertConforms(drifted, schema)).toThrow(/Undeclared payload key/);
  });

  it.each(CASES)("rejects a missing required field in $name", ({ build, schema }) => {
    const payload = build();
    delete payload[firstRequired(schema)];
    expect(() => assertConforms(payload, schema)).toThrow(/required/);
  });

  it.each(CASES)("rejects a mistyped field in $name", ({ build, schema }) => {
    const payload = build();
    payload[firstRequired(schema)] = { drifted: "object" };
    expect(() => assertConforms(payload, schema)).toThrow(/must be/);
  });
});
