import type { Dispatch, SetStateAction } from 'react';

import { api } from '@/app/api';
import type { Project, StudioDocument } from '@/app/types/studio';

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
}: AcceptProposalAndRefreshOptions): Promise<StudioDocument | null> {
  await api.acceptProposal(projectId, proposalId);
  const refreshed = await api.project(projectId);
  setProject(refreshed);
  const acceptedDocument =
    refreshed.documents?.find((document) => document.id === documentId) ?? null;
  if (acceptedDocument) onAccepted?.(acceptedDocument);
  loadJobs();
  return acceptedDocument;
}
