import { describe, expect, it } from "vitest";

import {
  buildStudioApp,
  call,
  getProject,
  listRevisions,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

type Jar = Awaited<ReturnType<typeof ownerJar>>;

interface LoreStatusEnvelope {
  lore_status?: string;
  error?: { code?: string };
}

function loreStatusUrl(projectId: string, documentId: string): string {
  return `/api/projects/${projectId}/documents/${documentId}/lore-status`;
}

async function setStatus(
  app: Awaited<ReturnType<typeof buildStudioApp>>["app"],
  jar: Jar,
  projectId: string,
  documentId: string,
  loreStatus: string,
): Promise<{ status: number; body: LoreStatusEnvelope }> {
  const response = await call(app, jar, "PUT", loreStatusUrl(projectId, documentId), {
    lore_status: loreStatus,
  });
  return { status: response.statusCode, body: response.json() as LoreStatusEnvelope };
}

describe("lore lifecycle status surface (#444)", () => {
  it("creates lore entries at draft and promotes them through the closed enum", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Lifecycle Studio");
      const character = await seedDocument(app, jar, project.id, {
        kind: "character",
        title: "Mara",
        content_markdown: "Mara keeps the flooded archive.",
      });

      // New lore entries default to draft: nothing injectable until promoted.
      let detail = await getProject(app, jar, project.id);
      expect(detail.documents.find((d) => d.id === character.id)?.lore_status).toBe("draft");

      expect(await setStatus(app, jar, project.id, character.id, "stable")).toEqual({
        status: 200,
        body: { lore_status: "stable" },
      });
      detail = await getProject(app, jar, project.id);
      expect(detail.documents.find((d) => d.id === character.id)?.lore_status).toBe("stable");

      expect(await setStatus(app, jar, project.id, character.id, "deprecated")).toEqual({
        status: 200,
        body: { lore_status: "deprecated" },
      });
      detail = await getProject(app, jar, project.id);
      expect(detail.documents.find((d) => d.id === character.id)?.lore_status).toBe("deprecated");
    } finally {
      await app.close();
    }
  });

  it("refuses unknown status values with 422 and changes nothing", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Refusing Studio");
      const character = await seedDocument(app, jar, project.id, {
        kind: "character",
        title: "Mara",
      });

      for (const invalid of ["archived", "STABLE", ""]) {
        const refused = await setStatus(app, jar, project.id, character.id, invalid);
        expect(refused.status, `status '${invalid}' must be refused`).toBe(422);
      }

      const detail = await getProject(app, jar, project.id);
      expect(detail.documents.find((d) => d.id === character.id)?.lore_status).toBe("draft");
    } finally {
      await app.close();
    }
  });

  it("refuses status writes for non-lore kinds with 422 INVALID_OPERATION", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Non-Lore Studio");
      const chapter = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Stacks",
      });

      const refused = await setStatus(app, jar, project.id, chapter.id, "stable");
      expect(refused.status).toBe(422);
      expect(refused.body.error?.code).toBe("INVALID_OPERATION");

      // The lifecycle semantics never leak beyond lore: non-lore payload
      // stays null even though the row keeps the column default.
      const detail = await getProject(app, jar, project.id);
      expect(detail.documents.find((d) => d.id === chapter.id)?.lore_status).toBeNull();
    } finally {
      await app.close();
    }
  });

  it("keeps the status write revision-free and durable across content saves", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Durable Status");
      const world = await seedDocument(app, jar, project.id, {
        kind: "world",
        title: "Sable Reaches",
        content_markdown: "Original body.",
      });
      expect(await setStatus(app, jar, project.id, world.id, "stable")).toEqual({
        status: 200,
        body: { lore_status: "stable" },
      });
      const before = await listRevisions(app, jar, project.id, world.id);

      // Document-level state (#444): a metadata-replacing save must ride
      // through without touching the lifecycle status.
      const saved = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/${world.id}`,
        {
          content_markdown: "Rewritten body.",
          base_revision_id: world.current_revision_id,
        },
      );
      expect(saved.statusCode, saved.body).toBe(200);

      const after = await listRevisions(app, jar, project.id, world.id);
      expect(after).toHaveLength(before.length + 1);
      const detail = await getProject(app, jar, project.id);
      expect(detail.documents.find((d) => d.id === world.id)?.lore_status).toBe("stable");
    } finally {
      await app.close();
    }
  });

  it("answers 404 outside the project or for an unknown document", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const mine = await seedProject(app, jar, "Mine Status");
      const other = await seedProject(app, jar, "Other Status");
      const foreign = await seedDocument(app, jar, other.id, {
        kind: "character",
        title: "Foreigner",
      });

      expect((await setStatus(app, jar, mine.id, foreign.id, "stable")).status).toBe(404);
      expect((await setStatus(app, jar, mine.id, "missing-document", "stable")).status).toBe(404);
    } finally {
      await app.close();
    }
  });
});
