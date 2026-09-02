import type { Dispatch, SetStateAction } from "react";
import { useCallback, useRef, useState } from "react";

import { api } from "@/app/api";
import type { DocumentKind, Project } from "@/app/types/studio";

import { GROUPS } from "../studioConstants";
import { mergeProjectDocumentOrder, summarizeDocument } from "./projectState";
import { toErrorMessage } from "./toErrorMessage";
import { usePendingAction } from "./usePendingAction";

const DOCUMENT_ACTION_KEYS = ["createDocument", "moveDocument"] as const;
type DocumentActionKey = (typeof DOCUMENT_ACTION_KEYS)[number];

interface DocumentActionsOwner {
  readonly projectId: string;
}

interface ScopedCreatingDocument {
  readonly projectId: string;
  readonly kind: DocumentKind;
}

export interface PendingDocumentMove {
  readonly documentId: string;
  readonly direction: -1 | 1;
}

interface ScopedMovingDocument extends PendingDocumentMove {
  readonly projectId: string;
}

interface UseStudioDocumentActionsOptions<Owner extends DocumentActionsOwner> {
  readonly project: Project | null;
  readonly projectId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly setActiveId: Dispatch<SetStateAction<string | null>>;
  readonly currentOwner: () => Owner | null;
  readonly isCurrentOwner: (owner: Owner) => boolean;
  readonly publishError: (owner: Owner, source: DocumentActionKey, value: string | null) => void;
}

/** Document mutations and their exact initiating command identities. */
export function useStudioDocumentActions<Owner extends DocumentActionsOwner>({
  project,
  projectId,
  setProject,
  setActiveId,
  currentOwner,
  isCurrentOwner,
  publishError,
}: UseStudioDocumentActionsOptions<Owner>) {
  const { pending, begin, finish } = usePendingAction<DocumentActionKey>(DOCUMENT_ACTION_KEYS);
  const activeMutationRef = useRef<DocumentActionKey | null>(null);
  const [creatingState, setCreatingState] = useState<ScopedCreatingDocument | null>(null);
  const [movingState, setMovingState] = useState<ScopedMovingDocument | null>(null);

  const beginMutation = useCallback(
    (key: DocumentActionKey) => {
      if (activeMutationRef.current !== null || !begin(key)) return false;
      activeMutationRef.current = key;
      return true;
    },
    [begin],
  );

  const finishMutation = useCallback(
    (key: DocumentActionKey) => {
      if (activeMutationRef.current !== key) return;
      activeMutationRef.current = null;
      finish(key);
    },
    [finish],
  );

  const createDocument = useCallback(
    async (kind: DocumentKind) => {
      const owner = currentOwner();
      if (!owner || !project || !beginMutation("createDocument")) return;
      setCreatingState({ projectId: owner.projectId, kind });
      const count = project.documents.filter((document) => document.kind === kind).length;
      const label = GROUPS.find((group) => group.kind === kind)?.label ?? "Document";
      publishError(owner, "createDocument", null);
      try {
        const document = await api.createDocument(project.id, {
          kind,
          title: kind === "chapter" ? `Chapter ${count + 1}` : `${label} ${count + 1}`,
          content_markdown: kind === "chapter" ? `# Chapter ${count + 1}\n\n` : "",
        });
        if (!isCurrentOwner(owner)) return;
        setProject((current) =>
          isCurrentOwner(owner) && current?.id === owner.projectId
            ? { ...current, documents: [...current.documents, summarizeDocument(document)] }
            : current,
        );
        setActiveId((current) => (isCurrentOwner(owner) ? document.id : current));
      } catch (reason) {
        publishError(owner, "createDocument", toErrorMessage(reason, "Unable to create document."));
      } finally {
        if (isCurrentOwner(owner)) {
          setCreatingState((current) =>
            current?.projectId === owner.projectId && current.kind === kind ? null : current,
          );
          finishMutation("createDocument");
        }
      }
    },
    [
      beginMutation,
      currentOwner,
      finishMutation,
      isCurrentOwner,
      project,
      publishError,
      setActiveId,
      setProject,
    ],
  );

  const moveDocument = useCallback(
    async (documentId: string, direction: -1 | 1) => {
      const owner = currentOwner();
      if (!owner || !project || !beginMutation("moveDocument")) return;
      const ordered = [...project.documents].sort((a, b) => a.position - b.position);
      const index = ordered.findIndex((document) => document.id === documentId);
      const target = index + direction;
      const currentItem = ordered[index];
      const targetItem = ordered[target];
      if (index < 0 || target < 0 || target >= ordered.length || !currentItem || !targetItem) {
        finishMutation("moveDocument");
        return;
      }
      setMovingState({ projectId: owner.projectId, documentId, direction });
      ordered[index] = targetItem;
      ordered[target] = currentItem;
      publishError(owner, "moveDocument", null);
      try {
        const response = await api.reorderDocuments(
          project.id,
          ordered.map((item) => item.id),
        );
        if (!isCurrentOwner(owner)) return;
        setProject((current) =>
          isCurrentOwner(owner) && current?.id === owner.projectId
            ? mergeProjectDocumentOrder(current, response.documents)
            : current,
        );
      } catch (reason) {
        publishError(owner, "moveDocument", toErrorMessage(reason, "Unable to reorder documents."));
      } finally {
        if (isCurrentOwner(owner)) {
          setMovingState((current) =>
            current?.projectId === owner.projectId &&
            current.documentId === documentId &&
            current.direction === direction
              ? null
              : current,
          );
          finishMutation("moveDocument");
        }
      }
    },
    [
      beginMutation,
      currentOwner,
      finishMutation,
      isCurrentOwner,
      project,
      publishError,
      setProject,
    ],
  );

  return {
    createDocument,
    moveDocument,
    pending,
    creatingDocumentKind: creatingState?.projectId === projectId ? creatingState.kind : null,
    movingDocument:
      movingState?.projectId === projectId
        ? { documentId: movingState.documentId, direction: movingState.direction }
        : null,
    isCreatingDocument: pending.createDocument,
    isMovingDocument: pending.moveDocument,
  };
}
