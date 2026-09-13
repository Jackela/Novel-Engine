import { useCallback, useEffect, useMemo, useRef } from "react";

import { createDocumentDraftOwner, type DocumentDraftOwner } from "./documentDraftState";

/** Owns the active project/document identity and its mounted lifecycle. */
export function useDocumentDraftOwner(projectId: string, documentId: string | null) {
  const owner = useMemo(
    () => createDocumentDraftOwner(projectId, documentId),
    [documentId, projectId],
  );
  const ownerRef = useRef<DocumentDraftOwner | null>(owner);
  const mountedRef = useRef(false);
  const isCurrentOwner = useCallback(
    (candidate: DocumentDraftOwner) => ownerRef.current === candidate,
    [],
  );
  const isCurrentProject = useCallback(
    (candidate: DocumentDraftOwner) =>
      mountedRef.current && ownerRef.current?.projectId === candidate.projectId,
    [],
  );

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    ownerRef.current = owner;
    return () => {
      if (ownerRef.current === owner) ownerRef.current = null;
    };
  }, [owner]);

  return { owner, ownerRef, mountedRef, isCurrentOwner, isCurrentProject };
}
