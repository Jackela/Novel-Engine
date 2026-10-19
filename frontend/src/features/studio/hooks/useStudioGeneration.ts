import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef } from "react";
import type { Project, StudioDocument } from "@/app/types/studio";
import type { CaptureAcceptedDocument } from "./useAcceptanceCapture";
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
  readonly captureAcceptance: CaptureAcceptedDocument;
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
  const projectRef = useRef(project);
  useEffect(() => {
    projectRef.current = project;
  }, [project]);

  const captureCurrentAcceptance = useCallback<CaptureAcceptedDocument>(
    (documentId) => {
      const capture = captureAcceptance(documentId);
      const expectedRevisionId = projectRef.current?.documents.find(
        (document) => document.id === documentId,
      )?.current_revision_id;
      return {
        ...capture,
        // The target shell remains authoritative after its Draft owner leaves.
        isCurrent: () =>
          projectRef.current?.id === projectId &&
          projectRef.current.documents.find((document) => document.id === documentId)
            ?.current_revision_id === expectedRevisionId &&
          (capture?.isCurrent() ?? true),
      };
    },
    [captureAcceptance, projectId],
  );

  const jobAudit = useStudioJobAudit(projectId, setJobsError);
  const copilot = useStudioProposal(
    projectId,
    activeDocument,
    project,
    setProject,
    setProposalError,
    jobAudit.loadJobs,
    captureCurrentAcceptance,
    jobAudit.proposalAudit,
  );
  const wholeBookLoop = useWholeBookLoop({
    projectId,
    provider: String(project?.settings.provider ?? "mock"),
    setProject,
    loadJobs: jobAudit.loadJobs,
    proposalAudit: jobAudit.proposalAudit,
    captureAcceptedDocument: captureCurrentAcceptance,
  });
  return { ...jobAudit, copilot, wholeBookLoop };
}
