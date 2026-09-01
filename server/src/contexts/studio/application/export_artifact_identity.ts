/** Runtime catalog and canonical filesystem identity for managed export artifacts. */
export const EXPORT_ARTIFACT_FORMATS = ["markdown", "docx", "epub"] as const;
export type ExportArtifactFormat = (typeof EXPORT_ARTIFACT_FORMATS)[number];
const EXPORT_ARTIFACT_FORMAT_SET: ReadonlySet<string> = new Set(EXPORT_ARTIFACT_FORMATS);

const EXTENSION_BY_FORMAT: Record<ExportArtifactFormat, string> = {
  markdown: "md",
  docx: "docx",
  epub: "epub",
};
const FORMAT_BY_EXTENSION = new Map(
  EXPORT_ARTIFACT_FORMATS.map((format) => [EXTENSION_BY_FORMAT[format], format] as const),
);
const SAFE_IDENTIFIER = /^[A-Za-z0-9_-]+$/;
const SHA256 = /^[a-f0-9]{64}$/;

export interface ExportArtifactEvidenceIdentity {
  readonly projectId: unknown;
  readonly id: unknown;
  readonly format: unknown;
  readonly relativePath: unknown;
  readonly sizeBytes: unknown;
  readonly checksumSha256: unknown;
}

export function isExportArtifactFormat(value: unknown): value is ExportArtifactFormat {
  return typeof value === "string" && EXPORT_ARTIFACT_FORMAT_SET.has(value);
}

export function exportArtifactExtension(format: unknown): string {
  if (!isExportArtifactFormat(format)) throw new Error("Export artifact format is invalid.");
  return EXTENSION_BY_FORMAT[format];
}

export function exportArtifactNames(
  projectId: unknown,
  artifactId: unknown,
  format: unknown,
): { filename: string; relativePath: string } {
  assertSafeIdentifier(projectId, "project");
  const filename = exportArtifactFilename(artifactId, format);
  return { filename, relativePath: `exports/${projectId}/${filename}` };
}

export function exportArtifactFilename(artifactId: unknown, format: unknown): string {
  assertSafeIdentifier(artifactId, "artifact");
  return `${artifactId}.${exportArtifactExtension(format)}`;
}

export function parseExportArtifactFilename(
  filename: unknown,
): { id: string; format: ExportArtifactFormat } | null {
  if (typeof filename !== "string") return null;
  const separator = filename.lastIndexOf(".");
  if (separator <= 0 || separator === filename.length - 1) return null;
  const id = filename.slice(0, separator);
  const format = FORMAT_BY_EXTENSION.get(filename.slice(separator + 1));
  if (!SAFE_IDENTIFIER.test(id) || format === undefined) return null;
  return { id, format };
}

export function assertCanonicalExportArtifactEvidence(
  evidence: ExportArtifactEvidenceIdentity,
): void {
  const expected = exportArtifactNames(evidence.projectId, evidence.id, evidence.format);
  if (evidence.relativePath !== expected.relativePath) {
    throw new Error("Export artifact path is not canonical.");
  }
  if (!Number.isSafeInteger(evidence.sizeBytes) || Number(evidence.sizeBytes) < 0) {
    throw new Error("Export artifact size is invalid.");
  }
  if (typeof evidence.checksumSha256 !== "string" || !SHA256.test(evidence.checksumSha256)) {
    throw new Error("Export artifact checksum is invalid.");
  }
}

function assertSafeIdentifier(value: unknown, label: string): asserts value is string {
  if (typeof value !== "string" || !SAFE_IDENTIFIER.test(value)) {
    throw new Error(`Export ${label} identifier is invalid.`);
  }
}
