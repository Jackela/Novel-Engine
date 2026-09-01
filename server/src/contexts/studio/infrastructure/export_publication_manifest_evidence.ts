import {
  exportArtifactNames,
  isExportArtifactFormat,
} from "../application/export_artifact_identity.js";
import type { FileIdentity } from "./export_artifact_fs_support.js";
import {
  EXPORT_PUBLICATION_VERSION,
  type ExportPublicationManifest,
} from "./export_artifact_publication.js";
import { readFileProof } from "./export_publication_file_evidence.js";

const SAFE_ID = /^[A-Za-z0-9_-]+$/;

export interface ManifestEvidence {
  readonly record: ExportPublicationManifest;
  readonly identity: FileIdentity;
}

export async function readManifestEvidence(
  path: string,
  filename: string,
  projectId: string,
): Promise<ManifestEvidence> {
  const proof = await readFileProof(path);
  if (proof === null) throw new Error("Export publication manifest disappeared.");
  let value: unknown;
  try {
    value = JSON.parse(proof.contents.toString("utf8"));
  } catch {
    throw new Error(`Malformed export publication manifest: ${filename}`);
  }
  if (!isManifest(value)) throw new Error(`Invalid export publication manifest: ${filename}`);
  if (
    value.project_id !== projectId ||
    filename !== `${value.artifact_id}.${value.publication_id}.manifest.json` ||
    value.stage_file !== `${value.artifact_id}.${value.publication_id}.stage` ||
    value.relative_path !==
      exportArtifactNames(projectId, value.artifact_id, value.format).relativePath
  ) {
    throw new Error(`Export publication manifest identity mismatch: ${filename}`);
  }
  return { record: value, identity: { dev: proof.dev, ino: proof.ino } };
}

function isManifest(value: unknown): value is ExportPublicationManifest {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const item = value as Record<string, unknown>;
  return (
    Object.keys(item).sort().join(",") ===
      "artifact_id,checksum_sha256,format,project_id,publication_id,relative_path,size_bytes,stage_file,version" &&
    item.version === EXPORT_PUBLICATION_VERSION &&
    typeof item.artifact_id === "string" &&
    SAFE_ID.test(item.artifact_id) &&
    typeof item.publication_id === "string" &&
    SAFE_ID.test(item.publication_id) &&
    typeof item.project_id === "string" &&
    SAFE_ID.test(item.project_id) &&
    isExportArtifactFormat(item.format) &&
    typeof item.relative_path === "string" &&
    typeof item.stage_file === "string" &&
    Number.isSafeInteger(item.size_bytes) &&
    Number(item.size_bytes) >= 0 &&
    typeof item.checksum_sha256 === "string" &&
    /^[a-f0-9]{64}$/.test(item.checksum_sha256)
  );
}
