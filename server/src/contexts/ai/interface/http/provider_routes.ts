import type { FastifyPluginAsync } from "fastify";
import type { AuthService } from "../../../../shared/application/auth_service.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import {
  buildProviderCatalog,
  type ProviderCatalogOptions,
} from "../../application/model_resolution.js";

export interface ProviderCatalogRoutesOptions extends ProviderCatalogOptions {
  readonly authService?: AuthService | undefined;
}

const providerCatalogResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    providers: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          provider: { type: "string", enum: ["mock", "dashscope", "openai_compatible"] },
          configured: { type: "boolean" },
          model: { type: "string" },
          is_default: { type: "boolean" },
        },
        required: ["provider", "configured", "model", "is_default"],
      },
    },
  },
  required: ["providers"],
} as const;

/** Authenticated catalog of server-owned provider availability and model facts. */
export const providerCatalogRoutes: FastifyPluginAsync<ProviderCatalogRoutesOptions> = async (
  app,
  options,
) => {
  const guard = principalGuard(options.authService);

  app.get(
    "/api/providers",
    { preHandler: [guard], schema: { response: { 200: providerCatalogResponseSchema } } },
    async () => ({ providers: buildProviderCatalog(options) }),
  );
};
