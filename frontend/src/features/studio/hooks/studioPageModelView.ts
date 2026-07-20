import type { ComponentProps } from 'react';
import type { NavigateFunction } from 'react-router-dom';

import type { DocumentKind } from '@/app/types/studio';

import { StudioNavigator } from '../StudioNavigator';

type NavigatorProps = ComponentProps<typeof StudioNavigator>;

export interface StudioNavigatorModel extends Omit<
  NavigatorProps,
  'onNavigateSection' | 'onCreateDocument' | 'onMoveDocument'
> {
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
