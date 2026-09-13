import { ArrowDown, ArrowUp } from "lucide-react";
import { useRef } from "react";

import type { DocumentSummary, Volume } from "@/app/types/studio";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { StudioDocumentRow } from "./StudioDocumentRow";
import { type NavigatorRowCommands, StudioNavigatorRowActions } from "./StudioNavigatorRowActions";

export interface PendingDocumentMove {
  readonly documentId: string;
  readonly direction: -1 | 1;
}

interface StudioNavigatorDocumentRowsProps {
  rows: DocumentSummary[];
  volumes?: Volume[] | null;
  activeId: string | null;
  isMovingDocument: boolean;
  movingDocument: PendingDocumentMove | null;
  onSelectDocument: (documentId: string) => void;
  onMoveDocument: (documentId: string, direction: -1 | 1) => void | Promise<void>;
  rowCommands?: NavigatorRowCommands | null;
  confirmingDeleteId: string | null;
  onConfirmingDeleteChange: (documentId: string | null) => void;
}

function moveKey(documentId: string, direction: -1 | 1): string {
  return `${documentId}:${direction === -1 ? "up" : "down"}`;
}

/**
 * Reorderable document rows for one navigator group or volume. Beyond the
 * #480 reading-group Move buttons, each row carries its #481 command
 * cluster; when a row disappears after deletion, focus falls back to its
 * surviving neighbor in this same reading group.
 */
export function StudioNavigatorDocumentRows({
  rows,
  volumes = null,
  activeId,
  isMovingDocument,
  movingDocument,
  onSelectDocument,
  onMoveDocument,
  rowCommands = null,
  confirmingDeleteId,
  onConfirmingDeleteChange,
}: StudioNavigatorDocumentRowsProps) {
  const runWithFocusRestoration = useCommandFocusRestoration(isMovingDocument);
  const moveButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const rowButtonRefs = useRef(new Map<string, HTMLButtonElement>());

  /** The row button of the neighbor that survives this document's removal. */
  const neighborFocusFallback = (documentId: string) => {
    const index = rows.findIndex((row) => row.id === documentId);
    if (index === -1) return null;
    const remaining = rows.filter((row) => row.id !== documentId);
    const neighbor = remaining[index] ?? remaining[index - 1] ?? null;
    return neighbor === null ? null : (rowButtonRefs.current.get(neighbor.id) ?? null);
  };

  return rows.map((document, index) => {
    const movingUp = movingDocument?.documentId === document.id && movingDocument.direction === -1;
    const movingDown = movingDocument?.documentId === document.id && movingDocument.direction === 1;
    return (
      <div className="document-row__wrap" key={document.id}>
        <StudioDocumentRow
          document={document}
          isActive={document.id === activeId}
          onSelect={onSelectDocument}
          ref={(node) => {
            if (node) rowButtonRefs.current.set(document.id, node);
            else rowButtonRefs.current.delete(document.id);
          }}
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
        <StudioNavigatorRowActions
          document={document}
          focusFallback={() => neighborFocusFallback(document.id)}
          isConfirmingDelete={confirmingDeleteId === document.id}
          isMutationBusy={isMovingDocument}
          onConfirmingDeleteChange={(open) => onConfirmingDeleteChange(open ? document.id : null)}
          rowCommands={rowCommands}
          runCommand={runWithFocusRestoration}
          volumes={volumes}
        />
      </div>
    );
  });
}
