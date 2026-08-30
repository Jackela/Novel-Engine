/**
 * Payload drift guard (#426, #433): every builder in `payloads.ts` is
 * validated against the TypeBox payload SSOT its HTTP surface declares
 * (`application/payload_schemas/`). Builders type their output with `Static`
 * of these very schemas, so compile-time drift is already impossible; this
 * guard pins the runtime half — a fixture-built payload must validate against
 * the same schema object the routes serialize with. Fast-json-stringify only
 * serializes and never validates, so this test is where drift would turn red.
 *
 * Strictness contract:
 * - Resource objects are strict (`additionalProperties: false`): extra keys
 *   fail via AJV itself, alongside missing/mistyped fields (no coercion).
 * - OpenAPI-3.0 `nullable: true` is mapped to a draft-07 `["<type>", "null"]`
 *   union before compiling (see `toAjvSchema`); dropping `nullable` from a
 *   schema therefore also turns red via the null-bearing fixtures.
 * - Free-form stored JSON (metadata/settings/request/result/details) keeps
 *   `additionalProperties: true` and stays exempt from the extra-key check.
 */

import { Ajv, type ValidateFunction } from "ajv";
import { describe, expect, it } from "vitest";
import {
  documentPayloadSchema,
  matchResultPayloadSchema,
} from "../../src/contexts/studio/application/payload_schemas/document.js";
import { jobPayloadSchema } from "../../src/contexts/studio/application/payload_schemas/job.js";
import {
  projectDetailPayloadSchema,
  projectPayloadSchema,
} from "../../src/contexts/studio/application/payload_schemas/project.js";
import { revisionPayloadSchema } from "../../src/contexts/studio/application/payload_schemas/revision.js";
import { volumePayloadSchema } from "../../src/contexts/studio/application/payload_schemas/volume.js";
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
function assertConforms(payload: Record<string, unknown>, schema: SchemaNode): void {
  const errors = validateAgainstSchema(payload, schema);
  if (errors !== null && errors !== undefined) {
    throw new Error(ajv.errorsText(errors, { dataVar: "payload" }));
  }
}

const CASES: Array<{ name: string; build: () => Record<string, unknown>; schema: SchemaNode }> = [
  {
    name: "projectPayload (list form) -> projectPayloadSchema",
    build: () => projectPayload(projectFixture()),
    schema: projectPayloadSchema as unknown as SchemaNode,
  },
  {
    name: "projectPayload (detail form) -> projectDetailPayloadSchema",
    build: () => projectPayload(projectFixture(), [documentFixture()], [volumeFixture()]),
    schema: projectDetailPayloadSchema as unknown as SchemaNode,
  },
  {
    name: "documentPayload (in volume) -> documentPayloadSchema",
    build: () => documentPayload(documentFixture()),
    schema: documentPayloadSchema as unknown as SchemaNode,
  },
  {
    name: "documentPayload (volumeless nulls) -> documentPayloadSchema",
    build: () => documentPayload({ ...documentFixture(), volumeId: null, beatRef: null }),
    schema: documentPayloadSchema as unknown as SchemaNode,
  },
  {
    name: "volumePayload -> volumePayloadSchema",
    build: () => volumePayload(volumeFixture()),
    schema: volumePayloadSchema as unknown as SchemaNode,
  },
  {
    name: "documentMatchPayload -> matchResultPayloadSchema",
    build: () => documentMatchPayload(matchFixture()),
    schema: matchResultPayloadSchema as unknown as SchemaNode,
  },
  {
    name: "revisionPayload -> revisionPayloadSchema",
    build: () => revisionPayload(revisionFixture()),
    schema: revisionPayloadSchema as unknown as SchemaNode,
  },
  {
    name: "jobPayload -> jobPayloadSchema",
    build: () => jobPayload(jobFixture()),
    schema: jobPayloadSchema as unknown as SchemaNode,
  },
];

describe("payload builders conform to their payload SSOT schemas", () => {
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
    expect(() => assertConforms(drifted, schema)).toThrow(/must NOT have additional properties/);
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
