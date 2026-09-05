import { ArrowDown, ArrowUp } from "lucide-react";
import { useRef } from "react";

import type { DocumentSummary } from "@/app/types/studio";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { StudioDocumentRow } from "./StudioDocumentRow";

export interface PendingDocumentMove {
  readonly documentId: string;
  readonly direction: -1 | 1;
}

interface StudioNavigatorDocumentRowsProps {
  rows: DocumentSummary[];
  activeId: string | null;
  isMovingDocument: boolean;
  movingDocument: PendingDocumentMove | null;
  onSelectDocument: (documentId: string) => void;
  onMoveDocument: (documentId: string, direction: -1 | 1) => void | Promise<void>;
}

function moveKey(documentId: string, direction: -1 | 1): string {
  return `${documentId}:${direction === -1 ? "up" : "down"}`;
}

/** Reorderable document rows for one navigator group or volume. */
export function StudioNavigatorDocumentRows({
  rows,
  activeId,
  isMovingDocument,
  movingDocument,
  onSelectDocument,
  onMoveDocument,
}: StudioNavigatorDocumentRowsProps) {
  const runWithFocusRestoration = useCommandFocusRestoration(isMovingDocument);
  const moveButtonRefs = useRef(new Map<string, HTMLButtonElement>());

  return rows.map((document, index) => {
    const movingUp = movingDocument?.documentId === document.id && movingDocument.direction === -1;
    const movingDown = movingDocument?.documentId === document.id && movingDocument.direction === 1;
    return (
      <div className="document-row__wrap" key={document.id}>
        <StudioDocumentRow
          document={document}
          isActive={document.id === activeId}
          onSelect={onSelectDocument}
        />
        <span className="document-row__order">
          <button
            aria-label={`${movingUp ? "Moving" : "Move"} ${document.title} up`}
            aria-busy={movingUp || undefined}
            disabled={isMovingDocument || index === 0}
            onClick={(event) => {
              void runWithFocusRestoration(
                event.currentTarget,
                () => onMoveDocument(document.id, -1),
                () => moveButtonRefs.current.get(moveKey(document.id, 1)) ?? null,
              );
            }}
            ref={(node) => {
              const key = moveKey(document.id, -1);
              if (node) moveButtonRefs.current.set(key, node);
              else moveButtonRefs.current.delete(key);
            }}
            title={movingUp ? "Moving up" : "Move up"}
            type="button"
          >
            <ArrowUp aria-hidden="true" />
          </button>
          <button
            aria-label={`${movingDown ? "Moving" : "Move"} ${document.title} down`}
            aria-busy={movingDown || undefined}
            disabled={isMovingDocument || index === rows.length - 1}
            onClick={(event) => {
              void runWithFocusRestoration(
                event.currentTarget,
                () => onMoveDocument(document.id, 1),
                () => moveButtonRefs.current.get(moveKey(document.id, -1)) ?? null,
              );
            }}
            ref={(node) => {
              const key = moveKey(document.id, 1);
              if (node) moveButtonRefs.current.set(key, node);
              else moveButtonRefs.current.delete(key);
            }}
            title={movingDown ? "Moving down" : "Move down"}
            type="button"
          >
            <ArrowDown aria-hidden="true" />
          </button>
        </span>
      </div>
    );
  });
}
