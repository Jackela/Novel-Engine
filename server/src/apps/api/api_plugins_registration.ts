import cookie from "@fastify/cookie";
import type { FastifyInstance } from "fastify";
import { providerCatalogRoutes } from "../../contexts/ai/interface/http/provider_routes.js";
import { studioRoutes } from "../../contexts/studio/interface/http/studio_routes.js";
import type { HealthProbe } from "../../shared/application/ports/health.js";
import { sqliteHealthProbe } from "../../shared/infrastructure/db/sqlite_health_probe.js";
import { principalGuard } from "../../shared/interface/http/auth_guard.js";
import { healthRoutes } from "../../shared/interface/http/health_routes.js";
import { metricsRoutes } from "../../shared/interface/http/metrics_routes.js";
import { versionRoutes } from "../../shared/interface/http/version_route.js";
import { type AuthRegistrationOptions, registerAuthRoutes } from "./auth_registration.js";
import {
  type CorsOriginsAppOptions,
  registerCors,
  resolveCorsOrigins,
} from "./cors_registration_policy.js";
import { buildMetricsProbe } from "./metrics_probe.js";
import { registerOpenApiDocument } from "./openapi_document_registration.js";
import type { RuntimeDependencies } from "./runtime_dependencies.js";

/** Probe for a database-free app: no components to report, never a failure. */
const emptyHealthProbe: HealthProbe = async () => ({ components: [] });

/**
 * Registration-time options the API plugins read from AppOptions. The app
 * root passes its whole option object; only these fields are consumed here,
 * so the surface stays visible and a signature change cannot silently reach
 * into unrelated app options.
 */
export interface ApiPluginOptions extends AuthRegistrationOptions, CorsOriginsAppOptions {
  /** Health probe override for tests; defaults to SQLite, or empty without a database. */
  healthProbe?: HealthProbe | undefined;
}

/**
 * Register the API surface in the order its plugins depend on each other: the
 * cookie parser, the OpenAPI document every later route contributes schemas
 * to, CORS, then auth, health, metrics, /version, the provider catalog, and
 * the Studio routes. The hidden `/openapi.json` contract route is mounted
 * here too, after the routes it describes, because its production guard
 * (DR-035) reads the same resolved environment and auth service.
 */
export async function registerApiPlugins(
  app: FastifyInstance,
  dependencies: RuntimeDependencies,
  options: ApiPluginOptions,
): Promise<void> {
  const {
    authService,
    dataDirectory,
    environment,
    persistence,
    productIdentity,
    provider,
    setupTokenGuard,
    studioServices,
    versionInfo,
  } = dependencies;

  await app.register(cookie);
  await registerOpenApiDocument(app, productIdentity, versionInfo);
  const corsOrigins = resolveCorsOrigins(options);
  await registerCors(app, corsOrigins);
  await registerAuthRoutes(
    app,
    { authService, productIdentity, environment, corsOrigins, setupTokenGuard },
    options,
  );
  await app.register(healthRoutes, {
    healthProbe:
      options.healthProbe ??
      (persistence === undefined ? emptyHealthProbe : sqliteHealthProbe(persistence.db.raw)),
  });
  // DR-041: the internal scrape surface. It is registered before the SPA
  // wildcard, kept out of the OpenAPI document, and gated to the loopback
  // peer or an authenticated owner session.
  await app.register(metricsRoutes, {
    probe: buildMetricsProbe(persistence?.db.raw),
    authService,
    productIdentity,
  });
  await app.register(versionRoutes, {
    info: versionInfo,
    production: environment === "production",
  });
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

  // The full contract is owner-only in production (DR-035); development and
  // test keep the route open so the snapshot gate and local tooling can read
  // it. The owner guard answers 401 to anonymous callers and 503 when no
  // persistence layer exists to authorize against (fail-closed).
  const openApiDocument = async () => app.swagger();
  if (environment === "production") {
    app.get(
      "/openapi.json",
      { schema: { hide: true }, preHandler: principalGuard(authService) },
      openApiDocument,
    );
  } else {
    app.get("/openapi.json", { schema: { hide: true } }, openApiDocument);
  }
}
