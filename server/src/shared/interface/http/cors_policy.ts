import { LOCALHOST_CORS_PORTS } from "./origin_validation.js";

/** The default development origin set, derived from the single port SSOT. */
export const DEFAULT_CORS_ORIGINS: string[] = [...LOCALHOST_CORS_PORTS].map(
  (port) => `http://localhost:${port}`,
);

export interface CorsAllowList {
  /** True for a configured bare `*` — reflect any origin (non-production only). */
  readonly allowAll: boolean;
  /** Concrete origins with localhost wildcards materialized to the dev ports. */
  readonly origins: string[];
}

/**
 * Materialize configured CORS origins the way the Python gold standard does:
 * `http://localhost:*`-style entries expand to exactly the development ports
 * from the shared SSOT; every other entry passes through lowercased.
 */
export function corsAllowList(configured: string[]): CorsAllowList {
  const origins: string[] = [];
  for (const raw of configured) {
    const origin = raw.trim().toLowerCase();
    if (origin === "*") {
      return { allowAll: true, origins: [] };
    }
    if (origin.endsWith(":*")) {
      const prefix = origin.slice(0, -1);
      if (prefix.includes("localhost") || prefix.includes("127.0.0.1")) {
        origins.push(...[...LOCALHOST_CORS_PORTS].map((port) => `${prefix}${port}`));
        continue;
      }
    }
    origins.push(origin);
  }
  return { allowAll: false, origins };
}
