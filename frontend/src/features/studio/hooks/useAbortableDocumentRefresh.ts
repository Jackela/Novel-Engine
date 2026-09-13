import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useCallback, useEffect, useRef } from "react";

import type { Project, StudioDocument } from "@/app/types/studio";

import type { DocumentDraftOwner } from "./documentDraftState";
import { mergeProjectDocument } from "./projectState";
import { loadLatestDocument } from "./useDocumentDraftAutosave";

interface DocumentRefreshArgs {
  readonly owner: DocumentDraftOwner;
  readonly projectId: string;
  readonly isCurrentOwner: (candidate: DocumentDraftOwner) => boolean;
  readonly isCurrentProject: (candidate: DocumentDraftOwner) => boolean;
  readonly loadedRevision: MutableRefObject<string | null>;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
}

function abortOwnerRequests(
  requests: Map<DocumentDraftOwner["token"], Set<AbortController>>,
  ownerToken: DocumentDraftOwner["token"],
): void {
  const controllers = requests.get(ownerToken);
  if (!controllers) return;
  for (const controller of controllers) controller.abort();
  requests.delete(ownerToken);
}

function abortAllRequests(requests: Map<DocumentDraftOwner["token"], Set<AbortController>>): void {
  for (const ownerToken of requests.keys()) abortOwnerRequests(requests, ownerToken);
}

/**
 * Owns the abortable-request registry for one project/document identity and
 * the guarded "refresh to the latest committed document" command. In-flight
 * requests abort when the owner token rotates or the hook unmounts, and the
 * project merge only publishes documents that still match the owner.
 */
export function useAbortableDocumentRefresh({
  owner,
  projectId,
  isCurrentOwner,
  isCurrentProject,
  loadedRevision,
  setProject,
}: DocumentRefreshArgs) {
  const requestControllersRef = useRef(
    new Map<DocumentDraftOwner["token"], Set<AbortController>>(),
  );

  useEffect(
    () => () => {
      abortOwnerRequests(requestControllersRef.current, owner.token);
    },
    [owner.token],
  );
  useEffect(() => () => abortAllRequests(requestControllersRef.current), []);

  const refreshLatestDocument = useCallback(
    async (documentId: string): Promise<StudioDocument | null> => {
      if (!isCurrentProject(owner) || documentId !== owner.documentId) return null;
      const controller = new AbortController();
      const ownerControllers =
        requestControllersRef.current.get(owner.token) ?? new Set<AbortController>();
      ownerControllers.add(controller);
      requestControllersRef.current.set(owner.token, ownerControllers);
      try {
        const document = await loadLatestDocument(projectId, documentId, controller.signal);
        if (!isCurrentProject(owner) || controller.signal.aborted) return null;
        if (isCurrentOwner(owner)) loadedRevision.current = document.current_revision_id;
        setProject((current) =>
          isCurrentProject(owner) && current?.id === owner.projectId
            ? mergeProjectDocument(current, document)
            : current,
        );
        return document;
      } finally {
        ownerControllers.delete(controller);
        if (ownerControllers.size === 0) requestControllersRef.current.delete(owner.token);
      }
    },
    [isCurrentOwner, isCurrentProject, loadedRevision, owner, projectId, setProject],
  );

  return { refreshLatestDocument };
}
