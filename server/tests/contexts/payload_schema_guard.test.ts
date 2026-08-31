/**
 * Payload drift guard, core resources (#426, #433): every builder feeding a
 * studio HTTP surface is validated against the TypeBox payload SSOT its route
 * declares (`application/payload_schemas/`). Builders type their output with
 * `Static` of these very schemas, so compile-time drift is already
 * impossible; this guard pins the runtime half — a fixture-built payload must
 * validate against the same schema object the routes serialize with.
 * Fast-json-stringify only serializes and never validates, so this test is
 * where drift would turn red. Batch-2 surfaces (beat, lore, review, export,
 * SSE frames) live in `payload_schema_guard_batch2.test.ts`.
 */

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
import {
  assertConforms,
  documentFixture,
  firstRequired,
  jobFixture,
  matchFixture,
  projectFixture,
  revisionFixture,
  type SchemaNode,
  volumeFixture,
} from "./payload_guard_harness.js";

const CASES: Array<{
  name: string;
  build: () => Record<string, unknown>;
  schema: SchemaNode;
  /** Overrides the default mistyped sentinel when the first required field is not primitive-typed. */
  mistypedValue?: unknown;
}> = [
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
    // #444: a lore-kind document narrows its row value into the closed enum
    // member; non-lore kinds (the chapter fixture above) stay null.
    name: "documentPayload (lore status member) -> documentPayloadSchema",
    build: () => documentPayload({ ...documentFixture(), kind: "character", loreStatus: "stable" }),
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

  it.each(CASES)("rejects a mistyped field in $name", ({ build, schema, mistypedValue }) => {
    const payload = build();
    payload[firstRequired(schema)] = mistypedValue ?? { drifted: "object" };
    expect(() => assertConforms(payload, schema)).toThrow(/must be/);
  });
});
