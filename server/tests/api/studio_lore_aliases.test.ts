import { describe, expect, it } from "vitest";

import {
  buildStudioApp,
  call,
  listRevisions,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

type Jar = Awaited<ReturnType<typeof ownerJar>>;
type App = Awaited<ReturnType<typeof buildStudioApp>>["app"];

function aliasesUrl(projectId: string, documentId: string): string {
  return `/api/projects/${projectId}/documents/${documentId}/aliases`;
}

interface AliasEnvelope {
  aliases?: string[];
  error?: { code?: string };
}

async function setAliases(
  app: App,
  jar: Jar,
  projectId: string,
  documentId: string,
  aliases: string[],
): Promise<{ status: number; body: AliasEnvelope }> {
  const response = await call(app, jar, "PUT", aliasesUrl(projectId, documentId), { aliases });
  return { status: response.statusCode, body: response.json() as AliasEnvelope };
}

async function getAliases(
  app: App,
  jar: Jar,
  projectId: string,
  documentId: string,
): Promise<{ status: number; body: AliasEnvelope }> {
  const response = await call(app, jar, "GET", aliasesUrl(projectId, documentId));
  return { status: response.statusCode, body: response.json() as AliasEnvelope };
}

describe("document lore-alias surface (#315)", () => {
  it("writes and reads normalized aliases for a character document", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Alias Studio");
      const character = await seedDocument(app, jar, project.id, {
        kind: "character",
        title: "Mara",
        content_markdown: "Mara keeps the flooded archive.",
      });

      const written = await setAliases(app, jar, project.id, character.id, [
        "  the archivist ",
        "",
        "The Archivist",
        "keeper",
      ]);
      expect(written.status, JSON.stringify(written.body)).toBe(200);
      // "The Archivist" case-insensitively duplicates the first spelling.
      expect(written.body).toEqual({ aliases: ["the archivist", "keeper"] });

      const readBack = await getAliases(app, jar, project.id, character.id);
      expect(readBack.status).toBe(200);
      expect(readBack.body).toEqual({ aliases: ["the archivist", "keeper"] });
    } finally {
      await app.close();
    }
  });

  it("serves the same surface for world documents and defaults to empty", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "World Alias");
      const world = await seedDocument(app, jar, project.id, {
        kind: "world",
        title: "Sable Reaches",
      });
      expect(await getAliases(app, jar, project.id, world.id)).toEqual({
        status: 200,
        body: { aliases: [] },
      });

      const cleared = await setAliases(app, jar, project.id, world.id, []);
      expect(cleared.status).toBe(200);
      expect(cleared.body).toEqual({ aliases: [] });
    } finally {
      await app.close();
    }
  });

  it("refuses alias writes for non-lore kinds without touching anything", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Refusal Studio");
      const note = await seedDocument(app, jar, project.id, { kind: "note", title: "Scratch" });

      const refused = await setAliases(app, jar, project.id, note.id, ["whatever"]);
      expect(refused.status).toBe(422);
      expect(refused.body.error?.code).toBe("INVALID_OPERATION");

      const readBack = await getAliases(app, jar, project.id, note.id);
      expect(readBack.body).toEqual({ aliases: [] });
    } finally {
      await app.close();
    }
  });

  it("keeps the alias write revision-free — revisions and content stay untouched", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Immutable Alias");
      const character = await seedDocument(app, jar, project.id, {
        kind: "character",
        title: "Mara",
        content_markdown: "Original body.",
      });
      const before = await listRevisions(app, jar, project.id, character.id);

      const written = await setAliases(app, jar, project.id, character.id, ["the archivist"]);
      expect(written.status).toBe(200);

      const after = await listRevisions(app, jar, project.id, character.id);
      expect(after).toHaveLength(before.length);
      expect(after[0]?.id).toBe(before[0]?.id);
    } finally {
      await app.close();
    }
  });

  it("aliases survive a later metadata-replacing content save", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Surviving Alias");
      const character = await seedDocument(app, jar, project.id, {
        kind: "character",
        title: "Mara",
        content_markdown: "First body.",
      });
      expect((await setAliases(app, jar, project.id, character.id, ["the archivist"])).status).toBe(
        200,
      );

      // The plain save path replaces revision metadata wholesale; document
      // aliases are document-level state and must ride through it (#315).
      const saved = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/${character.id}`,
        {
          content_markdown: "Rewritten body.",
          base_revision_id: character.current_revision_id,
        },
      );
      expect(saved.statusCode, saved.body).toBe(200);

      const readBack = await getAliases(app, jar, project.id, character.id);
      expect(readBack.body).toEqual({ aliases: ["the archivist"] });
    } finally {
      await app.close();
    }
  });

  it("answers 404 outside the project or for an unknown document", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const mine = await seedProject(app, jar, "Mine Aliases");
      const other = await seedProject(app, jar, "Other Aliases");
      const foreign = await seedDocument(app, jar, other.id, {
        kind: "character",
        title: "Foreigner",
      });

      expect((await getAliases(app, jar, mine.id, foreign.id)).status).toBe(404);
      expect((await getAliases(app, jar, mine.id, "missing-document")).status).toBe(404);
      expect((await setAliases(app, jar, other.id, foreign.id, ["x"])).status).toBe(200);
    } finally {
      await app.close();
    }
  });
});
