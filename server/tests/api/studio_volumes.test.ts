import { describe, expect, it } from "vitest";

import {
  buildStudioApp,
  call,
  getProject,
  listVolumes,
  monotonicClock,
  ownerJar,
  placeDocument,
  seedDocument,
  seedProject,
  seedVolume,
} from "./studio_helpers.js";

describe("volume hierarchy", () => {
  it("creates a project with a seeded default volume holding its chapters", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Volume Seed");

      const listed = await listVolumes(app, jar, project.id);
      expect(listed).toHaveLength(1);
      expect(listed[0]).toMatchObject({
        project_id: project.id,
        title: "Default Volume",
        position: 1,
      });

      // The detail payload carries the volume structure alongside documents.
      const detail = await getProject(app, jar, project.id);
      expect((detail as unknown as { volumes: typeof listed }).volumes).toEqual(listed);
      expect(detail.documents[0]?.kind).toBe("chapter");
      expect(detail.documents[0]?.volume_id).toBe(listed[0]?.id);
    } finally {
      await app.close();
    }
  });

  it("creates and renames volumes through the project surface", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Three Volumes");
      const second = await seedVolume(app, jar, project.id, "Act Two");
      expect(second.position).toBe(2);

      const renamed = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/volumes/${second.id}`,
        { title: "Act Two, Revised" },
      );
      expect(renamed.statusCode, renamed.body).toBe(200);
      expect(renamed.json().title).toBe("Act Two, Revised");

      const listed = await listVolumes(app, jar, project.id);
      expect(listed.map((volume) => volume.title)).toEqual(["Default Volume", "Act Two, Revised"]);
    } finally {
      await app.close();
    }
  });

  it("answers principal-safe not-found and auth errors on the volume surface", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Not Found");

      const anonymousCreate = await app.inject({
        method: "POST",
        url: `/api/projects/${project.id}/volumes`,
        payload: { title: "No Principal" },
      });
      expect(anonymousCreate.statusCode).toBe(401);
      expect(anonymousCreate.json().error.code).toBe("UNAUTHORIZED");

      const unknownProject = await call(
        app,
        jar,
        "POST",
        "/api/projects/00000000-0000-0000-0000-000000000000/volumes",
        { title: "Nowhere" },
      );
      expect(unknownProject.statusCode).toBe(404);
      expect(unknownProject.json().error.code).toBe("NOT_FOUND");

      const unknownRename = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/volumes/missing-volume`,
        { title: "Ghost" },
      );
      expect(unknownRename.statusCode).toBe(404);

      const unknownDelete = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${project.id}/volumes/missing-volume`,
      );
      expect(unknownDelete.statusCode).toBe(404);

      const document = (await getProject(app, jar, project.id)).documents[0]!;
      const unknownTarget = await placeDocument(
        app,
        jar,
        project.id,
        document.id,
        "missing-volume",
      );
      expect(unknownTarget.status).toBe(404);
    } finally {
      await app.close();
    }
  });

  it("refuses to delete the last remaining volume", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Last One");
      const [only] = await listVolumes(app, jar, project.id);

      const refused = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${project.id}/volumes/${only!.id}`,
      );
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.code).toBe("INVALID_OPERATION");
      expect(refused.json().error.message).toContain("at least one volume");

      // Nothing moved or vanished: the refused delete changed no state.
      const after = await listVolumes(app, jar, project.id);
      expect(after).toEqual([only]);
    } finally {
      await app.close();
    }
  });

  it("moves a deleted volume's chapters into the preceding volume (else the following)", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Merge On Delete");
      const [defaultVolume] = await listVolumes(app, jar, project.id);
      const tailOf = async (volumeId: string): Promise<Array<{ id: string }>> =>
        ((await getProject(app, jar, project.id)).documents ?? [])
          .filter((document) => document.volume_id === volumeId)
          .map((document) => ({ id: document.id }));

      const beta = await seedVolume(app, jar, project.id, "Beta");
      const gamma = await seedVolume(app, jar, project.id, "Gamma");
      const betaChapterId = (
        await seedDocument(app, jar, project.id, { kind: "chapter", title: "Beta Chapter" })
      ).id;
      await moveInto(beta.id, betaChapterId);
      await moveInto(
        gamma.id,
        (await seedDocument(app, jar, project.id, { kind: "chapter", title: "Gamma One" })).id,
      );
      await moveInto(
        gamma.id,
        (await seedDocument(app, jar, project.id, { kind: "chapter", title: "Gamma Two" })).id,
      );

      async function moveInto(volumeId: string, documentId: string): Promise<void> {
        const attempt = await placeDocument(app, jar, project.id, documentId, volumeId);
        expect(attempt.status, JSON.stringify(attempt)).toBe(200);
      }

      // Gamma's predecessor by reading order is Beta: deleting Gamma merges
      // its chapters into Beta and leaves the default volume untouched.
      const removed = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${project.id}/volumes/${gamma.id}`,
      );
      expect(removed.statusCode).toBe(204);
      let survivors = await listVolumes(app, jar, project.id);
      expect(survivors.map((volume) => volume.title)).toEqual(["Default Volume", "Beta"]);
      const defaultTailBeforeSecondDelete = await tailOf(defaultVolume!.id);

      // Now delete the FIRST volume while others remain: no predecessor
      // exists, so its chapters merge into the FOLLOWING volume at the tail.
      const removedAgain = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${project.id}/volumes/${defaultVolume!.id}`,
      );
      expect(removedAgain.statusCode).toBe(204);
      survivors = await listVolumes(app, jar, project.id);
      expect(survivors.map((volume) => volume.title)).toEqual(["Beta"]);

      const mergedTail = await tailOf(survivors[0]!.id);
      const movedIds = mergedTail.map((document) => document.id);
      expect(movedIds).toContain(betaChapterId);
      const firstMergedId = defaultTailBeforeSecondDelete[0]!.id;
      expect(movedIds.slice(movedIds.indexOf(firstMergedId))).toEqual(
        defaultTailBeforeSecondDelete.map((document) => document.id),
      );
    } finally {
      await app.close();
    }
  });

  it("refuses moving non-chapter documents between volumes", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Chapters Only");
      const outline = await seedDocument(app, jar, project.id, { kind: "outline", title: "Arc" });
      const [volume] = await listVolumes(app, jar, project.id);

      const attempt = await placeDocument(app, jar, project.id, outline.id, volume!.id);
      expect(attempt.status).toBe(422);
      const documents = (await getProject(app, jar, project.id)).documents;
      expect(
        documents.find((document) => document.id === outline.id)?.volume_id ?? null,
      ).toBeNull();
    } finally {
      await app.close();
    }
  });

  it("reorders volumes and refuses partial or duplicated sets", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Volume Order");
      const alpha = (await listVolumes(app, jar, project.id))[0]!;
      const beta = await seedVolume(app, jar, project.id, "Beta");
      const gamma = await seedVolume(app, jar, project.id, "Gamma");

      const reordered = await call(app, jar, "PUT", `/api/projects/${project.id}/volumes/reorder`, {
        volume_ids: [gamma.id, alpha.id, beta.id],
      });
      expect(reordered.statusCode, reordered.body).toBe(200);
      const listed = reordered.json().volumes;
      expect(listed.map((volume: { id: string }) => volume.id)).toEqual([
        gamma.id,
        alpha.id,
        beta.id,
      ]);
      expect(listed.map((volume: { position: number }) => volume.position)).toEqual([1, 2, 3]);

      const partial = await call(app, jar, "PUT", `/api/projects/${project.id}/volumes/reorder`, {
        volume_ids: [alpha.id],
      });
      expect(partial.statusCode).toBe(422);
      expect(partial.json().error.code).toBe("INVALID_OPERATION");

      const duplicated = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/volumes/reorder`,
        { volume_ids: [alpha.id, alpha.id, beta.id] },
      );
      expect(duplicated.statusCode).toBe(422);
    } finally {
      await app.close();
    }
  });
});
