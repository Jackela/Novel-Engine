import { eq } from "drizzle-orm";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import { jobs } from "../../../shared/infrastructure/db/schema.js";
import { exportJobResultJson } from "../application/payloads.js";
import type {
  ExportArtifactRecord,
  ExportCompletionRecord,
  ExportOutcomeStore,
  ExportSource,
  PreparedExportArtifact,
} from "../application/ports/export_store.js";
import type { AddJobInput } from "../application/ports/job_records.js";
import type { ProjectScope } from "../application/ports/studio_store.js";
import { InvalidJobTransitionError, NotFoundError } from "../domain/exceptions.js";
import {
  findLatestExportSnapshot,
  hasMatchingRevisionMap,
  insertExportArtifact,
  loadProjectArtifact,
  loadProjectArtifacts,
  readCurrentExportDocuments,
  readExportSnapshotDocuments,
  resolveExportSnapshot,
} from "./db/export_records.js";
import { applyJobOutcome, insertJobAndEvent } from "./db/job_writes.js";
import { scopedProject, type Tx } from "./db/studio_query_helpers.js";
import { jobWithEvents } from "./job_store_part.js";

const EXPORT_PROVIDER = "studio";

/** Atomic persistence adapter for export capture, evidence, and job outcomes. */
export class ExportStorePart implements ExportOutcomeStore {
  constructor(protected readonly db: StudioSqliteDatabase) {}

  readExportSource(scope: ProjectScope, projectId: string, capturedAt: Date): ExportSource {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const current = readCurrentExportDocuments(tx, project.id);
      const latest = findLatestExportSnapshot(tx, project.id);
      if (latest !== undefined) {
        const captured = readExportSnapshotDocuments(tx, latest.id);
        if (hasMatchingRevisionMap(current, captured)) {
          return {
            projectId: project.id,
            projectTitle: project.title,
            capturedAt,
            reuseSnapshotId: latest.id,
            documents: captured,
          };
        }
      }
      return {
        projectId: project.id,
        projectTitle: project.title,
        capturedAt,
        reuseSnapshotId: null,
        documents: current,
      };
    });
  }

  recordCompletedExportJob(
    scope: ProjectScope,
    input: PreparedExportArtifact,
  ): ExportCompletionRecord {
    return this.db.transaction(
      (tx) => {
        const projectId = this.scopedInputProject(tx, scope, input);
        const artifact = this.persistArtifact(tx, projectId, input);
        const jobId = insertJobAndEvent(
          tx,
          completedExportJobInput(projectId, artifact, input),
          (id) => this.beforeFreshJobEventInsert(tx, id),
        );
        return { artifact, job: jobWithEvents(tx, jobId) };
      },
      { behavior: "immediate" },
    );
  }

  completeExportRetryJob(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: PreparedExportArtifact,
  ): ExportCompletionRecord {
    return this.db.transaction(
      (tx) => {
        scopedProject(tx, scope, projectId);
        if (input.source.projectId !== projectId) {
          throw new Error("Export source project does not match the retry target.");
        }
        const job = this.requireRunningExportRetry(tx, projectId, jobId, input.format);
        const artifact = this.persistArtifact(tx, projectId, input);
        applyJobOutcome(
          tx,
          job.id,
          {
            status: "completed",
            resultJson: exportJobResultJson(projectId, artifact),
            error: null,
            eventDetailsJson: JSON.stringify({ export_id: artifact.id }),
            now: input.createdAt,
          },
          (id) => this.beforeRetryEventInsert(tx, id),
        );
        return { artifact, job: jobWithEvents(tx, job.id) };
      },
      { behavior: "immediate" },
    );
  }

  listProjectArtifacts(scope: ProjectScope, projectId: string): ExportArtifactRecord[] {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      return loadProjectArtifacts(tx, project.id);
    });
  }

  findProjectArtifact(
    scope: ProjectScope,
    projectId: string,
    artifactId: string,
  ): ExportArtifactRecord {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const artifact = loadProjectArtifact(tx, project.id, artifactId);
      if (artifact === undefined) throw new NotFoundError("Export artifact not found.");
      return artifact;
    });
  }

  /** Failure seam after snapshot writes but before the artifact row. */
  protected beforeArtifactInsert(_tx: Tx, _artifactId: string): void {}

  /** Failure seam after the fresh job row but before its completed event. */
  protected beforeFreshJobEventInsert(_tx: Tx, _jobId: string): void {}

  /** Failure seam after retry update but before its completed event. */
  protected beforeRetryEventInsert(_tx: Tx, _jobId: string): void {}

  private scopedInputProject(tx: Tx, scope: ProjectScope, input: PreparedExportArtifact): string {
    const project = scopedProject(tx, scope, input.source.projectId);
    return project.id;
  }

  private persistArtifact(
    tx: Tx,
    projectId: string,
    input: PreparedExportArtifact,
  ): ExportArtifactRecord {
    if (input.source.projectId !== projectId) {
      throw new Error("Export source project does not match the persistence target.");
    }
    const snapshotId = resolveExportSnapshot(tx, projectId, input.source);
    return insertExportArtifact(tx, projectId, snapshotId, input, (artifactId) =>
      this.beforeArtifactInsert(tx, artifactId),
    );
  }

  private requireRunningExportRetry(
    tx: Tx,
    projectId: string,
    jobId: string,
    format: PreparedExportArtifact["format"],
  ): typeof jobs.$inferSelect {
    const job = tx.select().from(jobs).where(eq(jobs.id, jobId)).get();
    if (
      job === undefined ||
      job.project_id !== projectId ||
      job.kind !== "export" ||
      job.operation !== "export" ||
      job.document_id !== null ||
      job.retry_of_job_id === null
    ) {
      throw new NotFoundError("Export retry job not found.");
    }
    if (job.status !== "running" && job.status !== "pending") {
      throw new InvalidJobTransitionError(job.id, job.status, "completed");
    }
    if (job.provider !== EXPORT_PROVIDER) {
      throw new Error("Export retry provider is invalid.");
    }
    if (readStoredExportFormat(job.request_json) !== format) {
      throw new Error("Export retry format does not match the prepared artifact.");
    }
    return job;
  }
}

function completedExportJobInput(
  projectId: string,
  artifact: ExportArtifactRecord,
  input: PreparedExportArtifact,
): AddJobInput {
  return {
    projectId,
    documentId: null,
    kind: "export",
    operation: "export",
    status: "completed",
    provider: EXPORT_PROVIDER,
    model: "",
    requestJson: JSON.stringify({ format: input.format }),
    resultJson: exportJobResultJson(projectId, artifact),
    error: null,
    eventDetailsJson: JSON.stringify({ export_id: artifact.id }),
    now: input.createdAt,
  };
}

function readStoredExportFormat(requestJson: string): string | undefined {
  const parsed: unknown = JSON.parse(requestJson);
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return undefined;
  const format = (parsed as Record<string, unknown>).format;
  return typeof format === "string" ? format : undefined;
}
