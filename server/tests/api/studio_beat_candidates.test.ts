import { describe, expect, it } from "vitest";

import {
  linkBeat,
  OUTLINE_CANDIDATES,
  outlineAuthority,
  readBeat,
  seedChapterWithOutline,
} from "./studio_beat_helpers.js";
import { buildStudioApp, call, ownerJar, seedDocument } from "./studio_helpers.js";

describe("chapter beat candidates (DR-043)", () => {
  it("lists the authoritative outline's beats as the association candidates", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const { projectId, chapter, outline } = await seedChapterWithOutline(app, jar);

      const read = await call(
        app,
        jar,
        "GET",
        `/api/projects/${projectId}/documents/${chapter.id}/beat`,
      );
      expect(read.statusCode).toBe(200);
      expect(read.json()).toEqual({
        beat: null,
        candidates: OUTLINE_CANDIDATES,
        outline: outlineAuthority(outline),
      });
    } finally {
      await app.close();
    }
  });

  it("names the authoritative outline and reports the outline count when several exist", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const { projectId, chapter, outline } = await seedChapterWithOutline(app, jar);
      // A second outline is legal; the first in reading order stays the
      // authority, and the payload discloses the count instead of hiding it.
      const second = await seedDocument(app, jar, projectId, {
        kind: "outline",
        title: "Alternate outline",
        content_markdown: "# Alternate\n\n## The Tempest\n\nA rival plan.\n",
      });

      const read = await readBeat(app, jar, projectId, chapter.id);
      expect(read.status).toBe(200);
      expect(read.view).toEqual({
        beat: null,
        candidates: OUTLINE_CANDIDATES,
        outline: outlineAuthority(outline, 2),
      });
      expect(read.view?.outline?.document_id).not.toBe(second.id);

      // Only the authoritative outline's beats may be linked.
      const refused = await linkBeat(app, jar, projectId, chapter.id, "The Tempest");
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.code).toBe("INVALID_OPERATION");

      const accepted = await linkBeat(app, jar, projectId, chapter.id, "The Archive");
      expect(accepted.statusCode).toBe(200);
      expect(accepted.json().beat?.title).toBe("The Archive");
    } finally {
      await app.close();
    }
  });
});
