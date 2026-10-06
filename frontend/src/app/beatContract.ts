import {
  arrayField,
  field,
  nonnegativeIntegerField,
  objectValue,
  stringField,
} from "./apiContract";

/** One resolved outline beat in the chapter-beat view (#313). */
export interface LinkedBeat {
  title: string;
  content: string;
}

/** One selectable outline beat: the association key is the heading title (DR-043). */
export interface BeatCandidate {
  title: string;
}

/** The outline a chapter's candidate catalog came from, plus the outline count (DR-043). */
export interface BeatOutlineAuthority {
  document_id: string;
  title: string;
  outline_count: number;
}

/**
 * The chapter-beat envelope (#313, DR-043): the resolved association view —
 * the live outline beat, or null when unlinked or vanished — plus the
 * selectable candidate catalog and the outline it was read from. The view is
 * display-only; `beat_ref` authority is the command's normalized requested
 * value (#466).
 */
export interface ChapterBeatView {
  beat: LinkedBeat | null;
  candidates: BeatCandidate[];
  outline: BeatOutlineAuthority | null;
}

function parseLinkedBeat(value: unknown, label: string): LinkedBeat {
  const linked = objectValue(value, label);
  return {
    title: stringField(linked, "title", label),
    content: stringField(linked, "content", label),
  };
}

function parseBeatOutline(value: unknown, label: string): BeatOutlineAuthority {
  const outline = objectValue(value, label);
  return {
    document_id: stringField(outline, "document_id", label),
    title: stringField(outline, "title", label),
    outline_count: nonnegativeIntegerField(outline, "outline_count", label),
  };
}

export function parseChapterBeat(value: unknown): ChapterBeatView {
  const item = objectValue(value, "chapter beat response");
  const beat = field(item, "beat", "chapter beat response");
  const outline = field(item, "outline", "chapter beat response");
  return {
    beat: beat === null ? null : parseLinkedBeat(beat, "chapter beat response.beat"),
    candidates: arrayField(item, "candidates", "chapter beat response", (entry, index) => {
      const label = `chapter beat response.candidates[${index}]`;
      return { title: stringField(objectValue(entry, label), "title", label) };
    }),
    outline: outline === null ? null : parseBeatOutline(outline, "chapter beat response.outline"),
  };
}
