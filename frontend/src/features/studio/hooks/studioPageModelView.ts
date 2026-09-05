import type { ComponentProps } from "react";
import type { NavigateFunction } from "react-router-dom";

import type { DocumentKind, DocumentSummary, LoreStatus } from "@/app/types/studio";

import type { StudioNavigator } from "../StudioNavigator";
import { isLoreEntryKind } from "../studioConstants";
import type { InspectorLoreStatusModel } from "../studioInspectorTypes";
import type { LoreStatusLifecycleState } from "./useStudioLoreStatusActions";

type NavigatorProps = ComponentProps<typeof StudioNavigator>;

export interface StudioNavigatorModel
  extends Omit<NavigatorProps, "onNavigateSection" | "onCreateDocument" | "onMoveDocument"> {
  createDocument: (kind: DocumentKind) => void | Promise<void>;
  moveDocument: (documentId: string, direction: -1 | 1) => void | Promise<void>;
}

export function buildStudioNavigatorProps(
  model: StudioNavigatorModel,
  navigate: NavigateFunction,
): NavigatorProps {
  const { createDocument, moveDocument, ...state } = model;
  return {
    ...state,
    onNavigateSection: (nextSection) => navigate(`/projects/${model.project.id}/${nextSection}`),
    onCreateDocument: createDocument,
    onMoveDocument: moveDocument,
  };
}

/**
 * Adapt the active shell summary into the concrete Lore editor seam. The
 * returned submit function preserves the mutation owner's completion Promise.
 */
export function buildLoreStatusModel(
  document: Pick<DocumentSummary, "id" | "kind" | "lore_status"> | null,
  changeLoreStatus: (documentId: string, status: LoreStatus) => Promise<void>,
  lifecycle: LoreStatusLifecycleState,
): InspectorLoreStatusModel | null {
  if (
    document === null ||
    !isLoreEntryKind(document.kind) ||
    document.lore_status === null ||
    document.lore_status === undefined
  ) {
    return null;
  }
  const documentId = document.id;
  return {
    documentId,
    savedStatus: document.lore_status,
    isSaving: lifecycle.isSaving,
    error: lifecycle.error,
    attemptedStatus: lifecycle.attemptedStatus,
    submit: (status) => changeLoreStatus(documentId, status),
  };
}
