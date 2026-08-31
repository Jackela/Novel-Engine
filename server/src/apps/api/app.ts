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
import { createStudioServices } from "../../contexts/studio/application/studio_services.js";
import { DrizzleStudioStore } from "../../contexts/studio/infrastructure/drizzle_studio_store.js";
import { FilesystemExportArtifactGateway } from "../../contexts/studio/infrastructure/export_artifact_files.js";
import { ExportStorePart } from "../../contexts/studio/infrastructure/export_store_part.js";
import { FsLegacyWorkspaceReader } from "../../contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { studioRoutes } from "../../contexts/studio/interface/http/studio_routes.js";
import { AuthService } from "../../shared/application/auth_service.js";
import type { HealthProbe } from "../../shared/application/ports/health.js";
import { DEFAULT_CORS_ORIGINS } from "../../shared/domain/cors_contract.js";
import {
  assertStartupGuards,
  type ServerConfig,
} from "../../shared/infrastructure/config/server_config.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";
import type { StudioSqliteDatabase } from "../../shared/infrastructure/db/connection.js";
import type { StudioDatabase } from "../../shared/infrastructure/db/startup.js";
import { clientIdentity } from "../../shared/infrastructure/rate_limit/client_identity.js";
import { TokenBucketRateLimiter } from "../../shared/infrastructure/rate_limit/token_bucket.js";
import {
  type ProductIdentity,
  readProductIdentity,
} from "../../shared/infrastructure/workspace_manifest.js";
import { authRoutes } from "../../shared/interface/http/auth_routes.js";
import { corsAllowList } from "../../shared/interface/http/cors_policy.js";
import { registerErrorEnvelope } from "../../shared/interface/http/error_envelope.js";
import { healthRoutes } from "../../shared/interface/http/health_routes.js";
import {
  defaultSpaDistDirectory,
  registerSpaServing,
} from "../../shared/interface/http/spa_serving.js";
import { type VersionInfo, versionRoutes } from "../../shared/interface/http/version_route.js";
import { openPersistence } from "./persistence.js";
import { buildProviderRuntime, type ProviderApiKeys } from "./provider_runtime.js";
import { correlationIdFrom, REQUEST_ID_HEADER } from "./request_correlation.js";

declare module "fastify" {
  interface FastifyInstance {
    /** The content-authority handle, present once a data directory is configured. */
    studioDb?: StudioDatabase;
  }
}

export interface AppOptions {
  logger?: FastifyServerOptions["logger"];
  healthProbe?: HealthProbe | undefined;
  environment?: string | undefined;
  buildSha?: string | undefined;
  /**
   * Directory holding novel-engine.sqlite3. When set, startup runs the
   * persistence pipeline (backup → migrations → restart recovery) before
   * serving; when absent the app stays database-free (walking skeleton).
   */
  dataDirectory?: string | undefined;
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
  /** Credentials for the HTTP providers; absent keys leave them unconfigured. */
  providerApiKeys?: ProviderApiKeys | undefined;
  /**
   * Resolved operational configuration (loadServerConfig). When present the
   * production guards fail fast here and unset options fall back to it.
   */
  config?: ServerConfig | undefined;
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
}

const CORS_ALLOWED_HEADERS = [
  "content-type",
  "authorization",
  "x-api-key",
  "x-request-id",
  "accept",
  "origin",
  "x-requested-with",
  "x-csrf-token",
];
const CORS_ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"];

const DEFAULT_AUTH_RATE_LIMIT_PER_MINUTE = 5;
/** Rate-limit buckets expire with the minute window that fills them. */
const AUTH_RATE_LIMIT_KEY_TTL_SECONDS = 60;

const emptyHealthProbe: HealthProbe = async () => ({ components: [] });

function loggerWithProductIdentity(
  logger: AppOptions["logger"],
  identity: ProductIdentity,
): false | Exclude<FastifyServerOptions["logger"], boolean | undefined> {
  if (logger === false) {
    return false;
  }
  const configured: Exclude<FastifyServerOptions["logger"], boolean | undefined> =
    logger === true || logger === undefined ? {} : logger;
  return {
    ...configured,
    base: {
      ...(configured.base ?? {}),
      product_name: identity.name,
      product_version: identity.version,
    },
  };
}

/**
 * Composition root of the TS server: correlation-id request logging, the
 * unified error envelope, health probes, /version metadata, the OpenAPI
 * document seam consumed by the snapshot gate, and — when a data directory
 * is configured — the persistence pipeline (backup → migrate → recover)
 * that must complete before the app serves traffic.
 */
export async function buildApp(options: AppOptions = {}): Promise<FastifyInstance> {
  // Guards run before any side effect: a misconfigured production start must
  // not create directories, open databases, or listen.
  if (options.config !== undefined) {
    assertStartupGuards(options.config);
  }

  const productIdentity = readProductIdentity();
  const app = Fastify({
    logger: loggerWithProductIdentity(options.logger, productIdentity),
    genReqId: (request) => correlationIdFrom(request.headers[REQUEST_ID_HEADER]) ?? randomUUID(),
  }).withTypeProvider<TypeBoxTypeProvider>();

  app.addHook("onRequest", async (request, reply) => {
    reply.header("x-request-id", request.id);
  });

  const dataDirectory = options.dataDirectory ?? options.config?.dataDirectory;
  // The content-authority database exists exactly when a data directory is
  // configured, so the handles travel together and downstream guards need a
  // single check (audit hard-10: the former `studioDb === undefined ||
  // dataDirectory === undefined` clause was unreachable).
  const persistence =
    dataDirectory === undefined ? undefined : await openPersistence(app, dataDirectory);
  if (persistence !== undefined) {
    app.decorate("studioDb", persistence.db);
    app.addHook("onClose", async () => {
      persistence.db.close();
    });
  }

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
            dataDirectory: persistence.dataDirectory,
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
              new FilesystemExportArtifactGateway(persistence.dataDirectory),
            loreBudgetCharacters,
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
    exposedHeaders: ["x-request-id", "x-total-count"],
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
  await app.register(healthRoutes, { healthProbe: options.healthProbe ?? emptyHealthProbe });
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
}
