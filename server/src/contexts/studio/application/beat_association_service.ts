import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { type OutlineBeat, splitOutlineBeats } from "./outline_beats.js";
import type { DocumentWithCurrent, ProjectScope } from "./ports/studio_store.js";
import { type StudioStore, scopeForPrincipal } from "./ports/studio_store.js";

/**
 * The chapter beat association surface (#313): a chapter links to at most one
 * beat of its project's outline document. The stored reference is the beat's
 * heading title; every read resolves it against the outline's current
 * sections, so a renamed or removed heading degrades to unlinked and never
 * errors.
 */
export class BeatAssociationService {
  private readonly store: StudioStore;
  private readonly now: () => Date;

  constructor(store: StudioStore, now: () => Date = () => new Date()) {
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
  ): Record<string, unknown> {
    const scope = scopeForPrincipal(principal);
    const requested = input.beat === null ? null : input.beat.trim();
    if (requested !== null && requested === "") {
      throw new InvalidOperationError("An outline beat title is required to link a chapter.");
    }
    if (requested !== null) {
      const known = projectOutlineBeats(this.store, scope, projectId).some(
        (beat) => beat.title === requested,
      );
      if (!known) {
        throw new InvalidOperationError(`The outline has no beat titled "${requested}".`);
      }
    }
    const updated = this.store.setBeatReference(scope, projectId, documentId, {
      beatRef: requested,
      now: this.now(),
    });
    return chapterBeatView(updated, projectOutlineBeats(this.store, scope, projectId));
  }

  /** The chapter's effective association, resolved against the live outline. */
  chapterBeat(
    principal: Principal,
    projectId: string,
    documentId: string,
  ): Record<string, unknown> {
    const scope = scopeForPrincipal(principal);
    const document = this.store.findDocument(scope, projectId, documentId);
    return chapterBeatView(document, projectOutlineBeats(this.store, scope, projectId));
  }
}

/**
 * The beats of the project's outline document in document order. The first
 * outline-kind document in the project's reading order is the authority; a
 * project without an outline has no beats.
 */
export function projectOutlineBeats(
  store: StudioStore,
  scope: ProjectScope,
  projectId: string,
): OutlineBeat[] {
  const outline = store
    .findDocuments(scope, projectId)
    .find((document) => document.kind === "outline");
  const revision = outline?.currentRevision ?? null;
  if (outline === undefined || revision === null) {
    return [];
  }
  return splitOutlineBeats(revision.contentMarkdown);
}

/** A chapter's linked beat right now; dangling references resolve to null. */
export function linkedChapterBeat(
  store: StudioStore,
  scope: ProjectScope,
  projectId: string,
  document: DocumentWithCurrent,
): OutlineBeat | null {
  const reference = document.beatRef;
  if (reference === null || reference === "") {
    return null;
  }
  return (
    projectOutlineBeats(store, scope, projectId).find((beat) => beat.title === reference) ?? null
  );
}

/** The read contract: `beat` is null when unlinked or when the beat vanished. */
function chapterBeatView(
  document: DocumentWithCurrent,
  beats: OutlineBeat[],
): Record<string, unknown> {
  const resolved =
    document.beatRef === null
      ? null
      : (beats.find((beat) => beat.title === document.beatRef) ?? null);
  if (resolved === null) {
    return { beat: null };
  }
  return { beat: { title: resolved.title, content: resolved.content } };
}
