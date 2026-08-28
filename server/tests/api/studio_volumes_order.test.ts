import { describe, expect, it } from "vitest";

import {
  buildStudioApp,
  call,
  getProject,
  listVolumes,
  monotonicClock,
  moveChapterToVolume,
  ownerJar,
  seedDocument,
  seedProject,
  seedVolume,
} from "./studio_helpers.js";

interface OrderedDocument {
  id: string;
  kind: string;
  title: string;
  position: number;
  volume_id: string | null;
}

async function orderedChapters(
  app: Parameters<typeof call>[0],
  jar: Parameters<typeof call>[1],
  projectId: string,
): Promise<OrderedDocument[]> {
  const detail = await getProject(app, jar, projectId);
  return (detail.documents as unknown as OrderedDocument[]).filter(
    (document) => document.kind === "chapter",
  );
}

describe("volume reading order", () => {
  it("projects whole-set document reorder onto per-volume chapter order", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Projected Reorder");
      const volumes = await listVolumes(app, jar, project.id);
      const firstVolume = volumes[0];
      if (firstVolume === undefined) throw new Error("expected default volume");
      const secondVolume = await seedVolume(app, jar, project.id, "Second");
      const projectView = await getProject(app, jar, project.id);
      const c1 = projectView.documents[0];
      if (c1 === undefined) throw new Error("expected seeded document");
      const c2 = await seedDocument(app, jar, project.id, { kind: "chapter", title: "Chapter 2" });
      const c3 = await seedDocument(app, jar, project.id, { kind: "chapter", title: "Chapter 3" });
      await moveChapterToVolume(app, jar, project.id, c3.id, secondVolume.id);
      const character = await seedDocument(app, jar, project.id, {
        kind: "character",
        title: "Mara",
      });

      // The submission interleaves the two volumes; each volume keeps its own
      // submitted relative order inside that volume only — cross-volume
      // arrangement is decided by volume positions alone.
      const reordered = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/reorder`,
        { document_ids: [c3.id, c2.id, character.id, c1.id] },
      );
      expect(reordered.statusCode, reordered.body).toBe(200);
      const returned = reordered.json().documents as OrderedDocument[];
      expect(returned.map((document) => [document.id, document.position])).toEqual([
        [c2.id, 1], // first volume received [c2 before c1]
        [c1.id, 2],
        [c3.id, 1], // second volume has a single chapter at position 1
        [character.id, 1], // non-chapters stay flat outside volumes
      ]);
      expect(returned.find((document) => document.id === c1.id)?.volume_id).toBe(firstVolume.id);
      expect(returned.find((document) => document.id === c3.id)?.volume_id).toBe(secondVolume.id);
      expect(returned.find((document) => document.id === character.id)?.volume_id).toBeNull();

      const persisted = (await getProject(app, jar, project.id))
        .documents as unknown as OrderedDocument[];
      expect(persisted.map((document) => document.id)).toEqual([c2.id, c1.id, c3.id, character.id]);
    } finally {
      await app.close();
    }
  });

  it("keeps listings and exports following volume order then in-volume order", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Export Order");
      const secondVolume = await seedVolume(app, jar, project.id, "Book Two");
      // Created order is deliberately scrambled against reading order:
      // read order must be Default Volume:[A,B] then Book Two:[C,D].
      await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "B",
        content_markdown: "# B\n\nmarker-bravo",
      });
      const c = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "C",
        content_markdown: "# C\n\nmarker-charlie",
      });
      await moveChapterToVolume(app, jar, project.id, c.id, secondVolume.id);
      const seed = (await getProject(app, jar, project.id)).documents.find(
        (document) => document.kind === "chapter" && document.title === "Chapter 1",
      );
      if (seed === undefined) throw new Error("expected Chapter 1 document");
      const renamed = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/${seed.id}`,
        {
          content_markdown: "# A\n\nmarker-alpha",
          base_revision_id: seed.current_revision_id,
          title: "A",
        },
      );
      expect(renamed.statusCode, renamed.body).toBe(200);
      const d = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "D",
        content_markdown: "# D\n\nmarker-delta",
      });
      await moveChapterToVolume(app, jar, project.id, d.id, secondVolume.id);

      // Listing order follows volumes even though creation interleaved them.
      const ordered = await orderedChapters(app, jar, project.id);
      expect(ordered.map((document) => document.title)).toEqual(["A", "B", "C", "D"]);
      expect(ordered.slice(0, 2).every((document) => document.volume_id !== secondVolume.id)).toBe(
        true,
      );

      // Export assembly reads exactly the same frozen order.
      const exportJob = await call(app, jar, "POST", `/api/projects/${project.id}/exports`, {
        format: "markdown",
      });
      expect(exportJob.statusCode, exportJob.body).toBe(201);
      const jobId = (exportJob.json() as { id: string }).id;

      const jobsResponse = await call(app, jar, "GET", `/api/projects/${project.id}/jobs`);
      expect(jobsResponse.statusCode).toBe(200);
      const job = (
        jobsResponse.json().jobs as Array<{ id: string; result: Record<string, unknown> }>
      ).find((entry) => entry.id === jobId);
      const artifactId = job?.result.export_id;
      expect(artifactId).toEqual(expect.any(String));

      const download = await call(
        app,
        jar,
        "GET",
        `/api/projects/${project.id}/exports/${String(artifactId)}/download`,
      );
      expect(download.statusCode, download.body).toBe(200);
      const book = download.body;
      const marks = [
        book.indexOf("marker-alpha"),
        book.indexOf("marker-bravo"),
        book.indexOf("marker-charlie"),
        book.indexOf("marker-delta"),
      ];
      expect(marks.every((position) => position >= 0)).toBe(true);
      expect([...marks].sort((left, right) => left - right)).toEqual(marks);

      // Moving a volume later moves its chapters in every reading surface.
      const [defaultVolume] = await listVolumes(app, jar, project.id);
      if (defaultVolume === undefined) throw new Error("expected default volume");
      const reversed = await call(app, jar, "PUT", `/api/projects/${project.id}/volumes/reorder`, {
        volume_ids: [secondVolume.id, defaultVolume.id],
      });
      expect(reversed.statusCode, reversed.body).toBe(200);
      const flipped = await orderedChapters(app, jar, project.id);
      expect(flipped.map((document) => document.title)).toEqual(["C", "D", "A", "B"]);
    } finally {
      await app.close();
    }
  });
});
