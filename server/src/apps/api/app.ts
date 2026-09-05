import { randomBytes, randomUUID } from "node:crypto";
import cookie from "@fastify/cookie";
import cors from "@fastify/cors";
import swagger from "@fastify/swagger";
import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import Fastify, { type FastifyInstance, type FastifyServerOptions } from "fastify";
import type { TextGenerationProviderFactory } from "../../contexts/ai/application/ports/text_generation.js";
import { providerCatalogRoutes } from "../../contexts/ai/interface/http/provider_routes.js";
import type { ExportArtifactGateway } from "../../contexts/studio/application/export_artifact_service.js";
import type { ExportOutcomeStore } from "../../contexts/studio/application/ports/export_store.js";
import type { ProjectArtifactCleaner } from "../../contexts/studio/application/ports/project_artifact_cleaner.js";
import { createStudioServices } from "../../contexts/studio/application/studio_services.js";
import { DrizzleStudioStore } from "../../contexts/studio/infrastructure/drizzle_studio_store.js";
import { FilesystemExportArtifactGateway } from "../../contexts/studio/infrastructure/export_artifact_files.js";
import { DatabaseExportPublicationCleanupJournal } from "../../contexts/studio/infrastructure/export_publication_cleanup_journal.js";
import { ExportStorePart } from "../../contexts/studio/infrastructure/export_store_part.js";
import { FsLegacyWorkspaceReader } from "../../contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { FilesystemProjectArtifactCleaner } from "../../contexts/studio/infrastructure/project_artifact_files.js";
import { studioRoutes } from "../../contexts/studio/interface/http/studio_routes.js";
import { AuthService } from "../../shared/application/auth_service.js";
import type { HealthProbe } from "../../shared/application/ports/health.js";
import { DEFAULT_CORS_ORIGINS } from "../../shared/domain/cors_contract.js";
import { assertStartupGuards } from "../../shared/infrastructure/config/server_config.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";
import type {
  StudioQueryLogger,
  StudioSqliteDatabase,
} from "../../shared/infrastructure/db/connection.js";
import { sqliteHealthProbe } from "../../shared/infrastructure/db/sqlite_health_probe.js";
import type { StudioDatabase } from "../../shared/infrastructure/db/startup.js";
import { clientIdentity } from "../../shared/infrastructure/rate_limit/client_identity.js";
import { TokenBucketRateLimiter } from "../../shared/infrastructure/rate_limit/token_bucket.js";
import { readProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";
import { authRoutes } from "../../shared/interface/http/auth_routes.js";
import { corsAllowList } from "../../shared/interface/http/cors_policy.js";
import { registerErrorEnvelope } from "../../shared/interface/http/error_envelope.js";
import { healthRoutes } from "../../shared/interface/http/health_routes.js";
import {
  defaultSpaDistDirectory,
  registerSpaServing,
} from "../../shared/interface/http/spa_serving.js";
import { type VersionInfo, versionRoutes } from "../../shared/interface/http/version_route.js";
import { closeAppAndRethrow } from "./app_lifecycle.js";
import {
  CORS_ALLOWED_HEADERS,
  CORS_ALLOWED_METHODS,
  CORS_EXPOSED_HEADERS,
} from "./cors_registration_policy.js";
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
import { openPersistence } from "./persistence.js";
import { loggerWithProductIdentity } from "./product_logger.js";
import { buildProviderRuntime, type ProviderApiKeys } from "./provider_runtime.js";
import { correlationIdFrom, REQUEST_ID_HEADER } from "./request_correlation.js";

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

const DEFAULT_AUTH_RATE_LIMIT_PER_MINUTE = 5;
/** Rate-limit buckets expire with the minute window that fills them. */
const AUTH_RATE_LIMIT_KEY_TTL_SECONDS = 60;

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
    const loreBudgetCharacters =
      options.lorebookBudgetCharacters ?? options.config?.llm.lorebookBudgetCharacters;
    const studioServices =
      persistence === undefined
        ? undefined
        : createStudioServices(
            new DrizzleStudioStore({
              database: persistence.db.db,
            }),
            {
              now: options.clock,
              providerFactory: provider.providerFactory,
              legacyWorkspaceReader: new FsLegacyWorkspaceReader(),
              reviewProvenance: {
                provider: provider.defaultProvider,
                model: provider.reviewModel,
              },
              artifactStore:
                options.exportStoreFactory?.(persistence.db.db) ??
                new ExportStorePart(persistence.db.db),
              artifactFiles:
                options.exportArtifactGateway ??
                new FilesystemExportArtifactGateway(persistence.dataDirectory, {
                  cleanupJournal: new DatabaseExportPublicationCleanupJournal(persistence.db.db),
                }),
              projectArtifactCleaner:
                options.projectArtifactCleaner ??
                new FilesystemProjectArtifactCleaner(persistence.dataDirectory),
              loreBudgetCharacters,
              operationCapacity,
            },
          );

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
      // Shared schemas land in components.schemas under their $id (e.g.
      // ErrorEnvelope) instead of positional def-N names, keeping the frozen
      // snapshot stable when shared-schema count changes.
      refResolver: {
        buildLocalReference: (json) => (typeof json.$id === "string" ? json.$id : `def-0`),
      },
    });
    const corsOrigins = options.corsOrigins ?? options.config?.corsOrigins ?? DEFAULT_CORS_ORIGINS;
    const allowList = corsAllowList(corsOrigins);
    await app.register(cors, {
      origin: allowList.allowAll ? true : allowList.origins,
      credentials: true,
      allowedHeaders: CORS_ALLOWED_HEADERS,
      methods: CORS_ALLOWED_METHODS,
      exposedHeaders: CORS_EXPOSED_HEADERS,
      maxAge: 600,
    });
    const perMinute =
      options.authRateLimitPerMinute ??
      options.config?.authRateLimitPerMinute ??
      DEFAULT_AUTH_RATE_LIMIT_PER_MINUTE;
    await app.register(authRoutes, {
      authService,
      limiter: new TokenBucketRateLimiter({
        ratePerSecond: perMinute / 60,
        capacity: perMinute,
        keyTtlSeconds: AUTH_RATE_LIMIT_KEY_TTL_SECONDS,
      }),
      productIdentity,
      environment,
      corsOrigins,
      resolveClientIdentity: (request) =>
        clientIdentity(
          request.socket?.remoteAddress,
          typeof request.headers["x-forwarded-for"] === "string"
            ? request.headers["x-forwarded-for"]
            : undefined,
          options.trustedProxies ?? options.config?.trustedProxies ?? [],
        ),
    });
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
