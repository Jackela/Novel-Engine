/**
 * Opaque JSON Schema shape for response declarations. Annotating response
 * schemas with this type keeps them out of the TypeBox type provider's static
 * inference: serializer statics stay `unknown` (responses are validated and
 * serialized at runtime by fast-json-stringify, exactly as before), while
 * request schemas in `studio_request_schemas.ts` keep full compile-time
 * inference.
 */
export type JsonResponseSchema = { readonly [key: string]: unknown };
