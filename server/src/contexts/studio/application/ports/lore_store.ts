import type { LoreStatus } from "../../domain/kinds.js";
import type { DocumentWithCurrent, ProjectScope } from "./studio_store.js";

/** The alias write (#315): the normalized key list of one lore entry. */
export interface SetLoreAliasesInput {
  aliases: string[];
  now: Date;
}

/** The lifecycle-status write (#444): a closed `LoreStatus` value. */
export interface SetLoreStatusInput {
  status: LoreStatus;
  now: Date;
}

/**
 * Lorebook-port of the authoring core (#315), kept in its own module so the
 * authoring StudioStore stays within its file-size budget. Method names avoid
 * stems shared with frontend client methods. Aliases and lifecycle status are
 * DOCUMENT-level state: revision metadata is replaced wholesale by ordinary
 * saves, so prompt keys and gating state must live outside revisions to
 * survive them — no revision is minted here and immutable history stays
 * untouched.
 */
export interface StudioLoreStore {
  /**
   * Replace the alias list of a character or world document with the given
   * normalized values. Other kinds are refused; unknown ids surface as
   * not-found exactly like the rest of the authoring store.
   */
  setLoreAliases(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: SetLoreAliasesInput,
  ): DocumentWithCurrent;
  /**
   * Set the lifecycle status of a character or world document (#444).
   * Refuses other kinds; mints no revision.
   */
  setLoreStatus(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: SetLoreStatusInput,
  ): DocumentWithCurrent;
}
