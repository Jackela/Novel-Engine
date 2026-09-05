import type { Dispatch, SetStateAction } from "react";
import { useCallback, useRef, useState } from "react";

import type { Project } from "@/app/types/studio";

import { mergeProjectNarrowField, type NarrowSummaryPatch } from "./projectState";
import { toErrorMessage } from "./toErrorMessage";

interface NarrowFieldOwner {
  readonly projectId: string;
}

/** Per-document pending lifecycle of one narrow summary field (#466). */
export interface NarrowFieldLifecycleState<Value> {
  readonly isSaving: boolean;
  readonly error: string | null;
  readonly attempted: Value | null;
}

interface NarrowFieldIntent<Value> {
  readonly epoch: number;
  readonly requested: Value;
  promise: Promise<void>;
}

/**
 * Invoke one narrow summary command and settle it under the task 3.4 causal
 * contract: every command captures its project, Document, current revision,
 * and a field-specific intent epoch. A response patches only its owned
 * summary field, and only while its epoch is still the latest intent for
 * that document and the captured revision still owns the shell row.
 * Anything older — reverse-order same-revision settlements, or a response
 * outrun by a newer revision — is stale and ignored.
 */
export interface UseNarrowSummaryFieldOptions<Owner extends NarrowFieldOwner, Value> {
  readonly project: Project | null;
  readonly projectId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly currentOwner: () => Owner | null;
  readonly isCurrentOwner: (owner: Owner) => boolean;
  readonly clearSharedError: (owner: Owner) => void;
  /** Human fallback when the command fails on its own surface. */
  readonly failureMessage: string;
  /** Performs the command and returns the value its field must store. */
  readonly invoke: (projectId: string, documentId: string, requested: Value) => Promise<Value>;
  readonly patchFor: (value: Value) => NarrowSummaryPatch;
}

function lifecycleKey(projectId: string, documentId: string): string {
  return `${projectId}\u0000${documentId}`;
}

export function useNarrowSummaryField<Owner extends NarrowFieldOwner, Value>({
  project,
  projectId,
  setProject,
  currentOwner,
  isCurrentOwner,
  clearSharedError,
  failureMessage,
  invoke,
  patchFor,
}: UseNarrowSummaryFieldOptions<Owner, Value>) {
  const [lifecycle, setLifecycle] = useState<Record<string, NarrowFieldLifecycleState<Value>>>({});
  const pendingRef = useRef(new Map<string, NarrowFieldIntent<Value>>());

  const run = useCallback(
    (documentId: string, requested: Value): Promise<void> => {
      const owner = currentOwner();
      if (!owner || !project) return Promise.resolve();
      const key = lifecycleKey(owner.projectId, documentId);
      // Duplicate activation of the identical in-flight request is one
      // command; a changed requested value supersedes it as a newer intent.
      const existing = pendingRef.current.get(key);
      if (existing && existing.requested === requested) return existing.promise;

      const capturedRevision =
        project.documents.find((document) => document.id === documentId)?.current_revision_id ??
        null;
      if (capturedRevision === null) return Promise.resolve();

      const intent: NarrowFieldIntent<Value> = {
        epoch: (existing?.epoch ?? 0) + 1,
        requested,
        promise: Promise.resolve(),
      };
      pendingRef.current.set(key, intent);
      const isLatestIntent = () => pendingRef.current.get(key) === intent;
      intent.promise = (async () => {
        clearSharedError(owner);
        setLifecycle((current) => ({
          ...current,
          [key]: { isSaving: true, error: null, attempted: requested },
        }));
        let failure: string | null = null;
        try {
          const stored = await invoke(project.id, documentId, requested);
          if (!isCurrentOwner(owner) || !isLatestIntent()) return;
          setProject((current) =>
            isCurrentOwner(owner) && current?.id === owner.projectId
              ? mergeProjectNarrowField(
                  current,
                  { projectId: owner.projectId, documentId, revisionId: capturedRevision },
                  patchFor(stored),
                )
              : current,
          );
        } catch (reason) {
          if (isCurrentOwner(owner) && isLatestIntent()) {
            failure = toErrorMessage(reason, failureMessage);
          }
        } finally {
          if (isLatestIntent()) {
            pendingRef.current.delete(key);
            if (isCurrentOwner(owner)) {
              setLifecycle((current) => {
                if (failure !== null) {
                  return {
                    ...current,
                    [key]: { isSaving: false, error: failure, attempted: requested },
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
    [
      clearSharedError,
      currentOwner,
      failureMessage,
      invoke,
      isCurrentOwner,
      patchFor,
      project,
      setProject,
    ],
  );

  const lifecycleFor = useCallback(
    (documentId: string): NarrowFieldLifecycleState<Value> =>
      lifecycle[lifecycleKey(projectId, documentId)] ?? {
        isSaving: false,
        error: null,
        attempted: null,
      },
    [lifecycle, projectId],
  );

  return { run, lifecycleFor };
}
