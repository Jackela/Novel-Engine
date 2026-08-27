import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { readFile, unlink, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { SnapshotArtifactService } from "../../src/contexts/studio/application/export_artifact_service.js";
import type {
  ExportArtifactFormat,
  ExportArtifactRecord,
} from "../../src/contexts/studio/application/ports/export_store.js";
import { exports as exportArtifacts } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import {
  anonymousCall,
  buildStudioApp,
  call,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

interface SessionPayload {
  session_id: string;
  kind: "owner" | "guest";
  owner_id: string | null;
  expires_at: string | null;
}

const deliveryTypes: Record<ExportArtifactFormat, string> = {
  markdown: "text/markdown; charset=utf-8",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  epub: "application/epub+zip",
};
const extensions: Record<ExportArtifactFormat, string> = {
  markdown: "md",
  docx: "docx",
  epub: "epub",
};

function principalFromSession(payload: SessionPayload): Principal {
  return {
    sessionId: payload.session_id,
    kind: "owner",
    ownerId: payload.owner_id,
    expiresAt: payload.expires_at === null ? null : new Date(payload.expires_at),
  };
}

function downloadUrl(projectId: string, artifactId: string): string {
  return (
    `/api/projects/${encodeURIComponent(projectId)}/exports/` +
    `${encodeURIComponent(artifactId)}/download`
  );
}

function publicArtifact(record: ExportArtifactRecord) {
  return {
    id: record.id,
    project_id: record.projectId,
    snapshot_id: record.snapshotId,
    format: record.format,
    size_bytes: record.sizeBytes,
    checksum_sha256: record.checksumSha256,
    created_at: record.createdAt.toISOString(),
    download_url: downloadUrl(record.projectId, record.id),
  };
}

async function expectDelivery(
  app: Parameters<typeof call>[0],
  jar: Parameters<typeof call>[1],
  directory: string,
  record: ExportArtifactRecord,
): Promise<void> {
  const response = await call(app, jar, "GET", downloadUrl(record.projectId, record.id));
  expect(response.statusCode, response.body).toBe(200);
  expect(response.rawPayload).toEqual(await readFile(join(directory, record.relativePath)));
  expect(response.headers["content-type"]).toBe(deliveryTypes[record.format]);
  expect(response.headers["content-disposition"]).toBe(
    `attachment; filename="export.${extensions[record.format]}"`,
  );
}

describe("export artifact catalog and delivery", () => {
  it("serves only authorized, integrity-backed export artifacts and documents the GET contract", async () => {
    const clock = monotonicClock();
    const { app, directory } = await buildStudioApp(clock);
    try {
      const owner = await ownerJar(app);
      const session = await call(app, owner, "GET", "/api/session");
      expect(session.statusCode, session.body).toBe(200);
      const principal = principalFromSession(session.json() as SessionPayload);
      expect(principal).toMatchObject({ kind: "owner", ownerId: expect.any(String) });

      const project = await seedProject(app, owner, "Delivery evidence");
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("Expected the real Studio database.");

      const ids = ["evidence markdown+%?", "evidence docx+%?", "evidence epub+%?"];
      let nextId = 0;
      const artifacts = new SnapshotArtifactService(
        new ExportStorePart(database),
        new DrizzleStudioStore({ database, dataDirectory: directory }),
        new FilesystemExportArtifactGateway(directory),
        {
          now: clock,
          newId: () => {
            const id = ids[nextId];
            if (id === undefined) throw new Error("Unexpected extra artifact id request.");
            nextId += 1;
            return id;
          },
        },
      );
      const markdown = await artifacts.materializeSnapshotArtifact(
        principal,
        project.id,
        "markdown",
      );
      const docx = await artifacts.materializeSnapshotArtifact(principal, project.id, "docx");
      const epub = await artifacts.materializeSnapshotArtifact(principal, project.id, "epub");
      const records = [markdown, docx, epub];
      expect(records.map((record) => record.id)).toEqual(ids);

      const list = await call(app, owner, "GET", `/api/projects/${project.id}/exports`);
      expect(list.statusCode, list.body).toBe(200);
      expect(list.json()).toEqual({ exports: [...records].reverse().map(publicArtifact) });
      for (const item of list.json().exports as Array<Record<string, unknown>>) {
        expect(item).not.toHaveProperty("relative_path");
        expect(item).not.toHaveProperty("path");
      }

      for (const record of records) {
        await expectDelivery(app, owner, directory, record);
      }

      const anonymous = await app.inject({
        method: "GET",
        url: downloadUrl(project.id, markdown.id),
      });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");

      const anonymousCatalog = await anonymousCall(
        app,
        "GET",
        `/api/projects/${project.id}/exports`,
      );
      expect(anonymousCatalog.statusCode).toBe(401);
      expect(anonymousCatalog.json().error.code).toBe("UNAUTHORIZED");
      const anonymousDownload = await anonymousCall(
        app,
        "GET",
        downloadUrl(project.id, markdown.id),
      );
      expect(anonymousDownload.statusCode).toBe(401);
      expect(anonymousDownload.json().error.code).toBe("UNAUTHORIZED");

      const tampered = markdown;
      const sentinel = join(dirname(directory), `${project.id}-outside-root.txt`);
      const sentinelBytes = Buffer.from("outside-root export sentinel", "utf8");
      await writeFile(sentinel, sentinelBytes);
      database
        .update(exportArtifacts)
        .set({
          relativePath: `../${project.id}-outside-root.txt`,
          sizeBytes: sentinelBytes.length,
          checksumSha256: createHash("sha256").update(sentinelBytes).digest("hex"),
        })
        .where(eq(exportArtifacts.id, tampered.id))
        .run();
      const outside = await call(app, owner, "GET", downloadUrl(project.id, tampered.id));
      expect(outside.statusCode).toBe(404);
      expect(outside.json().error.code).toBe("NOT_FOUND");
      expect(outside.body).not.toContain(sentinelBytes.toString("utf8"));

      const missing = docx;
      await unlink(join(directory, missing.relativePath));
      const absent = await call(app, owner, "GET", downloadUrl(project.id, missing.id));
      expect(absent.statusCode).toBe(404);
      expect(absent.json().error.code).toBe("NOT_FOUND");

      const openapiResponse = await app.inject({ method: "GET", url: "/openapi.json" });
      expect(openapiResponse.statusCode).toBe(200);
      const paths = (openapiResponse.json() as { paths: Record<string, Record<string, unknown>> })
        .paths;
      const catalogPath = "/api/projects/{projectId}/exports";
      const deliveryPath = "/api/projects/{projectId}/exports/{exportId}/download";
      expect(Object.keys(paths[catalogPath] ?? {}).sort()).toEqual(["get", "post"]);
      expect(Object.keys(paths[deliveryPath] ?? {}).sort()).toEqual(["get"]);
      const deliverySpec = JSON.stringify(paths[deliveryPath]);
      expect(deliverySpec).toContain("binary");
      expect(deliverySpec).toContain("Content-Disposition");
      for (const contentType of Object.values(deliveryTypes)) {
        expect(deliverySpec).toContain(contentType);
      }
    } finally {
      await app.close();
    }
  });

  it("removes completed production artifacts when their project is deleted", async () => {
    const clock = monotonicClock();
    const { app, directory } = await buildStudioApp(clock);
    try {
      const owner = await ownerJar(app);
      const session = await call(app, owner, "GET", "/api/session");
      expect(session.statusCode, session.body).toBe(200);
      const principal = principalFromSession(session.json() as SessionPayload);
      const project = await seedProject(app, owner, "Completed export deletion evidence");
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("Expected the real Studio database.");

      const completed = await new SnapshotArtifactService(
        new ExportStorePart(database),
        new DrizzleStudioStore({ database, dataDirectory: directory }),
        new FilesystemExportArtifactGateway(directory),
        { now: clock, newId: () => "completed-export-evidence" },
      ).materializeSnapshotArtifact(principal, project.id, "markdown");
      const exportDirectory = join(directory, "exports", project.id);
      expect(
        database
          .select()
          .from(exportArtifacts)
          .where(eq(exportArtifacts.projectId, project.id))
          .all(),
      ).toEqual([expect.objectContaining({ id: completed.id, projectId: project.id })]);
      expect(existsSync(join(directory, completed.relativePath))).toBe(true);

      const removed = await call(app, owner, "DELETE", `/api/projects/${project.id}`);
      expect(removed.statusCode, removed.body).toBe(204);
      expect(
        database
          .select()
          .from(exportArtifacts)
          .where(eq(exportArtifacts.projectId, project.id))
          .all(),
      ).toEqual([]);
      expect(existsSync(exportDirectory)).toBe(false);

      const catalog = await call(app, owner, "GET", `/api/projects/${project.id}/exports`);
      expect(catalog.statusCode, catalog.body).toBe(404);
      expect(catalog.json().error.code).toBe("NOT_FOUND");
      const download = await call(app, owner, "GET", downloadUrl(project.id, completed.id));
      expect(download.statusCode, download.body).toBe(404);
      expect(download.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});
