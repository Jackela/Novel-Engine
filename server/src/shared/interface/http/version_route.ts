/**
 * Diagnostic identity surface: `GET /version` reports which build is
 * serving — release version and product name from the identity SSOT, the
 * Node runtime, the resolved environment, and the build SHA. The payload is
 * assembled once by the API composition root; the route only echoes it.
 *
 * In production the route is reduced to the public product identity
 * (name and version): runtime, environment, and build are deployment
 * fingerprints and must not reach anonymous callers (DR-035). Development
 * and test keep the full diagnostics payload.
 */
import type { FastifyPluginAsync } from "fastify";

interface RuntimeIdentity {
  name: string;
  version: string;
}

/** What `GET /version` answers with, verbatim. */
export interface VersionInfo {
  version: string;
  name: string;
  runtime: RuntimeIdentity;
  environment: string;
  build: string;
}

interface VersionRoutesOptions {
  info: VersionInfo;
  /** When true, only the product identity is served (production). */
  production: boolean;
}

/** The public slice: product identity without deployment fingerprints. */
function publicIdentity(info: VersionInfo): Pick<VersionInfo, "name" | "version"> {
  return { name: info.name, version: info.version };
}

/** Registers the single read-only `GET /version` route. */
export const versionRoutes: FastifyPluginAsync<VersionRoutesOptions> = async (app, options) => {
  app.get(
    "/version",
    {
      schema: {
        response: {
          200: {
            type: "object",
            properties: {
              version: { type: "string" },
              name: { type: "string" },
              runtime: {
                type: "object",
                properties: {
                  name: { type: "string" },
                  version: { type: "string" },
                },
              },
              environment: { type: "string" },
              build: { type: "string" },
            },
          },
        },
      },
    },
    async () => (options.production ? publicIdentity(options.info) : options.info),
  );
};
