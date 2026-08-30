import type { Principal } from "../../../shared/application/ports/auth.js";
import { normalizeLoreAliases, parseLoreAliases } from "./lorebook.js";
import type { LoreAliasPayload } from "./payload_schemas/lore.js";
import { loreAliasPayload } from "./payloads.js";
import type { StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";

/**
 * The lore-alias product surface (#315): the extra prompt keys of a character
 * or world document. Reads answer for every document (non-lore kinds simply
 * have none); writes are refused outside the lorebook kinds. Normalization is
 * a write-path contract — readers always see trimmed, deduped aliases.
 */
export class LoreAliasService {
  private readonly store: StudioStore;
  private readonly now: () => Date;

  constructor(store: StudioStore, now: () => Date = () => new Date()) {
    this.store = store;
    this.now = now;
  }

  /** The stored alias list of one document, normalized defensively on read. */
  listDocumentLoreAliases(principal: Principal, projectId: string, documentId: string): string[] {
    const document = this.store.findDocument(scopeForPrincipal(principal), projectId, documentId);
    return normalizeLoreAliases(parseLoreAliases(document.loreAliasesJson));
  }

  /** Replace the alias list; no revision is minted and content stays untouched. */
  overwriteDocumentAliases(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: { aliases: readonly string[] },
  ): LoreAliasPayload {
    const normalized = normalizeLoreAliases(input.aliases);
    this.store.setLoreAliases(scopeForPrincipal(principal), projectId, documentId, {
      aliases: normalized,
      now: this.now(),
    });
    return loreAliasPayload(normalized);
  }
}
