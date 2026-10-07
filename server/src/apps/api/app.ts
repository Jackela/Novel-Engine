import { randomUUID } from "node:crypto";
import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import Fastify, { type FastifyInstance, type FastifyServerOptions } from "fastify";
import type { TextGenerationProviderFactory } from "../../contexts/ai/application/ports/text_generation.js";
import type { HealthProbe } from "../../shared/application/ports/health.js";
import { assertStartupGuards } from "../../shared/infrastructure/config/server_config.js";
import type { StudioQueryLogger } from "../../shared/infrastructure/db/connection.js";
import type { StudioDatabase } from "../../shared/infrastructure/db/startup.js";
import { readProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";
import { registerErrorEnvelope } from "../../shared/interface/http/error_envelope.js";
import {
  defaultSpaDistDirectory,
  registerSpaServing,
} from "../../shared/interface/http/spa_serving.js";
import { registerApiPlugins } from "./api_plugins_registration.js";
import { closeAppAndRethrow } from "./app_lifecycle.js";
import { type AuthRegistrationOptions, resolveTrustedProxies } from "./auth_registration.js";
import type { CorsOriginsAppOptions } from "./cors_registration_policy.js";
import {
  DEFAULT_HTTP_SERVER_POLICY,
  fastifyOptionsForHttpServerPolicy,
  type HttpServerPolicy,
  registerUndeclaredRequestBodyPolicy,
} from "./http_server_policy.js";
import {
  type OperationCapacityAppOptions,
  resolveOperationCapacity,
} from "./operation_capacity_config.js";
import { loggerWithProductIdentity } from "./product_logger.js";
import type { ProviderApiKeys } from "./provider_runtime.js";
import { correlationIdFrom, REQUEST_ID_HEADER } from "./request_correlation.js";
import { createRuntimeDependencies } from "./runtime_dependencies.js";
import type { StudioServicesAssemblyOptions } from "./studio_services_assembly.js";

declare module "fastify" {
  interface FastifyInstance {
    /** The content-authority handle, present once an exact database path is configured. */
    studioDb?: StudioDatabase;
  }
}

export interface AppOptions
  extends AuthRegistrationOptions,
    CorsOriginsAppOptions,
    OperationCapacityAppOptions,
    StudioServicesAssemblyOptions {
  logger?: FastifyServerOptions["logger"];
  healthProbe?: HealthProbe | undefined;
  environment?: string | undefined;
  buildSha?: string | undefined;
  /**
   * Exact SQLite database path. When set, startup runs the
   * persistence pipeline (backup → migrations → export reconciliation →
   * job-state recovery) before serving; when absent the app stays
   * database-free (walking skeleton).
   */
  databasePath?: string | undefined;
  /** Optional SQL statement observer for integration evidence and diagnostics. */
  databaseQueryLogger?: StudioQueryLogger | undefined;
  /**
   * HMAC key for session token digests. Unset outside the production guards:
   * a fresh random value per start deliberately invalidates all sessions at
   * each restart.
   */
  sessionSecret?: string | undefined;
  /**
   * Per-request AI provider factory override (tests inject capturing
   * providers). The default builds providers from `providerApiKeys`; HTTP
   * providers without a key fail explicitly — the mock is never a fallback.
   */
  textProviderFactory?: TextGenerationProviderFactory | undefined;
  /** Credentials for the HTTP providers; absent keys leave them unconfigured. */
  providerApiKeys?: ProviderApiKeys | undefined;
  /**
   * Directory holding the built SPA (frontend/dist by default, resolved
   * relative to the server package). When present the Studio shell is served
   * at the site root with an index.html fallback; when absent the app boots
   * API-only and the root explains the missing build.
   */
  spaDistDirectory?: string | undefined;
  /** Injectable finite request-receipt thresholds for real-socket tests. */
  httpServerPolicy?: HttpServerPolicy | undefined;
}

/**
 * Composition root of the TS server: correlation-id request logging, the
 * unified error envelope, health probes, /version metadata, the OpenAPI
 * document seam consumed by the snapshot gate, and — when a database path is
 * configured — the persistence pipeline (backup → migrate → reconcile
 * export publications → recover job state) that must complete before the app
 * serves traffic.
 *
 * This function owns only the phases and their order: the runtime handles
 * assemble in createRuntimeDependencies, the API surface registers in
 * registerApiPlugins, and the SPA wildcard mounts last. A failure in any
 * phase closes the partially built app before the error propagates.
 */
export async function buildApp(options: AppOptions = {}): Promise<FastifyInstance> {
  // Guards run before any side effect: a misconfigured production start must
  // not create directories, open databases, or listen.
  if (options.config !== undefined) {
    assertStartupGuards(options.config);
  }
  const operationCapacity = resolveOperationCapacity(options);

  const productIdentity = readProductIdentity();
  // One trusted-proxy resolution for the whole app: the HTTP server's
  // trustProxy option and the rate limiter's client identity must agree.
  const trustedProxies = resolveTrustedProxies(options);
  const app = Fastify({
    ...fastifyOptionsForHttpServerPolicy(
      options.httpServerPolicy ?? DEFAULT_HTTP_SERVER_POLICY,
      trustedProxies,
    ),
    logger: loggerWithProductIdentity(options.logger, productIdentity, options.config?.logLevel),
    genReqId: (request) => correlationIdFrom(request.headers[REQUEST_ID_HEADER]) ?? randomUUID(),
  }).withTypeProvider<TypeBoxTypeProvider>();

  try {
    app.addHook("onRequest", async (request, reply) => {
      reply.header("x-request-id", request.id);
    });
    registerUndeclaredRequestBodyPolicy(app);

    const dependencies = await createRuntimeDependencies(
      app,
      options,
      productIdentity,
      operationCapacity,
    );

    // The envelope must be installed before route plugins: Fastify child
    // contexts snapshot their parent's error handler at registration time.
    registerErrorEnvelope(app);
    await registerApiPlugins(app, dependencies, options);

    // The SPA surface registers last: its wildcard only fires when no API,
    // health, or version route matched, so the JSON API stays distinct.
    await registerSpaServing(app, {
      distDirectory: options.spaDistDirectory ?? defaultSpaDistDirectory(),
      productName: dependencies.versionInfo.name,
      version: dependencies.versionInfo.version,
    });

    return app;
  } catch (error) {
    return closeAppAndRethrow(app, error, "Application initialization and cleanup both failed.");
  }
}
