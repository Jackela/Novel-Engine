import type { Dispatch, SetStateAction } from "react";
import { useCallback, useRef, useState } from "react";

import { api } from "@/app/api";
import type { LoreStatus, Project } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";

interface LoreStatusOwner {
  readonly projectId: string;
}

export interface LoreStatusLifecycleState {
  readonly isSaving: boolean;
  readonly error: string | null;
  readonly attemptedStatus: LoreStatus | null;
}

const IDLE_LORE_STATUS: LoreStatusLifecycleState = {
  isSaving: false,
  error: null,
  attemptedStatus: null,
};

interface UseStudioLoreStatusActionsOptions<Owner extends LoreStatusOwner> {
  readonly project: Project | null;
  readonly projectId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly currentOwner: () => Owner | null;
  readonly isCurrentOwner: (owner: Owner) => boolean;
  readonly clearSharedError: (owner: Owner) => void;
}

interface LoreStatusOperation<Owner> {
  readonly owner: Owner;
  promise: Promise<void>;
}

function lifecycleKey(projectId: string, documentId: string): string {
  return `${projectId}\u0000${documentId}`;
}

/** Lore mutations keyed by their origin project and document. */
export function useStudioLoreStatusActions<Owner extends LoreStatusOwner>({
  project,
  projectId,
  setProject,
  currentOwner,
  isCurrentOwner,
  clearSharedError,
}: UseStudioLoreStatusActionsOptions<Owner>) {
  const [lifecycle, setLifecycle] = useState<Record<string, LoreStatusLifecycleState>>({});
  const operationsRef = useRef(new Map<string, LoreStatusOperation<Owner>>());

  const changeLoreStatus = useCallback(
    (documentId: string, loreStatus: LoreStatus): Promise<void> => {
      const owner = currentOwner();
      if (!owner || !project) return Promise.resolve();
      const key = lifecycleKey(owner.projectId, documentId);
      const existing = operationsRef.current.get(key);
      if (existing) return existing.promise;

      const operation: LoreStatusOperation<Owner> = {
        owner,
        promise: Promise.resolve(),
      };
      operationsRef.current.set(key, operation);
      operation.promise = (async () => {
        clearSharedError(owner);
        setLifecycle((current) => ({
          ...current,
          [key]: { isSaving: true, error: null, attemptedStatus: loreStatus },
        }));
        let failure: string | null = null;
        try {
          const { lore_status } = await api.saveLoreStatus(project.id, documentId, loreStatus);
          if (!isCurrentOwner(owner)) return;
          setProject((current) =>
            isCurrentOwner(owner) && current?.id === owner.projectId
              ? {
                  ...current,
                  documents: (current.documents ?? []).map((document) =>
                    document.id === documentId ? { ...document, lore_status } : document,
                  ),
                }
              : current,
          );
        } catch (reason) {
          if (isCurrentOwner(owner)) {
            failure = toErrorMessage(reason, "Unable to update the lore status.");
          }
        } finally {
          if (operationsRef.current.get(key) === operation) {
            operationsRef.current.delete(key);
            if (isCurrentOwner(owner)) {
              setLifecycle((current) => {
                if (failure !== null) {
                  return {
                    ...current,
                    [key]: { isSaving: false, error: failure, attemptedStatus: loreStatus },
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
      return operation.promise;
    },
    [clearSharedError, currentOwner, isCurrentOwner, project, setProject],
  );

  const loreStatusFor = useCallback(
    (documentId: string): LoreStatusLifecycleState =>
      lifecycle[lifecycleKey(projectId, documentId)] ?? IDLE_LORE_STATUS,
    [lifecycle, projectId],
  );
  return { changeLoreStatus, loreStatusFor };
}
