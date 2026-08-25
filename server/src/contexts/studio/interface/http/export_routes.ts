import type { FastifyPluginAsync } from "fastify";

import type { Principal } from "../../../../shared/application/ports/auth.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import type {
  ExportArtifactFormat,
  ExportArtifactRecord,
} from "../../application/ports/export_store.js";
import { jobResponseSchema } from "./job_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";

const timestampSchema = { type: "string", format: "date-time" } as const;
const exportResponseSchema = {
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
const exportListResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: { exports: { type: "array", items: exportResponseSchema } },
  required: ["exports"],
} as const;
const binaryExportSchema = {
  type: "string",
  format: "binary",
  headers: { "Content-Disposition": { type: "string" } },
} as const;
const exportCreateSchema = {
  type: "object",
  properties: { format: { type: "string", enum: ["markdown", "docx", "epub"] } },
  required: ["format"],
  additionalProperties: false,
} as const;
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

/** `withStudioErrors` is synchronous; artifact reads must map rejected promises too. */
async function withDeliveryErrors<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation();
  } catch (error) {
    return withStudioErrors<T>(() => {
      throw error;
    });
  }
}

/**
 * Project-scoped export surface: the synchronous POST bridge that reports a
 * terminal job, the read-only artifact catalog, and confined binary delivery.
 */
export const exportRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);
  const principal = (request: { principal?: Principal }) => request.principal as Principal;

  app.post(
    "/api/projects/:projectId/exports",
    {
      preHandler: [guard],
      schema: { body: exportCreateSchema, response: { 201: jobResponseSchema } },
    },
    async (request, reply) => {
      const { projectId } = request.params as { projectId: string };
      const { format } = request.body as { format: ExportArtifactFormat };
      const payload = await withDeliveryErrors(() =>
        requireServices(options).jobHistory.recordExportJob(principal(request), projectId, format),
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
        security: [{ cookieAuth: [] }],
        response: { 200: exportListResponseSchema },
      },
    },
    async (request) => {
      const { projectId } = request.params as { projectId: string };
      return withStudioErrors(() => ({
        exports: requireServices(options)
          .artifacts.catalogProjectArtifacts(principal(request), projectId)
          .map((artifact) => exportPayload(artifact, projectId)),
      }));
    },
  );

  app.get(
    "/api/projects/:projectId/exports/:exportId/download",
    {
      preHandler: [guard],
      schema: {
        security: [{ cookieAuth: [] }],
        produces: [
          "text/markdown; charset=utf-8",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "application/epub+zip",
        ],
        response: { 200: binaryExportSchema },
      },
    },
    async (request, reply) => {
      const { projectId, exportId } = request.params as { projectId: string; exportId: string };
      const artifact = await withDeliveryErrors(() =>
        requireServices(options).artifacts.readArtifactForDelivery(
          principal(request),
          projectId,
          exportId,
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
