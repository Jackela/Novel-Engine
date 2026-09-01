import { readdir } from "node:fs/promises";
import { resolve } from "node:path";

import {
  type ManifestEvidence,
  readManifestEvidence,
} from "./export_publication_manifest_evidence.js";

const STAGE_FILE = /^([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)\.stage$/;
const MANIFEST_FILE = /^([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)\.manifest\.json$/;
const LEGACY_TEMP = /^\..+\.tmp$/;
const MANIFEST_TEMP = /^\.([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.manifest\.json)\.[A-Za-z0-9_-]+\.tmp$/;
const CLEANUP_SUFFIX = /^(.*)\.cleanup-[A-Za-z0-9_-]+$/;
const MAX_CLEANUP_DEPTH = 8;

export interface RecoveryFileEntry {
  readonly path: string;
  readonly logicalName: string;
  readonly cleanupDepth: number;
}

export interface RecoveryManifestEntry extends RecoveryFileEntry {
  readonly evidence: ManifestEvidence;
}

export interface RecoveryTemporaryEntry extends RecoveryFileEntry {
  readonly manifestName: string | undefined;
}

export interface RecoveryStagingEntries {
  readonly stages: Map<string, RecoveryFileEntry>;
  readonly manifests: Map<string, RecoveryManifestEntry>;
  readonly temporary: RecoveryTemporaryEntry[];
}

export async function readRecoveryStagingEntries(
  staging: string,
  projectId: string,
): Promise<RecoveryStagingEntries> {
  const stages = new Map<string, RecoveryFileEntry>();
  const manifests = new Map<string, RecoveryManifestEntry>();
  const temporary: RecoveryTemporaryEntry[] = [];
  const temporaryNames = new Set<string>();
  for (const entry of await readdir(staging, { withFileTypes: true })) {
    if (entry.isSymbolicLink() || !entry.isFile()) {
      throw new Error(`Unsafe staging entry: ${entry.name}`);
    }
    const normalized = normalizeCleanupName(entry.name);
    const file = {
      path: resolve(staging, entry.name),
      logicalName: normalized.name,
      cleanupDepth: normalized.depth,
    };
    if (MANIFEST_FILE.test(file.logicalName)) {
      assertUnique(manifests, file.logicalName);
      manifests.set(file.logicalName, {
        ...file,
        evidence: await readManifestEvidence(file.path, file.logicalName, projectId),
      });
    } else if (STAGE_FILE.test(file.logicalName)) {
      assertUnique(stages, file.logicalName);
      stages.set(file.logicalName, file);
    } else if (LEGACY_TEMP.test(file.logicalName)) {
      if (temporaryNames.has(file.logicalName)) ambiguous(file.logicalName);
      temporaryNames.add(file.logicalName);
      temporary.push({
        ...file,
        manifestName: MANIFEST_TEMP.exec(file.logicalName)?.[1],
      });
    } else {
      throw new Error(`Unknown staging entry: ${entry.name}`);
    }
  }
  return { stages, manifests, temporary };
}

export function normalizeCleanupName(name: string): {
  readonly name: string;
  readonly depth: number;
} {
  let logicalName = name;
  let depth = 0;
  for (;;) {
    const match = CLEANUP_SUFFIX.exec(logicalName);
    if (match === null || match[1] === undefined) break;
    logicalName = match[1];
    depth += 1;
    if (depth > MAX_CLEANUP_DEPTH) {
      throw new Error(`Export cleanup quarantine nesting is excessive: ${name}`);
    }
  }
  return { name: logicalName, depth };
}

export function stageArtifactId(name: string): string | undefined {
  return STAGE_FILE.exec(name)?.[1];
}

function assertUnique<T>(entries: Map<string, T>, name: string): void {
  if (entries.has(name)) ambiguous(name);
}

function ambiguous(name: string): never {
  throw new Error(`Ambiguous export cleanup quarantine and replacement: ${name}`);
}
