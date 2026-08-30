import { type Static, Type } from "@fastify/type-provider-typebox";

/**
 * Chapter beat payload SSOT (#440): the resolved association view emitted by
 * `BeatAssociationService` — the live outline beat, or `null` when the
 * chapter is unlinked or its stored reference vanished from the outline
 * (#313). The nullable object keeps the #405 `Type.Unsafe` + `nullable: true`
 * literal shape so the OpenAPI 3.0 representation is unchanged.
 */

/** One resolved outline beat: heading title plus its raw section content. */
export const linkedBeatPayloadSchema = Type.Object(
  {
    title: Type.String(),
    content: Type.String(),
  },
  { additionalProperties: false },
);

export type LinkedBeatPayload = Static<typeof linkedBeatPayloadSchema>;

export const chapterBeatPayloadSchema = Type.Object(
  {
    beat: Type.Unsafe<LinkedBeatPayload | null>({
      ...linkedBeatPayloadSchema,
      nullable: true,
    }),
  },
  { additionalProperties: false },
);

export type ChapterBeatPayload = Static<typeof chapterBeatPayloadSchema>;
