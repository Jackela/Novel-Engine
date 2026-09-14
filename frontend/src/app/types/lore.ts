import type { paths } from "../../../generated/api-types";

/**
 * The lore family's wire types, split from `types/studio.ts` at the
 * file-size gate: the lore lifecycle status (#444) and the wizard's
 * extraction request body and candidate shape (#614), both derived from the
 * OpenAPI baseline. `types/studio.ts` re-exports `LoreStatus` for its
 * existing consumers.
 */

type LoreStatusWriteBody = NonNullable<
  paths["/api/projects/{projectId}/documents/{documentId}/lore-status"]["put"]
>["requestBody"]["content"]["application/json"];

/** The lore lifecycle status (#444); only `stable` entries inject (ADR-0006). */
export type LoreStatus = LoreStatusWriteBody["lore_status"];

type LoreExtractRequestBody = NonNullable<
  paths["/api/projects/{projectId}/lore-extractions"]["post"]
>["requestBody"]["content"]["application/json"];

/**
 * The wizard's one extraction request body: one segment plus the named
 * provider — models are resolved server-side, never sent.
 */
export type LoreExtractRequest = LoreExtractRequestBody;

/** One suggested lore entry; a suggestion, never persisted content. */
export interface LoreExtractCandidate {
  kind: "character" | "world";
  title: string;
  aliases: string[];
  summary: string;
}
