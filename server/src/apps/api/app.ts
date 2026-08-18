import { randomUUID } from "node:crypto";
import swagger from "@fastify/swagger";
import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import Fastify, { type FastifyInstance, type FastifyLoggerOptions } from "fastify";

import type { HealthProbe } from "../../shared/application/ports/health.js";
import { readWorkspaceVersion } from "../../shared/infrastructure/workspace_manifest.js";
import { registerErrorEnvelope } from "../../shared/interface/http/error_envelope.js";
import { healthRoutes } from "../../shared/interface/http/health_routes.js";
import { type VersionInfo, versionRoutes } from "../../shared/interface/http/version_route.js";

export interface AppOptions {
  logger?: boolean | FastifyLoggerOptions | undefined;
  healthProbe?: HealthProbe | undefined;
  environment?: string | undefined;
  buildSha?: string | undefined;
}

const emptyHealthProbe: HealthProbe = async () => ({ components: [] });

const REQUEST_ID_HEADER = "x-request-id";
const SAFE_REQUEST_ID = /^[A-Za-z0-9._-]{1,128}$/;

/**
 * Inbound correlation ids are honored only when short and plain: a hostile
 * header value must not flow into logs, responses, or error ids.
 */
function correlationIdFrom(value: string | string[] | undefined): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return SAFE_REQUEST_ID.test(trimmed) ? trimmed : undefined;
}

/**
 * Composition root of the TS server: correlation-id request logging, the
 * unified error envelope, health probes, /version metadata, and the OpenAPI
 * document seam consumed by the snapshot gate.
 */
export async function buildApp(options: AppOptions = {}): Promise<FastifyInstance> {
  const app = Fastify({
    logger: options.logger ?? true,
    genReqId: (request) => correlationIdFrom(request.headers[REQUEST_ID_HEADER]) ?? randomUUID(),
  }).withTypeProvider<TypeBoxTypeProvider>();

  app.addHook("onRequest", async (request, reply) => {
    reply.header("x-request-id", request.id);
  });

  const versionInfo: VersionInfo = {
    version: readWorkspaceVersion(),
    name: "Novel Engine",
    runtime: { name: "node", version: process.versions.node },
    environment: options.environment ?? process.env.NODE_ENV ?? "development",
    build: options.buildSha ?? process.env.BUILD_SHA ?? "unknown",
  };

  await app.register(swagger, {
    openapi: {
      info: {
        title: "Novel Engine API",
        version: versionInfo.version,
        description: "Self-hosted writing studio API (TypeScript rewrite).",
      },
    },
  });
  await app.register(healthRoutes, { healthProbe: options.healthProbe ?? emptyHealthProbe });
  await app.register(versionRoutes, { info: versionInfo });

  app.get("/openapi.json", { schema: { hide: true } }, async () => app.swagger());

  registerErrorEnvelope(app);
  return app;
}
