import { describe, expect, it } from "vitest";

import {
  assertCanonicalExportArtifactEvidence,
  EXPORT_ARTIFACT_FORMATS,
  exportArtifactExtension,
  exportArtifactFilename,
  exportArtifactNames,
  isExportArtifactFormat,
  parseExportArtifactFilename,
} from "../../src/contexts/studio/application/export_artifact_identity.js";
import { exportArtifactPayloadSchema } from "../../src/contexts/studio/application/payload_schemas/export.js";

describe("canonical export artifact identity", () => {
  it.each([
    ["markdown", "md"],
    ["docx", "docx"],
    ["epub", "epub"],
  ] as const)("owns the %s extension and canonical path", (format, extension) => {
    expect(exportArtifactExtension(format)).toBe(extension);
    expect(exportArtifactFilename("artifact-1", format)).toBe(`artifact-1.${extension}`);
    expect(parseExportArtifactFilename(`artifact-1.${extension}`)).toEqual({
      id: "artifact-1",
      format,
    });
    expect(exportArtifactNames("project-1", "artifact-1", format)).toEqual({
      filename: `artifact-1.${extension}`,
      relativePath: `exports/project-1/artifact-1.${extension}`,
    });
  });

  it("keeps the runtime format catalog exhaustive", () => {
    const responseFormatSchema = exportArtifactPayloadSchema.properties.format as unknown as {
      enum: readonly string[];
    };
    expect(EXPORT_ARTIFACT_FORMATS).toEqual(["markdown", "docx", "epub"]);
    expect(EXPORT_ARTIFACT_FORMATS.every((format) => isExportArtifactFormat(format))).toBe(true);
    expect(isExportArtifactFormat("pdf")).toBe(false);
    expect(responseFormatSchema.enum).toEqual([...EXPORT_ARTIFACT_FORMATS]);
  });

  it("rejects unknown, unsafe, and non-file artifact names", () => {
    expect(parseExportArtifactFilename("artifact-1.pdf")).toBeNull();
    expect(parseExportArtifactFilename("../artifact.md")).toBeNull();
    expect(parseExportArtifactFilename("artifact-without-extension")).toBeNull();
    expect(parseExportArtifactFilename(42)).toBeNull();
  });

  it("rejects unsafe identities and malformed integrity evidence", () => {
    expect(() => exportArtifactNames("../project", "artifact-1", "markdown")).toThrow();
    expect(() => exportArtifactNames("project-1", "../artifact", "markdown")).toThrow();
    expect(() => exportArtifactNames("project-1", "artifact-1", "pdf")).toThrow();

    const valid = {
      projectId: "project-1",
      id: "artifact-1",
      format: "markdown",
      relativePath: "exports/project-1/artifact-1.md",
      sizeBytes: 7,
      checksumSha256: "a".repeat(64),
    } as const;
    expect(() => assertCanonicalExportArtifactEvidence(valid)).not.toThrow();
    expect(() =>
      assertCanonicalExportArtifactEvidence({ ...valid, relativePath: "outside.md" }),
    ).toThrow();
    expect(() => assertCanonicalExportArtifactEvidence({ ...valid, sizeBytes: -1 })).toThrow();
    expect(() =>
      assertCanonicalExportArtifactEvidence({ ...valid, checksumSha256: "not-a-checksum" }),
    ).toThrow();
  });
});
