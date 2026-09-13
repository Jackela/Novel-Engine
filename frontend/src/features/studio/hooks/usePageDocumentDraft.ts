import type { Dispatch, SetStateAction } from "react";

import type { Project, StudioDocument } from "@/app/types/studio";

import { projectDocumentOwnerKey } from "./projectDocumentOwnerKey";
import { useDocumentDraft } from "./useDocumentDraft";
import { useScopedRevisionRestore } from "./useScopedRevisionRestore";

interface PageDocumentDraftInput {
  projectId: string;
  activeDocument: StudioDocument | null;
  selectedDocumentId: string | null;
  setProject: Dispatch<SetStateAction<Project | null>>;
  draftError: Dispatch<SetStateAction<string | null>>;
  revisionError: Dispatch<SetStateAction<string | null>>;
  restoreError: Dispatch<SetStateAction<string | null>>;
}

/**
 * The active document's draft workbench: per-owner draft state and revision
 * history actions, with the History pending-restore kept scoped to the
 * document that started it. The unscoped restore entry point never escapes
 * this hook; consumers only see the owner-scoped one.
 */
export function usePageDocumentDraft({
  projectId,
  activeDocument,
  selectedDocumentId,
  setProject,
  draftError,
  revisionError,
  restoreError,
}: PageDocumentDraftInput) {
  const { restoreRevision, ...draftModel } = useDocumentDraft(
    activeDocument,
    projectId,
    setProject,
    draftError,
    revisionError,
    restoreError,
    selectedDocumentId,
  );
  const { restoringRevisionId, restoreRevision: onRestoreRevision } = useScopedRevisionRestore(
    projectDocumentOwnerKey(projectId, activeDocument?.id ?? null),
    restoreRevision,
  );
  return { ...draftModel, restoringRevisionId, onRestoreRevision };
}
