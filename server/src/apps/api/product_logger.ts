import type { FastifyServerOptions } from "fastify";
import type { ProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";

/** Keep every structured application log anchored to the product SSOT. */
export function loggerWithProductIdentity(
  logger: FastifyServerOptions["logger"],
  identity: ProductIdentity,
): false | Exclude<FastifyServerOptions["logger"], boolean | undefined> {
  if (logger === false) return false;
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
