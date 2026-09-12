/**
 * Diagnostic identity surface: `GET /version` reports which build is
 * serving — release version and product name from the identity SSOT, the
 * Node runtime, the resolved environment, and the build SHA. The payload is
 * assembled once by the API composition root; the route only echoes it.
 */
import type { FastifyPluginAsync } from "fastify";

export interface RuntimeIdentity {
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

export interface VersionRoutesOptions {
  info: VersionInfo;
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
    async () => options.info,
  );
};
