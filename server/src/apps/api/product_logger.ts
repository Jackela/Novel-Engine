import type { FastifyServerOptions } from "fastify";
import type { ProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";

/**
 * Keep every structured application log anchored to the product SSOT, and
 * apply the configured level (DR-041): `LOG_LEVEL` reaches the pino logger
 * through the resolved server config, while an explicitly constructed logger
 * option object keeps its own level. `false` still disables logging entirely.
 */
export function loggerWithProductIdentity(
  logger: FastifyServerOptions["logger"],
  identity: ProductIdentity,
  level: string = "info",
): false | Exclude<FastifyServerOptions["logger"], boolean | undefined> {
  if (logger === false) return false;
  const configured: Exclude<FastifyServerOptions["logger"], boolean | undefined> =
    logger === true || logger === undefined ? {} : logger;
  return {
    ...configured,
    level: configured.level ?? level,
    base: {
      ...(configured.base ?? {}),
      product_name: identity.name,
      product_version: identity.version,
    },
  };
}
