import { type Static, Type } from "@fastify/type-provider-typebox";
import { EXPORT_ARTIFACT_FORMATS } from "../export_artifact_identity.js";
import type { ExportArtifactFormat } from "../ports/export_store.js";

/**
 * Export artifact payload SSOT (#440): the read-only catalog entry emitted by
 * `exportArtifactPayload` for the export LIST surface. The file bytes ride a
 * separate confined download endpoint, so the payload only carries integrity
 * and delivery metadata.
 */
export const exportArtifactPayloadSchema = Type.Object(
  {
    id: Type.String(),
    project_id: Type.String(),
    snapshot_id: Type.String(),
    format: Type.Unsafe<ExportArtifactFormat>({
      type: "string",
      enum: [...EXPORT_ARTIFACT_FORMATS],
    }),
    size_bytes: Type.Integer({ minimum: 0 }),
    checksum_sha256: Type.String({ pattern: "^[a-f0-9]{64}$" }),
    created_at: Type.String({ format: "date-time" }),
    download_url: Type.String(),
  },
  { additionalProperties: false },
);

export type ExportArtifactPayload = Static<typeof exportArtifactPayloadSchema>;
