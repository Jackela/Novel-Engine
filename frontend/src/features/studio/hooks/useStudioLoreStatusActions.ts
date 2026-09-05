import type { Dispatch, SetStateAction } from "react";
import { useCallback } from "react";

import { api } from "@/app/api";
import type { LoreStatus, Project } from "@/app/types/studio";

import type { NarrowSummaryPatch } from "./projectState";
import { useNarrowSummaryField } from "./useNarrowSummaryField";

interface LoreStatusOwner {
  readonly projectId: string;
}

export interface LoreStatusLifecycleState {
  readonly isSaving: boolean;
  readonly error: string | null;
  readonly attemptedStatus: LoreStatus | null;
}

interface UseStudioLoreStatusActionsOptions<Owner extends LoreStatusOwner> {
  readonly project: Project | null;
  readonly projectId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly currentOwner: () => Owner | null;
  readonly isCurrentOwner: (owner: Owner) => boolean;
  readonly clearSharedError: (owner: Owner) => void;
}

/** The lore-status surface's own value authority is its closed response. */
const invokeLoreStatus = async (
  projectId: string,
  documentId: string,
  requested: LoreStatus,
): Promise<LoreStatus> => (await api.saveLoreStatus(projectId, documentId, requested)).lore_status;

const lorePatch = (status: LoreStatus): NarrowSummaryPatch => ({
  field: "lore_status",
  value: status,
});

/**
 * Lore mutations keyed by their origin project and document (#444). The
 * field runs on the shared narrow-summary intent epoch (#466): only the
 * latest Lore intent for a document may publish, and only while its
 * captured revision still owns the shell row.
 */
export function useStudioLoreStatusActions<Owner extends LoreStatusOwner>({
  project,
  projectId,
  setProject,
  currentOwner,
  isCurrentOwner,
  clearSharedError,
}: UseStudioLoreStatusActionsOptions<Owner>) {
  const narrow = useNarrowSummaryField<Owner, LoreStatus>({
    project,
    projectId,
    setProject,
    currentOwner,
    isCurrentOwner,
    clearSharedError,
    failureMessage: "Unable to update the lore status.",
    invoke: invokeLoreStatus,
    patchFor: lorePatch,
  });

  const changeLoreStatus = useCallback(
    (documentId: string, loreStatus: LoreStatus): Promise<void> =>
      narrow.run(documentId, loreStatus),
    [narrow],
  );

  const loreStatusFor = useCallback(
    (documentId: string): LoreStatusLifecycleState => {
      const state = narrow.lifecycleFor(documentId);
      return {
        isSaving: state.isSaving,
        error: state.error,
        attemptedStatus: state.attempted,
      };
    },
    [narrow],
  );
  return { changeLoreStatus, loreStatusFor };
}
