import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import { Type } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { errorEnvelopeResponse } from "../../../../shared/interface/http/error_envelope.js";
import type {
  ExportArtifactFormat,
  ExportArtifactRecord,
} from "../../application/ports/export_store.js";
import { jobResponseSchema } from "./job_schemas.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withAsyncStudioErrors, withStudioErrors } from "./studio_error_mapping.js";
import { exportIdParams, projectIdParams } from "./studio_request_schemas.js";
import { operationInFlightSchema } from "./studio_schemas.js";

const timestampSchema = { type: "string", format: "date-time" } as const;
const exportResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    id: { type: "string" },
    project_id: { type: "string" },
    snapshot_id: { type: "string" },
    format: { type: "string", enum: ["markdown", "docx", "epub"] },
    size_bytes: { type: "integer", minimum: 0 },
    checksum_sha256: { type: "string", pattern: "^[a-f0-9]{64}$" },
    created_at: timestampSchema,
    download_url: { type: "string" },
  },
  required: [
    "id",
    "project_id",
    "snapshot_id",
    "format",
    "size_bytes",
    "checksum_sha256",
    "created_at",
    "download_url",
  ],
} as const;
const exportListResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: { exports: { type: "array", items: exportResponseSchema } },
  required: ["exports"],
} as const;
const binaryExportSchema: JsonResponseSchema = {
  type: "string",
  format: "binary",
  headers: { "Content-Disposition": { type: "string" } },
} as const;
const exportCreateSchema = Type.Object(
  {
    format: Type.Unsafe<ExportArtifactFormat>({
      type: "string",
      enum: ["markdown", "docx", "epub"],
    }),
  },
  { additionalProperties: false },
);
const deliveryByFormat: Record<ExportArtifactFormat, { contentType: string; extension: string }> = {
  markdown: { contentType: "text/markdown; charset=utf-8", extension: "md" },
  docx: {
    contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    extension: "docx",
  },
  epub: { contentType: "application/epub+zip", extension: "epub" },
};

function exportPayload(artifact: ExportArtifactRecord, projectId: string) {
  return {
    id: artifact.id,
    project_id: artifact.projectId,
    snapshot_id: artifact.snapshotId,
    format: artifact.format,
    size_bytes: artifact.sizeBytes,
    checksum_sha256: artifact.checksumSha256,
    created_at: artifact.createdAt.toISOString(),
    download_url:
      `/api/projects/${encodeURIComponent(projectId)}/exports/` +
      `${encodeURIComponent(artifact.id)}/download`,
  };
}

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
      const payload = await withAsyncStudioErrors(() =>
        requireServices(options).jobHistory.recordExportJob(
          requirePrincipal(request),
          request.params.projectId,
          format,
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
          .map((artifact) => exportPayload(artifact, request.params.projectId)),
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
        .header("content-disposition", `attachment; filename="export.${delivery.extension}"`)
        .send(artifact.bytes);
    },
  );
};
