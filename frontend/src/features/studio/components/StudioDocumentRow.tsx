import { FileText } from "lucide-react";

import type { DocumentSummary } from "@/app/types/studio";

interface StudioDocumentRowProps {
  document: DocumentSummary;
  isActive: boolean;
  onSelect: (documentId: string) => void;
}

/**
 * One document row inside the studio navigator (#376). Shows the in-volume
 * ordinal (`document.position`), the associated outline beat title
 * (`document.beat_ref`, a title soft link — never an ordinal), and — for
 * lore entries — the lifecycle status badge (`document.lore_status`, #444).
 */
export function StudioDocumentRow({ document, isActive, onSelect }: StudioDocumentRowProps) {
  // The row's accessible name stays the document title plus its meaningful
  // state (linked beat title, lore status); the ordinal and status badges
  // themselves are presentational, so assistive tech and role-based selectors
  // see one stable name per row (#376, #444).
  const beat = document.beat_ref ? ` (${document.beat_ref})` : "";
  const status = document.lore_status ? ` — ${document.lore_status}` : "";
  const label = `${document.title}${beat}${status}`;

  return (
    <button
      aria-current={isActive ? "page" : undefined}
      aria-label={label}
      className={isActive ? "document-row document-row--active" : "document-row"}
      onClick={() => onSelect(document.id)}
      type="button"
    >
      <FileText aria-hidden="true" />
      <span className="document-row__ordinal" aria-hidden="true">
        {document.position}
      </span>
      <span>{document.title}</span>
      {document.beat_ref ? <span className="document-row__beat">{document.beat_ref}</span> : null}
      {document.lore_status ? (
        <span
          aria-hidden="true"
          className={`document-row__lore-status document-row__lore-status--${document.lore_status}`}
        >
          {document.lore_status}
        </span>
      ) : null}
    </button>
  );
}
