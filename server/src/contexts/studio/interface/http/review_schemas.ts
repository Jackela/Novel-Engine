import { Type } from "@fastify/type-provider-typebox";
import { reviewPayloadSchema } from "../../application/payload_schemas/review.js";

/**
 * The review assessment response (#440) is the TypeBox payload SSOT from
 * `application/payload_schemas/review.ts`, re-exported under its HTTP-surface
 * name; the LIST envelope wraps those items.
 */

export { reviewPayloadSchema as reviewResponseSchema } from "../../application/payload_schemas/review.js";

export const reviewListResponseSchema = Type.Object(
  { reviews: Type.Array(reviewPayloadSchema) },
  { additionalProperties: false },
);

/**
 * A review has no client-controlled input. Provider and model provenance are
 * selected inside the server's service graph rather than accepted over HTTP.
 */
export const reviewCreateSchema = Type.Object({}, { additionalProperties: false });
