import type { Dispatch, SetStateAction } from "react";
import { useCallback } from "react";

import { api } from "@/app/api";
import type { Project } from "@/app/types/studio";

import type { NarrowSummaryPatch } from "./projectState";
import { useNarrowSummaryField } from "./useNarrowSummaryField";

interface BeatOwner {
  readonly projectId: string;
}

export interface BeatLifecycleState {
  readonly isSaving: boolean;
  readonly error: string | null;
  readonly attemptedTitle: string | null;
}

interface UseStudioBeatActionsOptions<Owner extends BeatOwner> {
  readonly project: Project | null;
  readonly projectId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly currentOwner: () => Owner | null;
  readonly isCurrentOwner: (owner: Owner) => boolean;
  readonly clearSharedError: (owner: Owner) => void;
}

/**
 * Stored-reference authority for the beat link (#466): the successful
 * command's normalized requested value (`null` or the trimmed non-empty
 * title) is what `beat_ref` stores. The response is confirmation plus the
 * independently resolved display view; it never feeds storage — the display
 * may already be `beat: null` when an outline heading was renamed between
 * persistence and response resolution.
 */
const invokeBeatLink = async (
  projectId: string,
  documentId: string,
  requested: string | null,
): Promise<string | null> => {
  await api.linkChapterBeat(projectId, documentId, requested);
  return requested;
};

const beatPatch = (title: string | null): NarrowSummaryPatch => ({
  field: "beat_ref",
  value: title,
});

/**
 * Chapter beat associations on the shared narrow-summary intent epoch
 * (#466): set and clear commands order by field intent and captured
 * revision, never by response arrival.
 */
export function useStudioBeatActions<Owner extends BeatOwner>({
  project,
  projectId,
  setProject,
  currentOwner,
  isCurrentOwner,
  clearSharedError,
}: UseStudioBeatActionsOptions<Owner>) {
  const narrow = useNarrowSummaryField<Owner, string | null>({
    project,
    projectId,
    setProject,
    currentOwner,
    isCurrentOwner,
    clearSharedError,
    failureMessage: "Unable to update the chapter beat.",
    invoke: invokeBeatLink,
    patchFor: beatPatch,
  });

  /** Link the chapter to a beat title, or clear the association with null. */
  const linkBeat = useCallback(
    (documentId: string, beat: string | null): Promise<void> =>
      narrow.run(documentId, beat === null ? null : beat.trim()),
    [narrow],
  );

  const beatFor = useCallback(
    (documentId: string): BeatLifecycleState => {
      const state = narrow.lifecycleFor(documentId);
      return {
        isSaving: state.isSaving,
        error: state.error,
        attemptedTitle: state.attempted,
      };
    },
    [narrow],
  );
  return { linkBeat, beatFor };
}
