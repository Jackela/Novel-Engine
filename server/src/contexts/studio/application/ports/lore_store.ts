import type { DocumentWithCurrent, ProjectScope } from "./studio_store.js";

/** The alias write (#315): the normalized key list of one lore entry. */
export interface SetLoreAliasesInput {
  aliases: string[];
  now: Date;
}

/**
 * Lorebook-port of the authoring core (#315), kept in its own module so the
 * authoring StudioStore stays within its file-size budget. Method names avoid
 * stems shared with frontend client methods. Aliases are DOCUMENT-level state:
 * revision metadata is replaced wholesale by ordinary saves, so prompt keys
 * must live outside revisions to survive them — no revision is minted here
 * and immutable history stays untouched.
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
}
