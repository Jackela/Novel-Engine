import type { FastifyPluginAsync } from "fastify";

export interface RuntimeIdentity {
  name: string;
  version: string;
}

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
