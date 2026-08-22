/**
 * The CORS contract's development-port authority: the ports localhost
 * wildcards expand to and the default origin set is derived from. Shared by
 * the configuration defaults (infrastructure) and the origin validation and
 * CORS policy (interface) so no layer repeats the list.
 */
export const LOCALHOST_CORS_PORTS: ReadonlySet<string> = new Set(["5173", "4173", "8000"]);

export const DEFAULT_CORS_ORIGINS: string[] = [...LOCALHOST_CORS_PORTS].map(
  (port) => `http://localhost:${port}`,
);
