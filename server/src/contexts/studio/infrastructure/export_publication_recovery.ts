import { readdir, realpath, rm } from "node:fs/promises";
import { resolve } from "node:path";

import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import {
  exportArtifactNames,
  parseExportArtifactFilename,
} from "../application/export_artifact_identity.js";
import { exports as exportArtifacts, projects } from "./db/schema.js";
import { syncDirectory } from "./export_artifact_fs_support.js";
import {
  type CleanupIntentRow,
  DatabaseExportPublicationCleanupJournal,
  loadCleanupIntents,
} from "./export_publication_cleanup_journal.js";
import { normalizeCleanupName } from "./export_publication_recovery_entries.js";
import {
  type ArtifactRow,
  artifactFilename,
  assertCanonicalArtifact,
  assertTreeContainsNoSymlinks,
  type MutableRecoveryReport,
  realDirectory,
  requireEvidence,
} from "./export_publication_recovery_support.js";
import {
  type FinalQuarantine,
  reconcileStaging,
  removeOwnedFinalQuarantines,
} from "./export_publication_staging_recovery.js";

export type ExportPublicationRecoveryReport = Readonly<MutableRecoveryReport>;

const LEGACY_TEMP = /^\..+\.tmp$/;
const ROLLBACK_FILE = /^(.+)\.rollback-[A-Za-z0-9_-]+$/;

/** Reconciles the database commit marker with the confined export filesystem. */
export async function reconcileExportPublications(
  db: StudioSqliteDatabase,
  dataDirectory: string,
): Promise<ExportPublicationRecoveryReport> {
  const report = emptyReport();
  const dataRoot = await realpath(resolve(dataDirectory));
  const exportsRoot = resolve(dataRoot, "exports");
  const artifactRows = db.select().from(exportArtifacts).all();
  const cleanupJournal = new DatabaseExportPublicationCleanupJournal(db);
  const cleanupIntents = groupCleanupIntents(loadCleanupIntents(db));
  const projectIds = new Set(
    db
      .select({ id: projects.id })
      .from(projects)
      .all()
      .map(({ id }) => id),
  );
  if (!(await realDirectory(exportsRoot, dataRoot, true))) {
    if (artifactRows.length > 0) throw new Error("Committed export directory is missing.");
    for (const intents of cleanupIntents.values()) {
      for (const intent of intents.values()) await cleanupJournal.complete(intent.publicationId);
    }
    return report;
  }
  const artifactsByProject = groupArtifacts(artifactRows);
  const seenProjects = new Set<string>();
  for (const entry of await readdir(exportsRoot, { withFileTypes: true })) {
    const projectDirectory = resolve(exportsRoot, entry.name);
    if (entry.isSymbolicLink() || !entry.isDirectory()) {
      throw new Error(`Unsafe entry in export root: ${entry.name}`);
    }
    await realDirectory(projectDirectory, exportsRoot, false);
    if (!projectIds.has(entry.name)) {
      if ((artifactsByProject.get(entry.name)?.size ?? 0) > 0) {
        throw new Error(
          `Committed export evidence references missing project ${entry.name}; preserving its directory.`,
        );
      }
      await assertTreeContainsNoSymlinks(projectDirectory);
      await rm(projectDirectory, { recursive: true });
      await syncDirectory(exportsRoot);
      for (const intent of cleanupIntents.get(entry.name)?.values() ?? []) {
        await cleanupJournal.complete(intent.publicationId);
      }
      report.deletedProjectDirectoriesRemoved += 1;
      continue;
    }
    seenProjects.add(entry.name);
    await reconcileProject(
      projectDirectory,
      entry.name,
      artifactsByProject.get(entry.name) ?? new Map(),
      cleanupIntents.get(entry.name) ?? new Map(),
      cleanupJournal,
      report,
    );
  }
  for (const [projectId, artifacts] of artifactsByProject) {
    if (!seenProjects.has(projectId) && artifacts.size > 0) {
      throw new Error(`Committed export directory is missing for project ${projectId}.`);
    }
  }
  for (const [projectId, intents] of cleanupIntents) {
    if (seenProjects.has(projectId)) continue;
    for (const intent of intents.values()) await cleanupJournal.complete(intent.publicationId);
  }
  return report;
}

// Classified contents of one project export directory feeding the recovery
// steps below: quarantined finals awaiting staged recovery, canonical
// committed file names, and whether a staging directory is present.
interface ClassifiedProjectExports {
  readonly quarantines: FinalQuarantine[];
  readonly canonicalFiles: Set<string>;
  readonly hasStaging: boolean;
}

async function reconcileProject(
  directory: string,
  projectId: string,
  artifacts: Map<string, ArtifactRow>,
  intents: Map<string, CleanupIntentRow>,
  cleanupJournal: DatabaseExportPublicationCleanupJournal,
  report: MutableRecoveryReport,
): Promise<void> {
  for (const artifact of artifacts.values()) assertCanonicalArtifact(artifact);
  const classified = await classifyProjectExportEntries(directory);
  await recoverProjectStagedExports(
    directory,
    projectId,
    classified,
    artifacts,
    intents,
    cleanupJournal,
    report,
  );
  await verifyProjectCommittedArtifacts(directory, artifacts, report);
  await assertProjectExportsOwnership(directory, projectId, artifacts);
  for (const intent of intents.values()) await cleanupJournal.complete(intent.publicationId);
  await syncDirectory(directory);
}

// Step 1: classify every entry of the project export directory into
// quarantined finals, canonical committed files, and the validated staging
// directory; any unsafe entry aborts recovery.
async function classifyProjectExportEntries(directory: string): Promise<ClassifiedProjectExports> {
  const entries = await readdir(directory, { withFileTypes: true });
  const quarantines: FinalQuarantine[] = [];
  const canonicalFiles = new Set<string>();
  let hasStaging = false;
  for (const entry of entries) {
    const path = resolve(directory, entry.name);
    const normalized = normalizeCleanupName(entry.name);
    const rollbackMatch = ROLLBACK_FILE.exec(normalized.name);
    const rollbackIdentity = parseExportArtifactFilename(rollbackMatch?.[1]);
    if (entry.name === ".staging") {
      if (entry.isSymbolicLink() || !entry.isDirectory()) throw new Error("Unsafe staging path.");
      await realDirectory(path, directory, false);
      hasStaging = true;
    } else if (
      normalized.depth > 0 &&
      parseExportArtifactFilename(normalized.name) !== null &&
      !entry.isSymbolicLink() &&
      entry.isFile()
    ) {
      quarantines.push({ path, finalName: normalized.name });
    } else if (rollbackMatch !== null && rollbackIdentity !== null) {
      if (entry.isSymbolicLink() || !entry.isFile() || rollbackMatch[1] === undefined) {
        throw new Error(`Unsafe export rollback quarantine: ${entry.name}`);
      }
      quarantines.push({ path, finalName: rollbackMatch[1] });
    } else if (
      entry.isSymbolicLink() ||
      !entry.isFile() ||
      (parseExportArtifactFilename(entry.name) === null && !LEGACY_TEMP.test(entry.name)) ||
      normalized.depth > 0
    ) {
      throw new Error(`Unsafe entry in project export directory: ${entry.name}`);
    } else if (parseExportArtifactFilename(entry.name) !== null) {
      canonicalFiles.add(entry.name);
    }
  }
  return { quarantines, canonicalFiles, hasStaging };
}

// Step 2: recover quarantined finals through the staging directory; without
// staging, surviving quarantines are ambiguous and abort recovery.
async function recoverProjectStagedExports(
  directory: string,
  projectId: string,
  classified: ClassifiedProjectExports,
  artifacts: Map<string, ArtifactRow>,
  intents: Map<string, CleanupIntentRow>,
  cleanupJournal: DatabaseExportPublicationCleanupJournal,
  report: MutableRecoveryReport,
): Promise<void> {
  const staging = resolve(directory, ".staging");
  if (!classified.hasStaging) {
    if (classified.quarantines.length > 0) {
      throw new Error(
        `Ambiguous export rollback quarantine or final cleanup quarantine: ${classified.quarantines[0]?.finalName}`,
      );
    }
    return;
  }
  await removeOwnedFinalQuarantines(
    staging,
    directory,
    projectId,
    classified.quarantines,
    classified.canonicalFiles,
    intents,
    cleanupJournal,
    report,
  );
  await reconcileStaging(staging, directory, projectId, artifacts, intents, cleanupJournal, report);
}

// Step 3: prove every committed artifact still has its integrity evidence in
// the project directory.
async function verifyProjectCommittedArtifacts(
  directory: string,
  artifacts: Map<string, ArtifactRow>,
  report: MutableRecoveryReport,
): Promise<void> {
  for (const artifact of artifacts.values()) {
    await requireEvidence(resolve(directory, artifactFilename(artifact)), artifact);
    report.committedArtifactsVerified += 1;
  }
}

// Step 4: sweep the project directory for files no committed artifact owns;
// anything unproven requires operator recovery.
async function assertProjectExportsOwnership(
  directory: string,
  projectId: string,
  artifacts: Map<string, ArtifactRow>,
): Promise<void> {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.name === ".staging") continue;
    if (entry.isSymbolicLink() || !entry.isFile())
      throw new Error(`Unsafe export file: ${entry.name}`);
    const identity = parseExportArtifactFilename(entry.name);
    const artifact = identity === null ? undefined : artifacts.get(identity.id);
    const owned =
      identity !== null &&
      artifact?.format === identity.format &&
      artifact.relativePath ===
        exportArtifactNames(projectId, identity.id, identity.format).relativePath;
    if (!owned) throw new Error(`Unproven export file requires operator recovery: ${entry.name}`);
  }
}

function groupArtifacts(rows: ArtifactRow[]): Map<string, Map<string, ArtifactRow>> {
  const grouped = new Map<string, Map<string, ArtifactRow>>();
  for (const row of rows) {
    const project = grouped.get(row.projectId) ?? new Map<string, ArtifactRow>();
    if (project.has(row.id)) throw new Error(`Duplicate export artifact id: ${row.id}`);
    project.set(row.id, row);
    grouped.set(row.projectId, project);
  }
  return grouped;
}

function groupCleanupIntents(rows: CleanupIntentRow[]): Map<string, Map<string, CleanupIntentRow>> {
  const grouped = new Map<string, Map<string, CleanupIntentRow>>();
  for (const row of rows) {
    const project = grouped.get(row.projectId) ?? new Map<string, CleanupIntentRow>();
    if (project.has(row.publicationId)) {
      throw new Error(`Duplicate export cleanup intent: ${row.publicationId}`);
    }
    project.set(row.publicationId, row);
    grouped.set(row.projectId, project);
  }
  return grouped;
}

function emptyReport(): MutableRecoveryReport {
  return {
    manifestsReconciled: 0,
    committedArtifactsVerified: 0,
    finalsRestored: 0,
    orphanFilesRemoved: 0,
    sidecarsRemoved: 0,
    deletedProjectDirectoriesRemoved: 0,
  };
}
