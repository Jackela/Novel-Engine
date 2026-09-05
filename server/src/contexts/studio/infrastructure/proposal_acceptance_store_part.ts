import { and, desc, eq } from "drizzle-orm";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import { jobs } from "../../../shared/infrastructure/db/schema.js";
import type { ProposalAcceptanceStore } from "../application/ports/proposal_acceptance_store.js";
import type { JobRecord, ProjectScope } from "../application/ports/studio_store.js";
import { NotFoundError } from "../domain/exceptions.js";
import { advanceDocumentInTransaction } from "./db/document_revision_writes.js";
import { documentRevisions } from "./db/schema.js";
import { scopedDocument, scopedProject, type Tx } from "./db/studio_query_helpers.js";
import { jobWithEvents } from "./job_store_part.js";

/**
 * Deep persistence command for proposal acceptance. Every authoring projection
 * and the job binding share one immediate transaction.
 */
export class ProposalAcceptanceStorePart implements ProposalAcceptanceStore {
  constructor(protected readonly db: StudioSqliteDatabase) {}

  acceptCompletedProposal(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    now: Date,
  ): JobRecord {
    return this.db.transaction(
      (tx) => {
        scopedProject(tx, scope, projectId);
        const job = tx.select().from(jobs).where(eq(jobs.id, jobId)).get();
        if (
          job === undefined ||
          job.project_id !== projectId ||
          job.kind !== "proposal" ||
          job.document_id === null
        ) {
          throw proposalNotFound(jobId, projectId);
        }
        if (job.status !== "completed") {
          throw new InvalidOperationError("Only a completed proposal can be accepted.");
        }
        this.afterLockedJobRead(job.id);
        const result = storedObject(job.result_json);
        if (result.accepted_revision_id) {
          return jobWithEvents(tx, job.id);
        }
        const proposal =
          typeof result.proposal_markdown === "string" ? result.proposal_markdown : "";
        if (proposal.trim() === "") {
          throw new InvalidOperationError(
            "Only a completed proposal with content can be accepted.",
          );
        }
        scopedDocument(tx, scope, projectId, job.document_id);
        const request = storedObject(job.request_json);
        const baseRevisionId =
          typeof request.base_revision_id === "string" ? request.base_revision_id : null;
        const splitRevisionId = findLegacySplitRevision(
          tx,
          job.document_id,
          job.id,
          proposal,
          baseRevisionId,
        );
        if (splitRevisionId !== null) {
          this.bindAcceptedRevision(tx, job.id, result, splitRevisionId, now);
          return jobWithEvents(tx, job.id);
        }
        const saved = advanceDocumentInTransaction(tx, scope, projectId, job.document_id, {
          contentMarkdown: proposal,
          baseRevisionId,
          title: null,
          metadataJson: JSON.stringify({ ai_job_id: job.id }),
          source: "ai-accepted",
          now,
        });
        const acceptedRevisionId = saved.currentRevisionId;
        if (acceptedRevisionId === null) {
          throw new InvalidOperationError("Accepted proposal did not create a revision.");
        }
        this.bindAcceptedRevision(tx, job.id, result, acceptedRevisionId, now);
        return jobWithEvents(tx, job.id);
      },
      { behavior: "immediate" },
    );
  }

  /** Test seam proving the immediate write lock precedes the idempotence decision. */
  protected afterLockedJobRead(_jobId: string): void {}

  /** Failure-injection seam: a throw here must roll every preceding write back. */
  protected bindAcceptedRevision(
    tx: Tx,
    jobId: string,
    previousResult: Record<string, unknown>,
    revisionId: string,
    now: Date,
  ): void {
    tx.update(jobs)
      .set({
        result_json: JSON.stringify({ ...previousResult, accepted_revision_id: revisionId }),
        updated_at: now,
      })
      .where(eq(jobs.id, jobId))
      .run();
  }
}

function findLegacySplitRevision(
  tx: Tx,
  documentId: string,
  jobId: string,
  proposal: string,
  baseRevisionId: string | null,
): string | null {
  const candidates = tx
    .select()
    .from(documentRevisions)
    .where(
      and(
        eq(documentRevisions.documentId, documentId),
        eq(documentRevisions.source, "ai-accepted"),
      ),
    )
    .orderBy(desc(documentRevisions.revisionNumber))
    .all();
  return (
    candidates.find(
      (revision) =>
        revision.contentMarkdown === proposal &&
        revision.parentRevisionId === baseRevisionId &&
        storedObject(revision.metadataJson).ai_job_id === jobId,
    )?.id ?? null
  );
}

function storedObject(value: string): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(value);
    if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // Persisted advisory JSON follows the existing fail-closed object decoder.
  }
  return {};
}

function proposalNotFound(jobId: string, projectId: string): NotFoundError {
  return new NotFoundError(
    `No AI proposal job '${jobId}' exists in project '${projectId}': the id does not ` +
      "exist there, or the job belongs to a different project.",
  );
}
