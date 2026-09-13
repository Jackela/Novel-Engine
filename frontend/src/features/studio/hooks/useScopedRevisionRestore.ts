import { useCallback, useRef, useState } from "react";

interface PendingRestore {
  readonly invocation: number;
  readonly revisionId: string;
}

/** Keeps History pending state attached to the document that started it. */
export function useScopedRevisionRestore(
  ownerKey: string,
  restoreRevision: (revisionId: string) => Promise<void>,
) {
  const invocationRef = useRef(0);
  const activeByOwnerRef = useRef(new Map<string, Promise<void>>());
  const [pendingByOwner, setPendingByOwner] = useState<ReadonlyMap<string, PendingRestore>>(
    () => new Map(),
  );
  const restoringRevisionId = pendingByOwner.get(ownerKey)?.revisionId ?? null;

  const restoreScopedRevision = useCallback(
    (revisionId: string): Promise<void> => {
      const active = activeByOwnerRef.current.get(ownerKey);
      if (active) return active;
      const invocation = invocationRef.current + 1;
      invocationRef.current = invocation;
      setPendingByOwner((current) => new Map(current).set(ownerKey, { invocation, revisionId }));
      let pending!: Promise<void>;
      pending = (async () => {
        try {
          await restoreRevision(revisionId);
        } finally {
          if (activeByOwnerRef.current.get(ownerKey) === pending) {
            activeByOwnerRef.current.delete(ownerKey);
          }
          setPendingByOwner((current) => {
            if (current.get(ownerKey)?.invocation !== invocation) return current;
            const next = new Map(current);
            next.delete(ownerKey);
            return next;
          });
        }
      })();
      activeByOwnerRef.current.set(ownerKey, pending);
      return pending;
    },
    [ownerKey, restoreRevision],
  );

  return { restoringRevisionId, restoreRevision: restoreScopedRevision };
}
