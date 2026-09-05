import type { Dispatch, SetStateAction } from "react";

import type { Project, StudioDocument } from "@/app/types/studio";
import { useStudioJobAudit } from "./useStudioJobAudit";
import { useStudioProposal } from "./useStudioProposal";
import { useWholeBookLoop } from "./useWholeBookLoop";

interface StudioGenerationOptions {
  readonly projectId: string;
  readonly activeDocument: StudioDocument | null;
  readonly project: Project | null;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly setProposalError: Dispatch<SetStateAction<string | null>>;
  readonly setJobsError: Dispatch<SetStateAction<string | null>>;
  readonly captureAcceptance: (
    documentId: string,
  ) => ((document: StudioDocument) => void) | undefined;
}

/** Coordinate every proposal producer through one project-owned audit gate. */
export function useStudioGeneration({
  projectId,
  activeDocument,
  project,
  setProject,
  setProposalError,
  setJobsError,
  captureAcceptance,
}: StudioGenerationOptions) {
  const jobAudit = useStudioJobAudit(projectId, setJobsError);
  const copilot = useStudioProposal(
    projectId,
    activeDocument,
    project,
    setProject,
    setProposalError,
    jobAudit.loadJobs,
    captureAcceptance,
    jobAudit.proposalAudit,
  );
  const wholeBookLoop = useWholeBookLoop({
    projectId,
    provider: String(project?.settings.provider ?? "mock"),
    setProject,
    loadJobs: jobAudit.loadJobs,
    proposalAudit: jobAudit.proposalAudit,
    captureAcceptedDocument: captureAcceptance,
  });
  return { ...jobAudit, copilot, wholeBookLoop };
}
