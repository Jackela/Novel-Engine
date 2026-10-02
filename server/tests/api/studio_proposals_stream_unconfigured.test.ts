import { describe, expect, it } from "vitest";

import { jobs } from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  buildStudioApp,
  call,
  type DocumentPayload,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

const STREAM_PATH = (projectId: string, documentId: string) =>
  `/api/projects/${projectId}/documents/${documentId}/ai-proposals/stream`;

describe("proposal stream unconfigured provider (DR-022)", () => {
  it("answers unconfigured providers with a credential-missing error before any stream", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Unconfigured");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "dashscope",
      });
      expect(response.statusCode).toBe(422);
      expect(response.headers["content-type"]).toContain("application/json");
      const envelope = response.json() as { error: { code: string; message: string } };
      // DR-022: the credential gap is named instead of the misleading
      // "does not support streaming generation" capability message.
      expect(envelope.error.code).toBe("PROVIDER_NOT_CONFIGURED");
      expect(response.body).not.toContain("does not support streaming");
      expect(envelope.error.message).toContain(
        "DASHSCOPE_API_KEY is required when provider is dashscope",
      );
      expect(envelope.error.message).toContain("provider-setup");
      expect(database.select().from(jobs).all()).toHaveLength(0);
    } finally {
      await app.close();
    }
  });
});
