import type { ComponentProps } from "react";
import type { NavigateFunction } from "react-router-dom";

import type { DocumentKind, LoreStatus, StudioDocument } from "@/app/types/studio";

import type { StudioNavigator } from "../StudioNavigator";
import { isLoreEntryKind } from "../studioConstants";
import type { InspectorLoreStatusModel } from "../studioInspectorTypes";

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
    onCreateDocument: (kind) => void createDocument(kind),
    onMoveDocument: (documentId, direction) => void moveDocument(documentId, direction),
  };
}

/**
 * Adapt one active domain document into the concrete Lore editor seam. The
 * returned submit function preserves the mutation owner's completion Promise.
 */
export function buildLoreStatusModel(
  document: StudioDocument | null,
  changeLoreStatus: (documentId: string, status: LoreStatus) => Promise<void>,
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
    submit: (status) => changeLoreStatus(documentId, status),
  };
}
