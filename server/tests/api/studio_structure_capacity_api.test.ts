import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import {
  STRUCTURE_CAPACITY_LIMITS,
  StructureCapacityExceededError,
} from "../../src/contexts/studio/domain/structure_capacity.js";
import { withStudioErrors } from "../../src/contexts/studio/interface/http/studio_error_mapping.js";
import { AppError } from "../../src/shared/interface/http/error_envelope.js";
import { firstVolumeId, seedChapterRows } from "./structure_capacity_seed_helpers.js";
import {
  buildStudioApp,
  call,
  getDocument,
  getProject,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

/**
 * Count-capacity contract (#461): document, volume, and per-volume chapter
 * budgets refuse the overflowing write with the stable 422 envelope and no
 * partial rows. Large populations are seeded directly through the live
 * Studio database (the export-capacity test pattern), never through N HTTP
 * calls.
 */
describe("authoring structure count capacity", () => {
  it("maps the refusal to the stable 422 envelope without a retry hint", () => {
    let mapped: unknown;
    try {
      withStudioErrors(() => {
        throw new StructureCapacityExceededError("project_documents", 2_500, 9_999);
      });
    } catch (error) {
      mapped = error;
    }
    expect(mapped).toBeInstanceOf(AppError);
    expect(mapped).toMatchObject({
      statusCode: 422,
      code: "STRUCTURE_CAPACITY_EXCEEDED",
      message: "Authoring structure capacity exceeded.",
      details: {
        resource: "project_documents",
        limit: STRUCTURE_CAPACITY_LIMITS.project_documents,
        observed: STRUCTURE_CAPACITY_LIMITS.project_documents + 1,
      },
      responseHeaders: undefined,
    });
  });

  it("admits the 2,500th document and refuses the 2,501st without partial writes", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Document capacity");
      const firstVolume = firstVolumeId(app, project.id);
      // Seed chapters across two volumes so neither volume crosses its own
      // 2,000-chapter budget: the project limit, not the volume limit, is the
      // boundary under test. 1 (seed) + 1,998 + 500 = 2,499 documents.
      const second = await call(app, owner, "POST", `/api/projects/${project.id}/volumes`, {
        title: "Overflow",
      });
      const secondVolume: string = second.json().id;
      seedChapterRows(app, project.id, firstVolume, STRUCTURE_CAPACITY_LIMITS.volume_chapters - 2);
      seedChapterRows(
        app,
        project.id,
        secondVolume,
        STRUCTURE_CAPACITY_LIMITS.project_documents -
          1 -
          (STRUCTURE_CAPACITY_LIMITS.volume_chapters - 2) -
          1,
      );

      const atLimit = await call(app, owner, "POST", `/api/projects/${project.id}/documents`, {
        kind: "chapter",
        title: "At Limit",
      });
      expect(atLimit.statusCode).toBe(201);

      const overLimit = await call(app, owner, "POST", `/api/projects/${project.id}/documents`, {
        kind: "character",
        title: "Over Limit",
      });
      expect(overLimit.statusCode).toBe(422);
      expect(overLimit.json()).toEqual({
        error: {
          code: "STRUCTURE_CAPACITY_EXCEEDED",
          message: "Authoring structure capacity exceeded.",
          details: {
            resource: "project_documents",
            limit: STRUCTURE_CAPACITY_LIMITS.project_documents,
            observed: STRUCTURE_CAPACITY_LIMITS.project_documents + 1,
          },
        },
      });

      const shell = await getProject(app, owner, project.id);
      expect(shell.documents).toHaveLength(STRUCTURE_CAPACITY_LIMITS.project_documents);
    } finally {
      await app.close();
    }
  }, 60_000);

  it("admits the 100th volume and refuses the 101st", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Volume capacity");
      for (let index = 2; index <= STRUCTURE_CAPACITY_LIMITS.project_volumes; index += 1) {
        const created = await call(app, owner, "POST", `/api/projects/${project.id}/volumes`, {
          title: `Volume ${index}`,
        });
        expect(created.statusCode, `volume ${index}`).toBe(201);
      }
      const refused = await call(app, owner, "POST", `/api/projects/${project.id}/volumes`, {
        title: "Volume 101",
      });
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.details).toEqual({
        resource: "project_volumes",
        limit: STRUCTURE_CAPACITY_LIMITS.project_volumes,
        observed: STRUCTURE_CAPACITY_LIMITS.project_volumes + 1,
      });
      const list = await call(app, owner, "GET", `/api/projects/${project.id}/volumes`);
      expect(list.json().volumes).toHaveLength(STRUCTURE_CAPACITY_LIMITS.project_volumes);
    } finally {
      await app.close();
    }
  }, 60_000);

  it("refuses chapter creation into a full volume", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Volume chapter capacity");
      const defaultVolume = firstVolumeId(app, project.id);
      // The seeded Chapter 1 already occupies the default volume: seed to the
      // exact inclusive boundary before attempting one more chapter.
      seedChapterRows(
        app,
        project.id,
        defaultVolume,
        STRUCTURE_CAPACITY_LIMITS.volume_chapters - 1,
      );

      const refused = await call(app, owner, "POST", `/api/projects/${project.id}/documents`, {
        kind: "chapter",
        title: "One Too Many",
      });
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.details).toEqual({
        resource: "volume_chapters",
        limit: STRUCTURE_CAPACITY_LIMITS.volume_chapters,
        observed: STRUCTURE_CAPACITY_LIMITS.volume_chapters + 1,
      });
      const shell = await getProject(app, owner, project.id);
      expect(
        shell.documents.filter((document) => document.volume_id === defaultVolume),
      ).toHaveLength(STRUCTURE_CAPACITY_LIMITS.volume_chapters);
    } finally {
      await app.close();
    }
  }, 60_000);

  it("refuses a volume deletion whose chapter merge would overflow the survivor", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Merge capacity");
      const doomed = firstVolumeId(app, project.id);
      const survivor = await call(app, owner, "POST", `/api/projects/${project.id}/volumes`, {
        title: "Survivor",
      });
      const survivorId: string = survivor.json().id;
      // 1 (seeded) + 1,499 = 1,500 in the doomed volume; 600 in the survivor.
      seedChapterRows(app, project.id, doomed, 1_499);
      seedChapterRows(app, project.id, survivorId, 600);

      const refused = await call(
        app,
        owner,
        "DELETE",
        `/api/projects/${project.id}/volumes/${doomed}`,
      );
      expect(refused.statusCode).toBe(422);
      expect(refused.json().error.details).toEqual({
        resource: "volume_chapters",
        limit: STRUCTURE_CAPACITY_LIMITS.volume_chapters,
        observed: STRUCTURE_CAPACITY_LIMITS.volume_chapters + 1,
      });
      const volumesAfter = await call(app, owner, "GET", `/api/projects/${project.id}/volumes`);
      expect(volumesAfter.json().volumes).toHaveLength(2);
      const shell = await getProject(app, owner, project.id);
      expect(shell.documents.filter((d) => d.volume_id === doomed)).toHaveLength(1_500);
      expect(shell.documents.filter((d) => d.volume_id === survivorId)).toHaveLength(600);
    } finally {
      await app.close();
    }
  }, 60_000);

  it("refuses chapter placement into a full volume but admits the empty one", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Placement capacity");
      const defaultVolume = firstVolumeId(app, project.id);
      const second = await call(app, owner, "POST", `/api/projects/${project.id}/volumes`, {
        title: "Second",
      });
      const secondVolumeId: string = second.json().id;
      const movable = await seedDocument(app, owner, project.id, {
        kind: "chapter",
        title: "Movable",
        content_markdown: "body",
      });
      // Fill the default volume past its own budget via raw rows: Chapter 1
      // and Movable occupy two slots, so after Movable moves out the default
      // volume sits exactly at the inclusive limit and taking Movable back
      // would overflow it.
      seedChapterRows(
        app,
        project.id,
        defaultVolume,
        STRUCTURE_CAPACITY_LIMITS.volume_chapters - 1,
      );
      const intoSecond = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/${movable.id}/volume`,
        { volume_id: secondVolumeId },
      );
      expect(intoSecond.statusCode).toBe(200);
      expect(intoSecond.json().volume_id).toBe(secondVolumeId);

      const intoFull = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/${movable.id}/volume`,
        { volume_id: defaultVolume },
      );
      expect(intoFull.statusCode).toBe(422);
      expect(intoFull.json().error.details).toEqual({
        resource: "volume_chapters",
        limit: STRUCTURE_CAPACITY_LIMITS.volume_chapters,
        observed: STRUCTURE_CAPACITY_LIMITS.volume_chapters + 1,
      });
      const reread = await getDocument(app, owner, project.id, movable.id);
      expect(reread.volume_id).toBe(secondVolumeId);
    } finally {
      await app.close();
    }
  }, 60_000);

  it("documents the 422 capacity envelope on every gated structure route", async () => {
    const app = await buildApp({ logger: false });
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const gated = [
        ["post", "/api/projects/{projectId}/documents"],
        ["put", "/api/projects/{projectId}/documents/{documentId}"],
        ["put", "/api/projects/{projectId}/documents/{documentId}/volume"],
        ["post", "/api/projects/{projectId}/documents/{documentId}/revisions/{revisionId}/restore"],
        ["post", "/api/projects/{projectId}/ai-proposals/{jobId}/accept"],
        ["patch", "/api/projects/{projectId}"],
        ["post", "/api/projects/{projectId}/volumes"],
        ["delete", "/api/projects/{projectId}/volumes/{volumeId}"],
      ] as const;
      for (const [method, path] of gated) {
        const operation = document.paths[path][method];
        const serialized = JSON.stringify(operation.responses["422"]);
        expect(serialized, `${method} ${path}`).toContain("STRUCTURE_CAPACITY_EXCEEDED");
      }
    } finally {
      await app.close();
    }
  });
});
