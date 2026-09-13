import type { MutableRefObject } from "react";
import { useCallback, useState } from "react";

import type { DocumentDraftOwner } from "./documentDraftState";

interface ConflictActionState {
  readonly ownerToken: DocumentDraftOwner["token"];
  readonly pending: boolean;
}

interface ConflictActionGateArgs {
  readonly owner: DocumentDraftOwner;
  readonly isCurrentOwner: (candidate: DocumentDraftOwner) => boolean;
  readonly conflictActionPendingRef: MutableRefObject<DocumentDraftOwner["token"] | null>;
}

/**
 * Owns the conflict-action pending gate shared by the explicit conflict
 * commands and the autosave loop. The React pending flag is mirrored into the
 * caller-owned ref so the gate can also be re-checked synchronously before a
 * save or refresh starts.
 */
export function useConflictActionGate({
  owner,
  isCurrentOwner,
  conflictActionPendingRef,
}: ConflictActionGateArgs) {
  const [conflictActionState, setConflictActionState] = useState<ConflictActionState>({
    ownerToken: owner.token,
    pending: false,
  });
  const isConflictActionPending =
    conflictActionState.ownerToken === owner.token && conflictActionState.pending;

  const beginConflictAction = useCallback(() => {
    setConflictActionState({ ownerToken: owner.token, pending: true });
    conflictActionPendingRef.current = owner.token;
  }, [conflictActionPendingRef, owner]);

  const finishConflictAction = useCallback(() => {
    if (!isCurrentOwner(owner)) return;
    setConflictActionState({ ownerToken: owner.token, pending: false });
    if (conflictActionPendingRef.current === owner.token) {
      conflictActionPendingRef.current = null;
    }
  }, [conflictActionPendingRef, isCurrentOwner, owner]);

  return { beginConflictAction, finishConflictAction, isConflictActionPending };
}
