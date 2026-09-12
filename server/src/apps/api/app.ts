import { randomBytes, randomUUID } from "node:crypto";
import cookie from "@fastify/cookie";
import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import Fastify, { type FastifyInstance, type FastifyServerOptions } from "fastify";
import type { TextGenerationProviderFactory } from "../../contexts/ai/application/ports/text_generation.js";
import { providerCatalogRoutes } from "../../contexts/ai/interface/http/provider_routes.js";
import type { ExportArtifactGateway } from "../../contexts/studio/application/ports/artifact_gateway.js";
import type { ExportOutcomeStore } from "../../contexts/studio/application/ports/export_store.js";
import type { ProjectArtifactCleaner } from "../../contexts/studio/application/ports/project_artifact_cleaner.js";
import { studioRoutes } from "../../contexts/studio/interface/http/studio_routes.js";
import { AuthService } from "../../shared/application/auth_service.js";
import type { HealthProbe } from "../../shared/application/ports/health.js";
import { assertStartupGuards } from "../../shared/infrastructure/config/server_config.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";
import type {
  StudioQueryLogger,
  StudioSqliteDatabase,
} from "../../shared/infrastructure/db/connection.js";
import { sqliteHealthProbe } from "../../shared/infrastructure/db/sqlite_health_probe.js";
import type { StudioDatabase } from "../../shared/infrastructure/db/startup.js";
import { readProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";
import { registerErrorEnvelope } from "../../shared/interface/http/error_envelope.js";
import { healthRoutes } from "../../shared/interface/http/health_routes.js";
import {
  defaultSpaDistDirectory,
  registerSpaServing,
} from "../../shared/interface/http/spa_serving.js";
import { type VersionInfo, versionRoutes } from "../../shared/interface/http/version_route.js";
import { closeAppAndRethrow } from "./app_lifecycle.js";
import { registerAuthRoutes } from "./auth_registration.js";
import { registerCors, resolveCorsOrigins } from "./cors_registration_policy.js";
import {
  DEFAULT_HTTP_SERVER_POLICY,
  fastifyOptionsForHttpServerPolicy,
  type HttpServerPolicy,
  registerUndeclaredRequestBodyPolicy,
} from "./http_server_policy.js";
import { registerOpenApiDocument } from "./openapi_document_registration.js";
import {
  type OperationCapacityAppOptions,
  resolveOperationCapacity,
} from "./operation_capacity_config.js";
import { openPersistence } from "./persistence.js";
import { loggerWithProductIdentity } from "./product_logger.js";
import { buildProviderRuntime, type ProviderApiKeys } from "./provider_runtime.js";
import { correlationIdFrom, REQUEST_ID_HEADER } from "./request_correlation.js";
import { assembleStudioServices } from "./studio_services_assembly.js";

declare module "fastify" {
  interface FastifyInstance {
    /** The content-authority handle, present once an exact database path is configured. */
    studioDb?: StudioDatabase;
  }
}

export interface AppOptions extends OperationCapacityAppOptions {
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
  /** Browser origins allowed by the setup same-origin check (default: dev set). */
  corsOrigins?: string[] | undefined;
  /** Trusted proxy IPs/CIDRs/hosts for rate-limit client identity (default: none). */
  trustedProxies?: string[] | undefined;
  /** Auth endpoint rate limit in requests per minute (default: five). */
  authRateLimitPerMinute?: number | undefined;
  /** Injectable time source for the session lifecycle (tests). */
  clock?: (() => Date) | undefined;
  /**
   * Per-request AI provider factory override (tests inject capturing
   * providers). The default builds providers from `providerApiKeys`; HTTP
   * providers without a key fail explicitly — the mock is never a fallback.
   */
  textProviderFactory?: TextGenerationProviderFactory | undefined;
  /** Injectable export persistence factory for transaction/failure tests. */
  exportStoreFactory?: ((database: StudioSqliteDatabase) => ExportOutcomeStore) | undefined;
  /** Injectable artifact filesystem boundary for publication/failure tests. */
  exportArtifactGateway?: ExportArtifactGateway | undefined;
  /** Injectable post-commit project artifact cleanup boundary for tests. */
  projectArtifactCleaner?: ProjectArtifactCleaner | undefined;
  /** Credentials for the HTTP providers; absent keys leave them unconfigured. */
  providerApiKeys?: ProviderApiKeys | undefined;
  /**
   * Directory holding the built SPA (frontend/dist by default, resolved
   * relative to the server package). When present the Studio shell is served
   * at the site root with an index.html fallback; when absent the app boots
   * API-only and the root explains the missing build.
   */
  spaDistDirectory?: string | undefined;
  /**
   * Lorebook injection budget in characters (#445). Falls back to the
   * configured `LLM_LOREBOOK_BUDGET_CHARACTERS`, then the adjudicated default.
   */
  lorebookBudgetCharacters?: number | undefined;
  /** Injectable finite request-receipt thresholds for real-socket tests. */
  httpServerPolicy?: HttpServerPolicy | undefined;
}

const emptyHealthProbe: HealthProbe = async () => ({ components: [] });

/**
 * Composition root of the TS server: correlation-id request logging, the
 * unified error envelope, health probes, /version metadata, the OpenAPI
 * document seam consumed by the snapshot gate, and — when a database path is
 * configured — the persistence pipeline (backup → migrate → reconcile
 * export publications → recover job state) that must complete before the app
 * serves traffic.
 */
export async function buildApp(options: AppOptions = {}): Promise<FastifyInstance> {
  // Guards run before any side effect: a misconfigured production start must
  // not create directories, open databases, or listen.
  if (options.config !== undefined) {
    assertStartupGuards(options.config);
  }
  const operationCapacity = resolveOperationCapacity(options);

  const productIdentity = readProductIdentity();
  const app = Fastify({
    ...fastifyOptionsForHttpServerPolicy(options.httpServerPolicy ?? DEFAULT_HTTP_SERVER_POLICY),
    logger: loggerWithProductIdentity(options.logger, productIdentity),
    genReqId: (request) => correlationIdFrom(request.headers[REQUEST_ID_HEADER]) ?? randomUUID(),
  }).withTypeProvider<TypeBoxTypeProvider>();

  try {
    app.addHook("onRequest", async (request, reply) => {
      reply.header("x-request-id", request.id);
    });
    registerUndeclaredRequestBodyPolicy(app);

    const databasePath = options.databasePath ?? options.config?.databasePath;
    // The content-authority database exists exactly when a database path is
    // configured, so the handles travel together and downstream guards need a
    // single check (audit hard-10: the former `studioDb === undefined ||
    // dataDirectory === undefined` clause was unreachable).
    const persistence =
      databasePath === undefined
        ? undefined
        : await openPersistence(app, databasePath, options.databaseQueryLogger);
    if (persistence !== undefined) {
      app.decorate("studioDb", persistence.db);
    }
    const dataDirectory = persistence?.dataDirectory;

    const environment =
      options.environment ?? options.config?.environment ?? process.env.NODE_ENV ?? "development";
    const authService =
      persistence === undefined
        ? undefined
        : new AuthService({
            store: new DrizzleAuthStore(persistence.db.db),
            sessionSecret:
              options.sessionSecret ??
              options.config?.sessionSecret ??
              randomBytes(32).toString("base64url"),
            now: options.clock,
          });
    const provider = buildProviderRuntime(options.config, options);
    const studioServices =
      persistence === undefined
        ? undefined
        : assembleStudioServices(persistence, options.config, provider, operationCapacity, options);

    const versionInfo: VersionInfo = {
      version: productIdentity.version,
      name: productIdentity.name,
      runtime: { name: "node", version: process.versions.node },
      environment,
      build: options.buildSha ?? process.env.BUILD_SHA ?? "unknown",
    };

    // The envelope must be installed before route plugins: Fastify child
    // contexts snapshot their parent's error handler at registration time.
    registerErrorEnvelope(app);

    await app.register(cookie);
    await registerOpenApiDocument(app, productIdentity, versionInfo);
    const corsOrigins = resolveCorsOrigins(options);
    await registerCors(app, corsOrigins);
    await registerAuthRoutes(
      app,
      { authService, productIdentity, environment, corsOrigins },
      options,
    );
    await app.register(healthRoutes, {
      healthProbe:
        options.healthProbe ??
        (persistence === undefined ? emptyHealthProbe : sqliteHealthProbe(persistence.db.raw)),
    });
    await app.register(versionRoutes, { info: versionInfo });
    await app.register(providerCatalogRoutes, {
      authService,
      defaultProvider: provider.defaultProvider,
      settings: provider.providerModelSettings,
      credentials: provider.providerApiKeys,
    });
    await app.register(studioRoutes, {
      authService,
      services: studioServices,
      dataDirectory,
    });

    app.get("/openapi.json", { schema: { hide: true } }, async () => app.swagger());

    // The SPA surface registers last: its wildcard only fires when no API,
    // health, or version route matched, so the JSON API stays distinct.
    await registerSpaServing(app, {
      distDirectory: options.spaDistDirectory ?? defaultSpaDistDirectory(),
      productName: versionInfo.name,
      version: versionInfo.version,
    });

    return app;
  } catch (error) {
    return closeAppAndRethrow(app, error, "Application initialization and cleanup both failed.");
  }
}
