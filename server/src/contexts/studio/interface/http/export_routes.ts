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
import { exportPageLimit } from "../../application/ports/export_store.js";
import { sendWithinArtifactResponseLifetime } from "./artifact_download_response_lifetime.js";
import {
  exportCreateOrRetry422ResponseSchema,
  exportDownload422ResponseSchema,
  exportJsonErrorResponseSchema,
} from "./export_capacity_schemas.js";
import { decodeExportCursor, encodeExportCursor } from "./export_cursor.js";
import { jobResponseSchema } from "./job_schemas.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withAsyncStudioErrors, withStudioErrors } from "./studio_error_mapping.js";
import { exportIdParams, projectIdParams } from "./studio_request_schemas.js";
import { operationCapacityResponseSchema, operationInFlightSchema } from "./studio_schemas.js";

/**
 * The export artifact response (#440) is the TypeBox payload SSOT from
 * `application/payload_schemas/export.ts`; the LIST envelope wraps those
 * items as bounded keyset pages (#460). Binary delivery keeps its
 * hand-written binary schema below.
 */
const exportListQuerySchema = Type.Object(
  {
    limit: Type.Optional(Type.Integer({ default: 50, minimum: 1, maximum: 100 })),
    cursor: Type.Optional(
      Type.String({
        minLength: 1,
        maxLength: 1024,
        pattern: "^[A-Za-z0-9_-]+$",
      }),
    ),
  },
  { additionalProperties: false },
);
const exportListResponseSchema = Type.Object(
  {
    exports: Type.Array(exportArtifactPayloadSchema),
    next_cursor: Type.Unsafe<string | null>({ type: "string", nullable: true }),
  },
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

const EXPORT_LIST_ERROR_RESPONSES = {
  ...EXPORT_READ_ERROR_RESPONSES,
  422: errorEnvelopeResponse,
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
          // No chapter answers INVALID_OPERATION; a permanent fresh limit has its own stable code.
          422: exportCreateOrRetry422ResponseSchema,
          409: operationInFlightSchema,
          503: operationCapacityResponseSchema,
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
        querystring: exportListQuerySchema,
        security: [{ cookieAuth: [] }],
        response: { 200: exportListResponseSchema, ...EXPORT_LIST_ERROR_RESPONSES },
      },
    },
    async (request) => {
      const cursor =
        request.query.cursor === undefined
          ? undefined
          : decodeExportCursor(request.query.cursor, request.params.projectId);
      return withStudioErrors(() => {
        const page = requireServices(options).artifacts.catalogProjectArtifacts(
          requirePrincipal(request),
          request.params.projectId,
          {
            limit: exportPageLimit(request.query.limit ?? 50),
            ...(cursor === undefined ? {} : { cursor }),
          },
        );
        return {
          exports: page.artifacts.map((artifact) =>
            exportArtifactPayload(artifact, request.params.projectId),
          ),
          next_cursor: encodeExportCursor(request.params.projectId, page.nextCursor),
        };
      });
    },
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
        response: {
          200: binaryExportSchema,
          401: exportJsonErrorResponseSchema,
          404: exportJsonErrorResponseSchema,
          422: exportDownload422ResponseSchema,
          503: operationCapacityResponseSchema,
        },
      },
    },
    async (request, reply) => {
      await withAsyncStudioErrors(() =>
        requireServices(options).artifacts.withArtifactDelivery(
          requirePrincipal(request),
          request.params.projectId,
          request.params.exportId,
          async (artifact) => {
            const delivery = deliveryByFormat[artifact.format];
            await sendWithinArtifactResponseLifetime({
              response: reply.raw,
              request: request.raw,
              socket: request.raw.socket,
              send: () => {
                void reply
                  .type(delivery.contentType)
                  .header(
                    "content-disposition",
                    `attachment; filename="export.${exportArtifactExtension(artifact.format)}"`,
                  )
                  .send(artifact.bytes);
              },
            });
          },
        ),
      );
      return reply;
    },
  );
};
