import { rm } from "node:fs/promises";
import { describe, expect, it } from "vitest";

import {
  buildStudioApp,
  call,
  monotonicClock,
  ownerJar,
  seedProject,
  seedVolume,
} from "./studio_helpers.js";

describe("volume deletion project update time", () => {
  it("advances the project timestamp and restores recent-project order after deletion", async () => {
    const { app, directory } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const older = await seedProject(app, jar, "Earlier manuscript");
      const extraVolume = await seedVolume(app, jar, older.id, "Temporary volume");
      const newer = await seedProject(app, jar, "Later manuscript");
      const before = await call(app, jar, "GET", `/api/projects/${older.id}`);

      const deleted = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${older.id}/volumes/${extraVolume.id}`,
      );
      expect(deleted.statusCode, deleted.body).toBe(204);

      const after = await call(app, jar, "GET", `/api/projects/${older.id}`);
      expect(Date.parse(after.json().updated_at)).toBeGreaterThan(
        Date.parse(before.json().updated_at),
      );
      expect(after.json().documents).toEqual(before.json().documents);
      const listed = await call(app, jar, "GET", "/api/projects");
      expect(listed.json().projects.map((project: { id: string }) => project.id)).toEqual([
        older.id,
        newer.id,
      ]);

      const remaining = after.json().volumes[0];
      const refused = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${older.id}/volumes/${remaining.id}`,
      );
      expect(refused.statusCode, refused.body).toBe(422);
      const afterRefusal = await call(app, jar, "GET", `/api/projects/${older.id}`);
      expect(afterRefusal.json()).toEqual(after.json());
    } finally {
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
