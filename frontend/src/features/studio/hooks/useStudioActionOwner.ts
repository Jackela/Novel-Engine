import type { Dispatch, SetStateAction } from "react";
import { useCallback, useLayoutEffect, useRef } from "react";

/** Error publication channels shared across the studio action domains. */
export interface StudioActionErrorPublishers {
  readonly review: Dispatch<SetStateAction<string | null>>;
  readonly settings: Dispatch<SetStateAction<string | null>>;
  readonly retryJob: Dispatch<SetStateAction<string | null>>;
  readonly createDocument: Dispatch<SetStateAction<string | null>>;
  readonly moveDocument: Dispatch<SetStateAction<string | null>>;
}

type StudioActionErrorSource = keyof StudioActionErrorPublishers;

/** Identifies the mounted project generation that owns in-flight studio actions. */
export interface StudioActionsOwner {
  readonly projectId: string;
  readonly controllers: Set<AbortController>;
  active: boolean;
}

interface UseStudioActionOwnerOptions {
  readonly projectId: string;
  readonly setError: Dispatch<SetStateAction<string | null>>;
  readonly errorPublishers?: Partial<StudioActionErrorPublishers>;
}

/**
 * Owns the mounted project identity for studio actions: switching projects
 * deactivates and aborts the previous generation's in-flight reads, and error
 * publication is scoped to the current owner with per-channel publisher
 * fallbacks onto the shared error.
 */
export function useStudioActionOwner({
  projectId,
  setError,
  errorPublishers,
}: UseStudioActionOwnerOptions) {
  const ownerRef = useRef<StudioActionsOwner | null>(null);

  useLayoutEffect(() => {
    const owner: StudioActionsOwner = {
      projectId,
      controllers: new Set<AbortController>(),
      active: true,
    };
    ownerRef.current = owner;
    return () => {
      owner.active = false;
      for (const controller of owner.controllers) controller.abort();
      owner.controllers.clear();
      if (ownerRef.current === owner) ownerRef.current = null;
    };
  }, [projectId]);

  const currentOwner = useCallback((): StudioActionsOwner | null => {
    const owner = ownerRef.current;
    return owner?.active && owner.projectId === projectId ? owner : null;
  }, [projectId]);

  const isCurrentOwner = useCallback(
    (owner: StudioActionsOwner): boolean => owner.active && ownerRef.current === owner,
    [],
  );

  const publishError = useCallback(
    (owner: StudioActionsOwner, source: StudioActionErrorSource, value: string | null) => {
      if (!isCurrentOwner(owner)) return;
      const publisher = errorPublishers?.[source] ?? setError;
      publisher((current) => (isCurrentOwner(owner) ? value : current));
    },
    [errorPublishers, isCurrentOwner, setError],
  );

  const clearSharedError = useCallback(
    (owner: StudioActionsOwner) => {
      if (!errorPublishers) publishError(owner, "review", null);
    },
    [errorPublishers, publishError],
  );

  return { currentOwner, isCurrentOwner, publishError, clearSharedError };
}
