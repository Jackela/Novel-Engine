import type { Dispatch, SetStateAction } from "react";
import { useCallback, useRef, useState } from "react";

import { api } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";

import { projectDocumentOwnerKey } from "./projectDocumentOwnerKey";
import { mergeProjectDocumentPlacement, type NarrowFieldCapture } from "./projectState";
import { toErrorMessage } from "./toErrorMessage";

interface ChapterPlacementOwner {
  readonly projectId: string;
}

interface PlacementIntent {
  readonly epoch: number;
  readonly requestedVolumeId: string;
  promise: Promise<void>;
}

interface ScopedPlacingChapter {
  readonly projectId: string;
  readonly documentId: string;
  readonly volumeId: string;
}

export interface ChapterPlacementLifecycleState {
  readonly isPlacing: boolean;
  readonly error: string | null;
  readonly attemptedVolumeId: string | null;
}

interface UseStudioChapterPlacementOptions<Owner extends ChapterPlacementOwner> {
  readonly project: Project | null;
  readonly projectId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly currentOwner: () => Owner | null;
  readonly isCurrentOwner: (owner: Owner) => boolean;
}

const IDLE_PLACEMENT: ChapterPlacementLifecycleState = {
  isPlacing: false,
  error: null,
  attemptedVolumeId: null,
};

/** The placement fields the complete response owns (#481). */
function placementOf(document: StudioDocument) {
  return {
    volumeId: document.volume_id ?? "",
    position: document.position,
    updatedAt: document.updated_at,
  };
}

/**
 * Navigator chapter volume placement (#481) under the #469 mutation
 * contract: every command captures its project, document, summary revision,
 * and a per-document intent epoch. A response patches only the summary
 * fields placement owns — volume, position, updated timestamp — and only
 * while its captured revision still owns the shell row and its intent is
 * still the latest. Anything older — a response outrun by a newer save or a
 * newer placement intent — is stale and ignored; no follow-up shell read
 * happens.
 */
export function useStudioChapterPlacement<Owner extends ChapterPlacementOwner>({
  project,
  projectId,
  setProject,
  currentOwner,
  isCurrentOwner,
}: UseStudioChapterPlacementOptions<Owner>) {
  const [lifecycle, setLifecycle] = useState<Record<string, ChapterPlacementLifecycleState>>({});
  const [placingState, setPlacingState] = useState<ScopedPlacingChapter | null>(null);
  const pendingRef = useRef(new Map<string, PlacementIntent>());

  const placeChapter = useCallback(
    (documentId: string, volumeId: string): Promise<void> => {
      const owner = currentOwner();
      if (!owner || !project) return Promise.resolve();
      const key = projectDocumentOwnerKey(owner.projectId, documentId);
      // Duplicate activation of the identical in-flight placement is one
      // command; a different target volume supersedes it as a newer intent.
      const existing = pendingRef.current.get(key);
      if (existing && existing.requestedVolumeId === volumeId) return existing.promise;

      const capturedRevision =
        project.documents.find((document) => document.id === documentId)?.current_revision_id ??
        null;
      if (capturedRevision === null) return Promise.resolve();

      const intent: PlacementIntent = {
        epoch: (existing?.epoch ?? 0) + 1,
        requestedVolumeId: volumeId,
        promise: Promise.resolve(),
      };
      pendingRef.current.set(key, intent);
      const isLatestIntent = () => pendingRef.current.get(key) === intent;
      intent.promise = (async () => {
        setPlacingState({ projectId: owner.projectId, documentId, volumeId });
        setLifecycle((current) => ({
          ...current,
          [key]: { isPlacing: true, error: null, attemptedVolumeId: volumeId },
        }));
        let failure: string | null = null;
        try {
          const placed = await api.moveChapterToVolume(project.id, documentId, volumeId);
          if (!isCurrentOwner(owner) || !isLatestIntent()) return;
          const capture: NarrowFieldCapture = {
            projectId: owner.projectId,
            documentId,
            revisionId: capturedRevision,
          };
          setProject((current) =>
            isCurrentOwner(owner) && current?.id === owner.projectId
              ? mergeProjectDocumentPlacement(current, capture, placementOf(placed))
              : current,
          );
        } catch (reason) {
          if (isCurrentOwner(owner) && isLatestIntent()) {
            failure = toErrorMessage(reason, "Unable to place the chapter.");
          }
        } finally {
          if (isLatestIntent()) {
            pendingRef.current.delete(key);
            if (isCurrentOwner(owner)) {
              setPlacingState((current) =>
                current?.projectId === owner.projectId &&
                current.documentId === documentId &&
                current.volumeId === volumeId
                  ? null
                  : current,
              );
              setLifecycle((current) => {
                if (failure !== null) {
                  return {
                    ...current,
                    [key]: { isPlacing: false, error: failure, attemptedVolumeId: volumeId },
                  };
                }
                const next = { ...current };
                delete next[key];
                return next;
              });
            }
          }
        }
      })();
      return intent.promise;
    },
    [currentOwner, isCurrentOwner, project, setProject],
  );

  const placementFor = useCallback(
    (documentId: string): ChapterPlacementLifecycleState =>
      lifecycle[projectDocumentOwnerKey(projectId, documentId)] ?? IDLE_PLACEMENT,
    [lifecycle, projectId],
  );

  return {
    placeChapter,
    placementFor,
    placingDocument:
      placingState?.projectId === projectId
        ? { documentId: placingState.documentId, volumeId: placingState.volumeId }
        : null,
  };
}
