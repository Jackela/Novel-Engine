import type { Dispatch, SetStateAction } from "react";

import { api, HttpError } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";
import { mergeProjectDocument } from "./projectState";
import { reportUnexpectedError } from "./reportUnexpectedError";
import type { AcceptedDocumentCapture } from "./useAcceptanceCapture";

interface AcceptProposalAndRefreshOptions {
  readonly projectId: string;
  readonly proposalId: string;
  /** Document the proposal was drafted for (looked up in the refreshed aggregate). */
  readonly documentId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  /** Receives the freshly accepted document (active-editor cache reset). */
  readonly acceptance?: AcceptedDocumentCapture;
  /** Fire-and-forget jobs refresh, matching the manual accept flow. */
  readonly loadJobs: () => void;
  /** Cancels the post-accept aggregate refresh when the workbench owner changes. */
  readonly signal?: AbortSignal;
  /** Guards aggregate and jobs publication against the originating project owner. */
  readonly isProjectCurrent?: () => boolean;
  /** Runs once after the server has atomically committed the acceptance. */
  readonly onAcceptanceCommitted?: () => void;
}

export class AcceptedProposalRefreshError extends Error {
  constructor(cause: unknown) {
    super("Proposal was accepted, but refreshing the project failed. Reload the project to sync.", {
      cause,
    });
    this.name = "AcceptedProposalRefreshError";
  }
}

/**
 * Shared accept-refresh orchestration (#318/#397): accept the proposal, pull
 * the refreshed project aggregate, publish it, and hand the accepted document
 * to the caller. Returns the accepted document, or null when it disappeared
 * from the refreshed aggregate.
 */
export async function acceptProposalAndRefresh({
  projectId,
  proposalId,
  documentId,
  setProject,
  acceptance,
  loadJobs,
  signal,
  isProjectCurrent = () => true,
  onAcceptanceCommitted,
}: AcceptProposalAndRefreshOptions): Promise<StudioDocument | null> {
  const committed = await api.acceptProposal(projectId, proposalId);
  onAcceptanceCommitted?.();
  const isRefreshCurrent = () =>
    isProjectCurrent() && (acceptance?.isCurrent(committed.result.base_revision_id) ?? true);
  let acceptedDocument: StudioDocument | null;
  try {
    if (!isRefreshCurrent()) return null;
    const refreshed = await api.project(projectId, { signal });
    if (!isRefreshCurrent()) return null;
    const acceptedSummary = refreshed.documents.find((document) => document.id === documentId);
    acceptedDocument = acceptedSummary
      ? await api.document(projectId, documentId, { signal })
      : null;
    if (!isRefreshCurrent()) return null;
  } catch (cause) {
    if (!isRefreshCurrent()) {
      if (
        !(cause instanceof HttpError) &&
        !(cause instanceof DOMException && cause.name === "AbortError")
      ) {
        reportUnexpectedError("Superseded proposal acceptance refresh failed.", cause);
      }
      return null;
    }
    if (!(cause instanceof HttpError)) {
      reportUnexpectedError("Proposal acceptance refresh failed.", cause);
    }
    throw new AcceptedProposalRefreshError(cause);
  } finally {
    if (isProjectCurrent() && !isRefreshCurrent()) loadJobs();
  }
  if (acceptedDocument) {
    setProject((current) =>
      isRefreshCurrent() &&
      current?.id === projectId &&
      (committed.result.base_revision_id === undefined ||
        current.documents.some(
          (document) =>
            document.id === documentId &&
            (document.current_revision_id === committed.result.base_revision_id ||
              document.current_revision_id === acceptedDocument.current_revision_id),
        ))
        ? mergeProjectDocument(current, acceptedDocument)
        : current,
    );
    acceptance?.reconcile?.(acceptedDocument);
  }
  if (isProjectCurrent()) loadJobs();
  return acceptedDocument;
}
