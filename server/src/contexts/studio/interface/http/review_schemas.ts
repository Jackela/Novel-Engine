import { Type } from "@fastify/type-provider-typebox";
import { reviewSummaryPayloadSchema } from "../../application/payload_schemas/review.js";

/**
 * The review assessment detail response (#440) is the TypeBox payload SSOT
 * from `application/payload_schemas/review.ts`, re-exported under its
 * HTTP-surface name; the LIST envelope wraps bounded summaries whose ordered
 * issues live only on the detail read (#459).
 */

export { reviewPayloadSchema as reviewResponseSchema } from "../../application/payload_schemas/review.js";

export const reviewListQuerySchema = Type.Object(
  {
    limit: Type.Optional(Type.Integer({ default: 50, minimum: 1, maximum: 100 })),
    cursor: Type.Optional(
      Type.String({
        minLength: 1,
        maxLength: 1024,
        pattern: "^[A-Za-z0-9_-]+$",
      }),
    ),
  },
  { additionalProperties: false },
);

export const reviewListResponseSchema = Type.Object(
  {
    reviews: Type.Array(reviewSummaryPayloadSchema),
    next_cursor: Type.Union([Type.String(), Type.Null()]),
  },
  { additionalProperties: false },
);

/**
 * A review has no client-controlled input. Provider and model provenance are
 * selected inside the server's service graph rather than accepted over HTTP.
 */
export const reviewCreateSchema = Type.Object({}, { additionalProperties: false });
