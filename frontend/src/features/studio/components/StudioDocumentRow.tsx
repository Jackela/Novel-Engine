import { FileText } from 'lucide-react';

import type { StudioDocument } from '@/app/types/studio';

interface StudioDocumentRowProps {
  document: StudioDocument;
  isActive: boolean;
  onSelect: (documentId: string) => void;
}

/**
 * One document row inside the studio navigator (#376). Shows the in-volume
 * ordinal (`document.position`) and, when linked, the associated outline
 * beat title (`document.beat_ref`, a title soft link — never an ordinal).
 */
export function StudioDocumentRow({ document, isActive, onSelect }: StudioDocumentRowProps) {
  return (
    <button
      aria-current={isActive ? 'page' : undefined}
      className={isActive ? 'document-row document-row--active' : 'document-row'}
      onClick={() => onSelect(document.id)}
      type="button"
    >
      <FileText aria-hidden="true" />
      <span className="document-row__ordinal" aria-label={`Chapter ${document.position}`}>
        {document.position}
      </span>
      <span>{document.title}</span>
      {document.beat_ref ? <span className="document-row__beat">{document.beat_ref}</span> : null}
    </button>
  );
}
