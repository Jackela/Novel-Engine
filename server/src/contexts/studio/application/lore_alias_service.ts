import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { isLoreStatus, type LoreStatus } from "../domain/kinds.js";
import { normalizeLoreAliases, parseLoreAliases } from "./lorebook.js";
import type { LoreAliasPayload, LoreStatusPayload } from "./payload_schemas/lore.js";
import { loreAliasPayload, loreStatusPayload } from "./payloads.js";
import type { StudioStore } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";

/**
 * The lore product surface (#315, #444): the extra prompt keys and the
 * lifecycle status of a character or world document. Alias reads answer for
 * every document (non-lore kinds simply have none); alias and status writes
 * are refused outside the lorebook kinds. Normalization is a write-path
 * contract — readers always see trimmed, deduped aliases and a closed-set
 * status. Neither write mints a revision.
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

  /**
   * Set the lifecycle status (#444, ADR-0006): a closed-enum write that
   * flips injection gating without minting a revision. Non-lore kinds and
   * non-enum values are refused — a programming error or forged request
   * must surface, never silently no-op.
   */
  changeDocumentLoreStatus(
    principal: Principal,
    projectId: string,
    documentId: string,
    input: { status: string },
  ): LoreStatusPayload {
    if (!isLoreStatus(input.status)) {
      throw new InvalidOperationError(
        `Unsupported lore lifecycle status: ${input.status} (expected draft, stable, or deprecated).`,
      );
    }
    const status: LoreStatus = input.status;
    this.store.setLoreStatus(scopeForPrincipal(principal), projectId, documentId, {
      status,
      now: this.now(),
    });
    return loreStatusPayload(status);
  }
}
