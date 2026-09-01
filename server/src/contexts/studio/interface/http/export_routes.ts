import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import { Type } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { errorEnvelopeResponse } from "../../../../shared/interface/http/error_envelope.js";
import {
  EXPORT_ARTIFACT_FORMATS,
  exportArtifactExtension,
} from "../../application/export_artifact_identity.js";
import { exportArtifactPayloadSchema } from "../../application/payload_schemas/export.js";
import { exportArtifactPayload } from "../../application/payloads.js";
import type { ExportArtifactFormat } from "../../application/ports/export_store.js";
import { jobResponseSchema } from "./job_schemas.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withAsyncStudioErrors, withStudioErrors } from "./studio_error_mapping.js";
import { exportIdParams, projectIdParams } from "./studio_request_schemas.js";
import { operationInFlightSchema } from "./studio_schemas.js";

/**
 * The export artifact response (#440) is the TypeBox payload SSOT from
 * `application/payload_schemas/export.ts`; the LIST envelope wraps those
 * items. Binary delivery keeps its hand-written binary schema below.
 */
const exportListResponseSchema = Type.Object(
  { exports: Type.Array(exportArtifactPayloadSchema) },
  { additionalProperties: false },
);
const binaryExportSchema: JsonResponseSchema = {
  type: "string",
  format: "binary",
  headers: { "Content-Disposition": { type: "string" } },
} as const;
const exportCreateSchema = Type.Object(
  {
    format: Type.Unsafe<ExportArtifactFormat>({
      type: "string",
      enum: [...EXPORT_ARTIFACT_FORMATS],
    }),
  },
  { additionalProperties: false },
);
const deliveryByFormat: Record<ExportArtifactFormat, { contentType: string }> = {
  markdown: { contentType: "text/markdown; charset=utf-8" },
  docx: {
    contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  },
  epub: { contentType: "application/epub+zip" },
};

/** Guard + scope failures shared by the project-scoped export reads. */
const EXPORT_READ_ERROR_RESPONSES = {
  401: errorEnvelopeResponse,
  404: errorEnvelopeResponse,
  503: errorEnvelopeResponse,
} as const;

/**
 * Project-scoped export surface: the synchronous POST bridge that reports a
 * terminal job, the read-only artifact catalog, and confined binary delivery.
 */
export const exportRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.post(
    "/api/projects/:projectId/exports",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        body: exportCreateSchema,
        response: {
          201: jobResponseSchema,
          ...EXPORT_READ_ERROR_RESPONSES,
          403: errorEnvelopeResponse,
          // A project with no chapter answers 422 INVALID_OPERATION.
          422: errorEnvelopeResponse,
          409: operationInFlightSchema,
        },
      },
    },
    async (request, reply) => {
      const { format } = request.body;
      const reportCleanupFailure = (failure: unknown): void => {
        request.log.error(
          { err: failure, errorId: request.id, artifact_cleanup_failed: true },
          "artifact cleanup failed",
        );
      };
      const payload = await withAsyncStudioErrors(() =>
        requireServices(options).jobHistory.recordExportJob(
          requirePrincipal(request),
          request.params.projectId,
          format,
          reportCleanupFailure,
        ),
      );
      reply.status(201);
      return payload;
    },
  );

  app.get(
    "/api/projects/:projectId/exports",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        security: [{ cookieAuth: [] }],
        response: { 200: exportListResponseSchema, ...EXPORT_READ_ERROR_RESPONSES },
      },
    },
    async (request) =>
      withStudioErrors(() => ({
        exports: requireServices(options)
          .artifacts.catalogProjectArtifacts(requirePrincipal(request), request.params.projectId)
          .map((artifact) => exportArtifactPayload(artifact, request.params.projectId)),
      })),
  );

  app.get(
    "/api/projects/:projectId/exports/:exportId/download",
    {
      preHandler: [guard],
      schema: {
        params: exportIdParams,
        security: [{ cookieAuth: [] }],
        produces: [
          "text/markdown; charset=utf-8",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "application/epub+zip",
        ],
        response: { 200: binaryExportSchema, ...EXPORT_READ_ERROR_RESPONSES },
      },
    },
    async (request, reply) => {
      const artifact = await withAsyncStudioErrors(() =>
        requireServices(options).artifacts.readArtifactForDelivery(
          requirePrincipal(request),
          request.params.projectId,
          request.params.exportId,
        ),
      );
      const delivery = deliveryByFormat[artifact.format];
      return reply
        .type(delivery.contentType)
        .header(
          "content-disposition",
          `attachment; filename="export.${exportArtifactExtension(artifact.format)}"`,
        )
        .send(artifact.bytes);
    },
  );
};
