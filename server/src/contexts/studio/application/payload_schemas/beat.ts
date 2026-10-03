import { type Static, Type } from "@fastify/type-provider-typebox";

/**
 * Chapter beat payload SSOT (#440, DR-043): the resolved association view
 * emitted by `BeatAssociationService` — the live outline beat, or `null` when
 * the chapter is unlinked or its stored reference vanished from the outline
 * (#313) — plus the selectable candidate catalog and the outline the catalog
 * was read from. The nullable objects keep the #405 `Type.Unsafe` +
 * `nullable: true` literal shape so the OpenAPI 3.0 representation is
 * unchanged.
 */

/** One resolved outline beat: heading title plus its raw section content. */
const linkedBeatPayloadSchema = Type.Object(
  {
    title: Type.String(),
    content: Type.String(),
  },
  { additionalProperties: false },
);

type LinkedBeatPayload = Static<typeof linkedBeatPayloadSchema>;

/**
 * One selectable beat candidate: the association key is the heading title, so
 * the catalog carries exactly what a link command may send back.
 */
const beatCandidateSchema = Type.Object(
  {
    title: Type.String(),
  },
  { additionalProperties: false },
);

type BeatCandidatePayload = Static<typeof beatCandidateSchema>;

/**
 * The outline document the candidate catalog was read from, together with the
 * project's outline count. More than one outline is disclosed rather than
 * silently resolved, so the UI can name the authority the beats come from
 * (DR-043).
 */
const outlineAuthoritySchema = Type.Object(
  {
    document_id: Type.String(),
    title: Type.String(),
    outline_count: Type.Integer({ minimum: 1 }),
  },
  { additionalProperties: false },
);

export type BeatOutlineAuthority = Static<typeof outlineAuthoritySchema>;

export const chapterBeatPayloadSchema = Type.Object(
  {
    beat: Type.Unsafe<LinkedBeatPayload | null>({
      ...linkedBeatPayloadSchema,
      nullable: true,
    }),
    candidates: Type.Array(beatCandidateSchema),
    outline: Type.Unsafe<BeatOutlineAuthority | null>({
      ...outlineAuthoritySchema,
      nullable: true,
    }),
  },
  { additionalProperties: false },
);

export type ChapterBeatPayload = Static<typeof chapterBeatPayloadSchema>;
export type BeatCandidate = BeatCandidatePayload;
