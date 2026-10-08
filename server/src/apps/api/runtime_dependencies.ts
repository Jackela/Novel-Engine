import { randomBytes } from "node:crypto";
import type { FastifyInstance } from "fastify";
import type { TextGenerationProviderFactory } from "../../contexts/ai/application/ports/text_generation.js";
import type { OperationCapacityPolicy } from "../../contexts/studio/application/operation_in_flight.js";
import type { StudioServices } from "../../contexts/studio/application/studio_services.js";
import { AuthService } from "../../shared/application/auth_service.js";
import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";
import { resolveSessionSecret } from "../../shared/infrastructure/config/session_secret.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";
import type { StudioQueryLogger } from "../../shared/infrastructure/db/connection.js";
import { armFirstBootSetupToken } from "../../shared/infrastructure/db/setup_token.js";
import type { ProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";
import type { SetupTokenGuard } from "../../shared/interface/http/auth_routes.js";
import type { VersionInfo } from "../../shared/interface/http/version_route.js";
import { openPersistence, type PersistenceHandles } from "./persistence.js";
import {
  buildProviderRuntime,
  type ProviderApiKeys,
  type ProviderRuntime,
} from "./provider_runtime.js";
import {
  assembleStudioServices,
  type StudioServicesAssemblyOptions,
} from "./studio_services_assembly.js";

/**
 * Composition-root inputs the runtime dependency assembly reads from
 * AppOptions. Every field is optional: an app booted without a config and
 * without a database path is the deliberate walking skeleton.
 */
export interface RuntimeDependencyInputs extends StudioServicesAssemblyOptions {
  /** Resolved operational configuration from loadServerConfig. */
  readonly config?: ServerConfig | undefined;
  /** Exact SQLite database path; absent keeps the app database-free. */
  databasePath?: string | undefined;
  /** Optional SQL statement observer for integration evidence and diagnostics. */
  databaseQueryLogger?: StudioQueryLogger | undefined;
  /** Runtime environment name; falls back to config, then NODE_ENV. */
  environment?: string | undefined;
  /** Explicit session secret; unset generates one per start (see resolveSessionSecret). */
  sessionSecret?: string | undefined;
  /** Build SHA reported by /version when the environment carries none. */
  buildSha?: string | undefined;
  /** Per-request AI provider factory override (tests inject capturing providers). */
  textProviderFactory?: TextGenerationProviderFactory | undefined;
  /** Credentials for the HTTP providers; absent keys leave them unconfigured. */
  providerApiKeys?: ProviderApiKeys | undefined;
}

/**
 * Runtime handles one app instance owns after assembly. The database-backed
 * fields are absent together — they exist exactly when a database path is
 * configured — so every consumer needs a single undefined check, and the
 * routes that need them answer 503 rather than serving a half-wired app.
 */
export interface RuntimeDependencies {
  /** Open content-authority handle; absent while the app is database-free. */
  persistence: PersistenceHandles | undefined;
  /** Data directory of the open handle; absent with the handle. */
  dataDirectory: string | undefined;
  /** Resolved environment name; also decides the production-only surfaces. */
  environment: string;
  /** Auth service; absent while the app is database-free. */
  authService: AuthService | undefined;
  /** One-time first-boot setup token gate; absent with the auth service. */
  setupTokenGuard: SetupTokenGuard | undefined;
  /** Release identity from the manifest SSOT; feeds logging and diagnostics. */
  productIdentity: ProductIdentity;
  /** Provider identity and model settings shared by generation and catalog routes. */
  provider: ProviderRuntime;
  /** Studio service container; absent while the app is database-free. */
  studioServices: StudioServices | undefined;
  /** /version metadata frozen at startup; the SPA shell reports the same values. */
  versionInfo: VersionInfo;
}

/** Session and auth handles resolved once per app instance. */
interface AuthRuntime {
  authService: AuthService | undefined;
  setupTokenGuard: SetupTokenGuard | undefined;
  /** Whether the session secret is explicit; the value itself never leaves here. */
  sessionSecretConfigured: boolean;
}

/**
 * Resolve the session secret, the auth store, the first-boot setup token
 * gate, and the auth service for one app instance. A database-free app still
 * resolves a secret — the diagnostics export reports whether it was explicit
 * — but has no store, so the auth service and token gate stay absent and the
 * auth surfaces answer 503 instead of authenticating nobody. Failures are
 * never swallowed: a secret resolution or token-arming error propagates to
 * the caller, which closes the partially built app.
 */
function createAuthRuntime(
  app: FastifyInstance,
  options: RuntimeDependencyInputs,
  persistence: PersistenceHandles | undefined,
  environment: string,
): AuthRuntime {
  // One resolution for the whole app (#654): the session secret is either
  // explicit (options or config) or generated — and outside the guarded
  // production/staging environments the generated key is persisted into the
  // data directory once and reused, so a restart no longer logs the author
  // out (DR-040). The diagnostics export reports only which of the three it
  // was, never the value.
  const resolvedSessionSecret =
    options.sessionSecret ??
    resolveSessionSecret({
      configured: options.config?.sessionSecret,
      environment,
      dataDirectory: persistence?.dataDirectory,
    });
  const authStore = persistence === undefined ? undefined : new DrizzleAuthStore(persistence.db.db);
  // First-boot takeover gate (DR-008): while no owner exists the one-time
  // setup token is armed and logged here; the raw socket peer decides the
  // loopback exemption inside the route, never a forwarded address.
  const setupTokenGuard =
    persistence === undefined || authStore === undefined
      ? undefined
      : armFirstBootSetupToken({
          directory: persistence.dataDirectory,
          ownerExists: authStore.ownerExists(),
          onToken: (token) => app.log.info({ setup_token: token }, "first-start setup token"),
          onWarning: (message, error) => app.log.warn({ err: error }, message),
        });
  return {
    authService:
      persistence === undefined || authStore === undefined
        ? undefined
        : new AuthService({
            store: authStore,
            sessionSecret: resolvedSessionSecret ?? randomBytes(32).toString("base64url"),
            now: options.clock,
          }),
    setupTokenGuard,
    sessionSecretConfigured: resolvedSessionSecret !== undefined,
  };
}

/**
 * Assemble the runtime handles one app instance owns: the persistence
 * pipeline when a database path is configured, the session/auth runtime, the
 * AI provider runtime, the Studio service container, and the frozen /version
 * metadata. The operation capacity policy arrives already resolved and
 * validated — capacity must be adjudicated before Fastify exists — and is
 * only passed through to the service container.
 */
export async function createRuntimeDependencies(
  app: FastifyInstance,
  options: RuntimeDependencyInputs,
  productIdentity: ProductIdentity,
  operationCapacity: OperationCapacityPolicy | undefined,
): Promise<RuntimeDependencies> {
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

  const environment =
    options.environment ?? options.config?.environment ?? process.env.NODE_ENV ?? "development";
  const auth = createAuthRuntime(app, options, persistence, environment);
  const provider = buildProviderRuntime(options.config, {
    ...options,
    studioDataDirectory: persistence?.dataDirectory,
  });
  app.addHook("onClose", async () => provider.aiOperations.close());
  const studioServices =
    persistence === undefined
      ? undefined
      : assembleStudioServices(persistence, {
          config: options.config,
          provider,
          operationCapacity,
          options,
          productIdentity,
          sessionSecretConfigured: auth.sessionSecretConfigured,
        });
  const versionInfo: VersionInfo = {
    version: productIdentity.version,
    name: productIdentity.name,
    runtime: { name: "node", version: process.versions.node },
    environment,
    build: options.buildSha ?? process.env.BUILD_SHA ?? "unknown",
  };

  return {
    persistence,
    dataDirectory: persistence?.dataDirectory,
    environment,
    authService: auth.authService,
    setupTokenGuard: auth.setupTokenGuard,
    productIdentity,
    provider,
    studioServices,
    versionInfo,
  };
}
