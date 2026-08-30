/**
 * Opaque JSON Schema shape for hand-written response declarations. Annotating
 * response schemas with this type keeps them out of the TypeBox type
 * provider's static inference: serializer statics stay `unknown` (responses
 * are validated and serialized at runtime by fast-json-stringify, exactly as
 * before), while request schemas in `studio_request_schemas.ts` keep full
 * compile-time inference.
 *
 * Core resource payload schemas are NOT declared here anymore: they are the
 * TypeBox SSOT in `application/payload_schemas/` (#433), re-exported by the
 * `*_schemas.ts` modules. This annotation now covers only the hand-written
 * error/aggregate/SSE shapes (conflict envelopes, usage, export artifacts).
 */
export type JsonResponseSchema = { readonly [key: string]: unknown };
