import type { Dispatch, SetStateAction } from "react";

import { api } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";
import { mergeProjectDocument } from "./projectState";

interface AcceptProposalAndRefreshOptions {
  readonly projectId: string;
  readonly proposalId: string;
  /** Document the proposal was drafted for (looked up in the refreshed aggregate). */
  readonly documentId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  /** Receives the freshly accepted document (active-editor cache reset). */
  readonly onAccepted?: (document: StudioDocument) => void;
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
  onAccepted,
  loadJobs,
  signal,
  isProjectCurrent = () => true,
  onAcceptanceCommitted,
}: AcceptProposalAndRefreshOptions): Promise<StudioDocument | null> {
  await api.acceptProposal(projectId, proposalId);
  onAcceptanceCommitted?.();
  if (!isProjectCurrent()) return null;
  let refreshed: Project;
  try {
    refreshed = await api.project(projectId, { signal });
  } catch (cause) {
    if (!isProjectCurrent()) return null;
    throw new AcceptedProposalRefreshError(cause);
  }
  if (!isProjectCurrent()) return null;
  const acceptedSummary = refreshed.documents.find((document) => document.id === documentId);
  const acceptedDocument = acceptedSummary
    ? await api.document(projectId, documentId, { signal })
    : null;
  if (acceptedDocument) {
    setProject((current) =>
      isProjectCurrent() && current?.id === projectId
        ? mergeProjectDocument(current, acceptedDocument)
        : current,
    );
    onAccepted?.(acceptedDocument);
  }
  if (isProjectCurrent()) loadJobs();
  return acceptedDocument;
}
