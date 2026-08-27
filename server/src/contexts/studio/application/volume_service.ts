import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { documentPayload, volumePayload } from "./payloads.js";
import type { StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";

/**
 * Volume surface of the fixed two-level hierarchy (ADR-0005): CRUD with the
 * at-least-one-volume invariant, chapter placement, and whole-set volume
 * reorder. Method names deliberately avoid stems shared with frontend
 * client methods (create/update/delete/reorder/move).
 */
export class VolumeService {
  private readonly store: StudioStore;
  private readonly now: () => Date;

  constructor(store: StudioStore, now: () => Date = () => new Date()) {
    this.store = store;
    this.now = now;
  }

  listVolumes(principal: Principal, projectId: string): Record<string, unknown>[] {
    return this.store
      .findVolumes(scopeForPrincipal(principal), projectId)
      .map((volume) => volumePayload(volume));
  }

  newVolume(
    principal: Principal,
    projectId: string,
    input: { title: string },
  ): Record<string, unknown> {
    const title = requireVolumeTitle(input.title);
    const scope = scopeForPrincipal(principal);
    return volumePayload(this.store.addVolume(scope, projectId, { title, now: this.now() }));
  }

  retitleVolume(
    principal: Principal,
    projectId: string,
    volumeId: string,
    input: { title: string },
  ): Record<string, unknown> {
    const title = requireVolumeTitle(input.title);
    const scope = scopeForPrincipal(principal);
    return volumePayload(
      this.store.alterVolume(scope, projectId, volumeId, { title, now: this.now() }),
    );
  }

  /** Refuses through the store when it is the project's last volume. */
  removeVolume(principal: Principal, projectId: string, volumeId: string): void {
    this.store.dropVolume(scopeForPrincipal(principal), projectId, volumeId);
  }

  /** Chapters land at the tail of their target volume; other kinds refuse. */
  placeChapter(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: { volumeId: string },
  ): Record<string, unknown> {
    const placed = this.store.placeDocumentInVolume(
      scopeForPrincipal(principal),
      projectId,
      documentId,
      { volumeId: input.volumeId, now: this.now() },
    );
    return documentPayload(placed);
  }

  /** Whole-set reorder: every project volume exactly once, positions 1..n. */
  applyVolumeOrder(
    principal: Principal,
    projectId: string,
    volumeIds: string[],
  ): Record<string, unknown>[] {
    return this.store
      .renumberVolumes(scopeForPrincipal(principal), projectId, volumeIds, this.now())
      .map((volume) => volumePayload(volume));
  }
}

/** Volume titles follow the same whitespace/emptiness contract as projects. */
function requireVolumeTitle(raw: string): string {
  const title = raw.trim();
  if (title === "") {
    throw new InvalidOperationError("Volume title is required.");
  }
  return title;
}
