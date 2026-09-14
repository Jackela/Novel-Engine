import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import { Type } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { AppError, ERROR_CODES } from "../../../../shared/interface/http/error_envelope.js";
import type { DiagnosticsSummary } from "../../application/diagnostics_service.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { authedReadResponses } from "./route_responses.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { projectIdParams } from "./studio_request_schemas.js";

/**
 * The diagnostics export response (#654). Structurally redacted by its
 * shape: configuration state is booleans only, the error summary carries
 * persisted messages only, and no field can hold a secret value, a provider
 * response body, or manuscript content.
 */
export const diagnosticsResponseSchema = Type.Object(
  {
    generated_at: Type.String(),
    product: Type.Object(
      { name: Type.String(), version: Type.String() },
      { additionalProperties: false },
    ),
    runtime: Type.Object(
      {
        platform: Type.String(),
        architecture: Type.String(),
        node_version: Type.String(),
      },
      { additionalProperties: false },
    ),
    configuration: Type.Object(
      {
        provider: Type.Object(
          { id: Type.String(), configured: Type.Boolean() },
          { additionalProperties: false },
        ),
        keys: Type.Object(
          {
            session_secret: Type.Boolean(),
            dashscope_api_key: Type.Boolean(),
            openai_compatible_api_key: Type.Boolean(),
          },
          { additionalProperties: false },
        ),
      },
      { additionalProperties: false },
    ),
    database: Type.Object(
      {
        quick_check: Type.String(),
        journal_mode: Type.String(),
        foreign_keys: Type.Boolean(),
        owner_configured: Type.Boolean(),
      },
      { additionalProperties: false },
    ),
    recent_errors: Type.Array(
      Type.Object(
        { message: Type.String(), occurred_at: Type.String() },
        { additionalProperties: false },
      ),
    ),
  },
  { additionalProperties: false },
);

/** The snake_case wire view of the service's summary. */
function diagnosticsPayload(summary: DiagnosticsSummary): Record<string, unknown> {
  return {
    generated_at: summary.generatedAt,
    product: summary.product,
    runtime: {
      platform: summary.runtime.platform,
      architecture: summary.runtime.architecture,
      node_version: summary.runtime.nodeVersion,
    },
    configuration: {
      provider: summary.configuration.provider,
      keys: {
        session_secret: summary.configuration.keys.sessionSecret,
        dashscope_api_key: summary.configuration.keys.dashscopeApiKey,
        openai_compatible_api_key: summary.configuration.keys.openaiCompatibleApiKey,
      },
    },
    database: {
      quick_check: summary.database.quickCheck,
      journal_mode: summary.database.journalMode,
      foreign_keys: summary.database.foreignKeys,
      owner_configured: summary.database.ownerConfigured,
    },
    recent_errors: summary.recentErrors.map((error) => ({
      message: error.message,
      occurred_at: error.occurredAt,
    })),
  };
}

function requireDiagnostics(options: StudioRoutesOptions) {
  const diagnostics = requireServices(options).diagnostics;
  if (diagnostics === undefined) {
    throw new AppError({
      statusCode: 503,
      code: ERROR_CODES.SERVICE_UNAVAILABLE,
      message: "The diagnostics surface is not configured.",
    });
  }
  return diagnostics;
}

/**
 * The opt-in diagnostics export (#654): one owner-guarded read-only route
 * scoped to the current project, matching its Settings-panel mount point.
 * Thin-handler discipline — the assembly and redaction rules live in the
 * application service.
 */
export const diagnosticsRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (
  fastify,
  options,
) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects/:projectId/diagnostics",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        response: authedReadResponses({
          200: diagnosticsResponseSchema,
        }),
      },
    },
    async (request) =>
      withStudioErrors(() =>
        diagnosticsPayload(
          requireDiagnostics(options).collectDiagnostics(
            requirePrincipal(request),
            request.params.projectId,
          ),
        ),
      ),
  );
};
