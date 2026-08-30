/**
 * Payload drift guard, batch-2 surfaces (#440): the beat association view,
 * lore alias list, review assessment, export artifact, and SSE proposal
 * frames are validated against the TypeBox payload SSOT their routes (or the
 * frame serializer) declare in `application/payload_schemas/`. Builders and
 * generators type their output with `Static` of these very schemas; this
 * guard pins the runtime half, where fast-json-stringify would stay silent.
 * The strictness contract and AJV bridge live in `payload_guard_harness.ts`.
 */

import { describe, expect, it } from "vitest";
import { chapterBeatView } from "../../src/contexts/studio/application/beat_association_service.js";
import { chapterBeatPayloadSchema } from "../../src/contexts/studio/application/payload_schemas/beat.js";
import { exportArtifactPayloadSchema } from "../../src/contexts/studio/application/payload_schemas/export.js";
import { loreAliasPayloadSchema } from "../../src/contexts/studio/application/payload_schemas/lore.js";
import {
  proposalDeltaFrameSchema,
  proposalDoneFrameSchema,
  proposalErrorFrameSchema,
} from "../../src/contexts/studio/application/payload_schemas/proposal_frame.js";
import { reviewPayloadSchema } from "../../src/contexts/studio/application/payload_schemas/review.js";
import {
  exportArtifactPayload,
  jobPayload,
  loreAliasPayload,
  reviewPayload,
} from "../../src/contexts/studio/application/payloads.js";
import type { ExportArtifactRecord } from "../../src/contexts/studio/application/ports/export_store.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import type { EditorialAssessment } from "../../src/contexts/studio/application/review_service.js";
import {
  assertConforms,
  documentFixture,
  firstRequired,
  jobFixture,
  NOW,
  type SchemaNode,
} from "./payload_guard_harness.js";

function assessmentFixture(): EditorialAssessment {
  return {
    id: "rev-1",
    projectId: "proj-1",
    snapshotId: "snap-1",
    provider: "mock",
    model: "deterministic-story-v1",
    summary: "Two warnings about pacing.",
    createdAt: NOW,
    issues: [
      {
        id: "issue-1",
        documentId: "doc-1",
        severity: "warning",
        code: "pacing.thin_chapter",
        message: "The chapter carries too few story beats.",
        suggestion: "Add a turning point.",
        evidence: { word_count: 120, threshold: 300 },
      },
    ],
  };
}

function artifactFixture(): ExportArtifactRecord {
  return {
    id: "art-1",
    projectId: "proj-1",
    snapshotId: "snap-1",
    format: "markdown",
    relativePath: "exports/proj-1/art-1.md",
    sizeBytes: 2048,
    checksumSha256: "c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2",
    createdAt: NOW,
  };
}

function deltaFrameFixture(): ProposalStreamFrame {
  return { type: "delta", text: "The harbour wakes " };
}

function doneFrameFixture(): ProposalStreamFrame {
  return { type: "done", job: jobPayload(jobFixture()) };
}

function errorFrameFixture(): ProposalStreamFrame {
  return { type: "error", error: { code: "PROVIDER_FAILED", message: "upstream failed" } };
}

const CASES: Array<{
  name: string;
  build: () => Record<string, unknown>;
  schema: SchemaNode;
  /** Overrides the default mistyped sentinel when the first required field is not primitive-typed. */
  mistypedValue?: unknown;
}> = [
  {
    name: "chapterBeatView (linked) -> chapterBeatPayloadSchema",
    build: () =>
      chapterBeatView(documentFixture(), [{ title: "beat-7", content: "Opening image." }]),
    schema: chapterBeatPayloadSchema as unknown as SchemaNode,
    // `beat` is an object-typed field: a number trips the type check itself.
    mistypedValue: 42,
  },
  {
    name: "chapterBeatView (unlinked null) -> chapterBeatPayloadSchema",
    build: () => chapterBeatView({ ...documentFixture(), beatRef: null }, []),
    schema: chapterBeatPayloadSchema as unknown as SchemaNode,
    mistypedValue: 42,
  },
  {
    name: "loreAliasPayload -> loreAliasPayloadSchema",
    build: () => loreAliasPayload(["TheMarianne", "Marianne"]),
    schema: loreAliasPayloadSchema as unknown as SchemaNode,
  },
  {
    name: "reviewPayload -> reviewPayloadSchema",
    build: () => reviewPayload(assessmentFixture()),
    schema: reviewPayloadSchema as unknown as SchemaNode,
  },
  {
    name: "exportArtifactPayload -> exportArtifactPayloadSchema",
    build: () => exportArtifactPayload(artifactFixture(), "proj-1"),
    schema: exportArtifactPayloadSchema as unknown as SchemaNode,
  },
  {
    name: "proposal delta frame -> proposalDeltaFrameSchema",
    build: deltaFrameFixture,
    schema: proposalDeltaFrameSchema as unknown as SchemaNode,
  },
  {
    name: "proposal done frame -> proposalDoneFrameSchema",
    build: doneFrameFixture,
    schema: proposalDoneFrameSchema as unknown as SchemaNode,
  },
  {
    name: "proposal error frame -> proposalErrorFrameSchema",
    build: errorFrameFixture,
    schema: proposalErrorFrameSchema as unknown as SchemaNode,
  },
];

describe("batch-2 payload builders conform to their payload SSOT schemas", () => {
  it.each(CASES)("validates $name", ({ build, schema }) => {
    expect(() => assertConforms(build(), schema)).not.toThrow();
  });
});

describe("batch-2 payload drift guard trips on every drift class", () => {
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
