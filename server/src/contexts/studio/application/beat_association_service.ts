import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { type OutlineBeat, splitOutlineBeats } from "./outline_beats.js";
import type { BeatOutlineAuthority, ChapterBeatPayload } from "./payload_schemas/beat.js";
import { chapterBeatPayload } from "./payloads.js";
import type { DocumentStore, DocumentWithCurrent } from "./ports/document_store.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";

/**
 * The chapter beat association surface (#313): a chapter links to at most one
 * beat of its project's outline document. The stored reference is the beat's
 * heading title; every read resolves it against the outline's current
 * sections, so a renamed or removed heading degrades to unlinked and never
 * errors. The candidate catalog and its authoritative outline travel with
 * every view (DR-043), so the association never depends on recall or on a
 * silently chosen outline.
 */
export class BeatAssociationService {
  private readonly store: DocumentStore;
  private readonly now: () => Date;

  constructor(store: DocumentStore, now: () => Date = () => new Date()) {
    this.store = store;
    this.now = now;
  }

  /**
   * Link the chapter to a current outline beat (or clear the link with
   * null). Requesting a beat the outline no longer holds is refused; a link
   * whose beat vanishes later simply stops resolving instead.
   */
  linkChapterBeat(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: { beat: string | null },
  ): ChapterBeatPayload {
    const scope = scopeForPrincipal(principal);
    const requested = input.beat === null ? null : input.beat.trim();
    if (requested !== null && requested === "") {
      throw new InvalidOperationError("An outline beat title is required to link a chapter.");
    }
    const authority = projectOutlineAuthority(this.store, scope, projectId);
    if (requested !== null && !authority.beats.some((beat) => beat.title === requested)) {
      throw new InvalidOperationError(`The outline has no beat titled "${requested}".`);
    }
    const updated = this.store.setBeatReference(scope, projectId, documentId, {
      beatRef: requested,
      now: this.now(),
    });
    return chapterBeatView(updated, authority);
  }

  /** The chapter's effective association, resolved against the live outline. */
  chapterBeat(principal: Principal, projectId: string, documentId: string): ChapterBeatPayload {
    const scope = scopeForPrincipal(principal);
    const document = this.store.findDocument(scope, projectId, documentId);
    return chapterBeatView(document, projectOutlineAuthority(this.store, scope, projectId));
  }
}

/** The outline document whose beats a project's chapters associate with. */
export interface OutlineAuthority {
  readonly beats: OutlineBeat[];
  readonly outline: { readonly id: string; readonly title: string } | null;
  /** Outline-kind documents in the project; more than one is disclosed, never hidden. */
  readonly outlineCount: number;
}

/**
 * The beats of the project's outline document in document order, together
 * with which outline was read and how many exist. The first outline-kind
 * document in the project's reading order is the authority — an explicit,
 * disclosed rule (DR-043): the payload names that document and reports the
 * total count, so a project with several outlines surfaces the choice instead
 * of silently dropping the others. A project without an outline has no beats.
 */
function projectOutlineAuthority(
  store: DocumentStore,
  scope: ProjectScope,
  projectId: string,
): OutlineAuthority {
  const outlines = store
    .findDocuments(scope, projectId)
    .filter((document) => document.kind === "outline");
  const outline = outlines[0] ?? null;
  const revision = outline?.currentRevision ?? null;
  return {
    beats: outline === null || revision === null ? [] : splitOutlineBeats(revision.contentMarkdown),
    outline: outline === null ? null : { id: outline.id, title: outline.title },
    outlineCount: outlines.length,
  };
}

function outlineAuthorityPayload(authority: OutlineAuthority): BeatOutlineAuthority | null {
  return authority.outline === null
    ? null
    : {
        document_id: authority.outline.id,
        title: authority.outline.title,
        outline_count: authority.outlineCount,
      };
}

/** The read contract: `beat` is null when unlinked or when the beat vanished. */
export function chapterBeatView(
  document: DocumentWithCurrent,
  authority: OutlineAuthority,
): ChapterBeatPayload {
  const resolved =
    document.beatRef === null
      ? null
      : (authority.beats.find((beat) => beat.title === document.beatRef) ?? null);
  return chapterBeatPayload(resolved, authority.beats, outlineAuthorityPayload(authority));
}
