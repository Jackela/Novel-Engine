import { randomBytes, randomUUID } from "node:crypto";
import cookie from "@fastify/cookie";
import cors from "@fastify/cors";
import swagger from "@fastify/swagger";
import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import Fastify, { type FastifyInstance, type FastifyLoggerOptions } from "fastify";
import { resolveReviewModel } from "../../contexts/ai/application/model_resolution.js";
import type { TextGenerationProviderFactory } from "../../contexts/ai/application/ports/text_generation.js";
import { textProviderFactory } from "../../contexts/ai/infrastructure/providers/text_provider_factory.js";
import { providerCatalogRoutes } from "../../contexts/ai/interface/http/provider_routes.js";
import { createStudioServices } from "../../contexts/studio/application/studio_services.js";
import { DrizzleStudioStore } from "../../contexts/studio/infrastructure/drizzle_studio_store.js";
import { FilesystemExportArtifactGateway } from "../../contexts/studio/infrastructure/export_artifact_files.js";
import { ExportStorePart } from "../../contexts/studio/infrastructure/export_store_part.js";
import { documentRoutes } from "../../contexts/studio/interface/http/document_routes.js";
import { projectRoutes } from "../../contexts/studio/interface/http/project_routes.js";
import { proposalRoutes } from "../../contexts/studio/interface/http/proposal_routes.js";
import { reviewRoutes } from "../../contexts/studio/interface/http/review_routes.js";
import { AuthService } from "../../shared/application/auth_service.js";
import type { HealthProbe } from "../../shared/application/ports/health.js";
import { DEFAULT_CORS_ORIGINS } from "../../shared/domain/cors_contract.js";
import {
  assertStartupGuards,
  type ServerConfig,
} from "../../shared/infrastructure/config/server_config.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";
import { openStudioDatabase, type StudioDatabase } from "../../shared/infrastructure/db/startup.js";
import { clientIdentity } from "../../shared/infrastructure/rate_limit/client_identity.js";
import { TokenBucketRateLimiter } from "../../shared/infrastructure/rate_limit/token_bucket.js";
import { readWorkspaceVersion } from "../../shared/infrastructure/workspace_manifest.js";
import { authRoutes } from "../../shared/interface/http/auth_routes.js";
import { corsAllowList } from "../../shared/interface/http/cors_policy.js";
import { registerErrorEnvelope } from "../../shared/interface/http/error_envelope.js";
import { healthRoutes } from "../../shared/interface/http/health_routes.js";
import { type VersionInfo, versionRoutes } from "../../shared/interface/http/version_route.js";

declare module "fastify" {
  interface FastifyInstance {
    /** The content-authority handle, present once a data directory is configured. */
    studioDb?: StudioDatabase;
  }
}

export interface AppOptions {
  logger?: boolean | FastifyLoggerOptions | undefined;
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
  /** Credentials for the HTTP providers; absent keys leave them unconfigured. */
  providerApiKeys?: { dashscope?: string; openaiCompatible?: string } | undefined;
  /**
   * Resolved operational configuration (loadServerConfig). When present the
   * production guards fail fast here and unset options fall back to it.
   */
  config?: ServerConfig | undefined;
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

  const app = Fastify({
    logger: options.logger ?? true,
    genReqId: (request) => correlationIdFrom(request.headers[REQUEST_ID_HEADER]) ?? randomUUID(),
  }).withTypeProvider<TypeBoxTypeProvider>();

  app.addHook("onRequest", async (request, reply) => {
    reply.header("x-request-id", request.id);
  });

  const dataDirectory = options.dataDirectory ?? options.config?.dataDirectory;
  let studioDb: StudioDatabase | undefined;
  if (dataDirectory !== undefined) {
    try {
      studioDb = await openStudioDatabase(dataDirectory);
    } catch (error) {
      await app.close();
      throw error;
    }
    app.decorate("studioDb", studioDb);
    app.addHook("onClose", async () => {
      studioDb?.close();
    });
  }

  const environment =
    options.environment ?? options.config?.environment ?? process.env.NODE_ENV ?? "development";
  const authService =
    studioDb === undefined
      ? undefined
      : new AuthService({
          store: new DrizzleAuthStore(studioDb.db),
          sessionSecret:
            options.sessionSecret ??
            options.config?.sessionSecret ??
            randomBytes(32).toString("base64url"),
          now: options.clock,
        });
  const llm = options.config?.llm;
  const providerApiKeys = options.providerApiKeys ?? {
    dashscope: llm?.dashscopeApiKey,
    openaiCompatible: llm?.openaiCompatibleApiKey,
  };
  const providerModelSettings = {
    genericModel: llm?.genericModel,
    dashscopeModel: llm?.dashscopeModel,
    dashscopeReviewModel: llm?.dashscopeReviewModel,
    openaiCompatibleModel: llm?.openaiCompatibleModel,
  };
  const defaultProvider = llm?.defaultProvider ?? "mock";
  const providerFactory: TextGenerationProviderFactory =
    options.textProviderFactory ??
    textProviderFactory(providerApiKeys, {
      modelSettings: providerModelSettings,
      ...(llm === undefined
        ? {}
        : {
            adapterOptions: {
              dashscope: {
                apiBase: llm.dashscopeApiBase,
                transportMode: llm.dashscopeTransportMode,
                timeoutSeconds: llm.timeoutSeconds,
                retry: { maxAttempts: llm.retryAttempts, delayMs: llm.retryDelayMs },
              },
              openaiCompatible: {
                apiBase: llm.openaiCompatibleApiBase,
                timeoutSeconds: llm.timeoutSeconds,
                retry: { maxAttempts: llm.retryAttempts, delayMs: llm.retryDelayMs },
              },
            },
          }),
    });
  const studioServices =
    studioDb === undefined || dataDirectory === undefined
      ? undefined
      : createStudioServices(new DrizzleStudioStore({ database: studioDb.db, dataDirectory }), {
          now: options.clock,
          providerFactory,
          reviewProvenance: {
            provider: defaultProvider,
            model: resolveReviewModel(defaultProvider, providerModelSettings),
          },
          artifactStore: new ExportStorePart(studioDb.db),
          artifactFiles: new FilesystemExportArtifactGateway(dataDirectory),
        });

  const versionInfo: VersionInfo = {
    version: readWorkspaceVersion(),
    name: "Novel Engine",
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
        title: "Novel Engine API",
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
      keyTtlSeconds: 60,
    }),
    version: versionInfo.version,
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
    defaultProvider,
    settings: providerModelSettings,
    credentials: providerApiKeys,
  });
  await app.register(projectRoutes, { authService, services: studioServices });
  await app.register(documentRoutes, { authService, services: studioServices });
  await app.register(proposalRoutes, { authService, services: studioServices });
  await app.register(reviewRoutes, { authService, services: studioServices });

  app.get("/openapi.json", { schema: { hide: true } }, async () => app.swagger());

  return app;
}
