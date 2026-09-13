import swagger from "@fastify/swagger";
import type { FastifyInstance } from "fastify";

import type { ProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";
import type { VersionInfo } from "../../shared/interface/http/version_route.js";

/**
 * Register the OpenAPI document consumed by the snapshot gate. Shared schemas
 * land in components.schemas under their $id (e.g. ErrorEnvelope) instead of
 * positional def-N names, keeping the frozen snapshot stable when
 * shared-schema count changes.
 */
export async function registerOpenApiDocument(
  app: FastifyInstance,
  productIdentity: ProductIdentity,
  versionInfo: VersionInfo,
): Promise<void> {
  await app.register(swagger, {
    openapi: {
      info: {
        title: `${productIdentity.name} API`,
        version: versionInfo.version,
        description: "Self-hosted writing studio API (TypeScript rewrite).",
      },
      components: {
        securitySchemes: {
          cookieAuth: {
            type: "apiKey",
            in: "cookie",
            name: "novel_engine_session",
          },
        },
      },
    },
    refResolver: {
      buildLocalReference: (json) => (typeof json.$id === "string" ? json.$id : `def-0`),
    },
  });
}
