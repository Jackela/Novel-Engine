import { mkdirSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { makeLegacyWorkspace } from "../legacy_workspace_fixtures.js";
import {
  anonymousCall,
  buildStudioApp,
  call,
  guestJar,
  monotonicClock,
  ownerJar,
} from "./studio_helpers.js";

const CONFINEMENT_MESSAGE = "Web imports must name a workspace directory under data/imports.";
const NOT_FOUND_MESSAGE = "Import workspace not found under data/imports.";

describe("web import confinement and guards", () => {
  it("is owner-only: guests are rejected before the source is resolved", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await guestJar(app);
      const response = await call(app, jar, "POST", "/api/imports/preview", {
        source: "legacy-story",
      });
      expect(response.statusCode, response.body).toBe(403);
      const error = response.json().error;
      expect(error.code).toBe("FORBIDDEN");
      expect(error.message).toBe("This operation requires the local Owner.");
    } finally {
      await app.close();
    }
  });

  it("requires a session", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const response = await anonymousCall(app, "POST", "/api/imports/preview", {
        source: "legacy-story",
      });
      expect(response.statusCode).toBe(401);
      expect(response.json().error.code).toBe("UNAUTHORIZED");
    } finally {
      await app.close();
    }
  });

  it("rejects separators, traversal, and dot names before any file read", async () => {
    const { app, directory } = await buildStudioApp(monotonicClock());
    try {
      makeLegacyWorkspace(join(directory, "imports", "legacy-story"), {
        title: "Imported Story",
        chapters: [{ filename: "chapter-001.md", content: "# One\n" }],
      });
      const jar = await ownerJar(app);
      for (const source of ["a/b", "a\\b", "..", ".", "../legacy-story", "/etc/passwd"]) {
        const response = await call(app, jar, "POST", "/api/imports/preview", { source });
        expect(response.statusCode, `${source}: ${response.body}`).toBe(422);
        const error = response.json().error;
        expect(error.code).toBe("INVALID_OPERATION");
        expect(error.message).toBe(CONFINEMENT_MESSAGE);
      }
    } finally {
      await app.close();
    }
  });

  it("rejects symlinked sources with not-found before reading them", async () => {
    const { app, directory } = await buildStudioApp(monotonicClock());
    try {
      // A perfectly valid workspace outside the import root; only a symlink
      // named inside data/imports points at it. Following it would import.
      const target = makeLegacyWorkspace(join(tmpdir(), `outside-${Date.now()}`), {
        title: "Stolen Story",
        chapters: [{ filename: "chapter-001.md", content: "# One\n" }],
      });
      const importsRoot = join(directory, "imports");
      mkdirSync(importsRoot, { recursive: true });
      symlinkSync(target, join(importsRoot, "sneaky"));
      const jar = await ownerJar(app);
      const response = await call(app, jar, "POST", "/api/imports/preview", { source: "sneaky" });
      expect(response.statusCode, response.body).toBe(404);
      const error = response.json().error;
      expect(error.code).toBe("NOT_FOUND");
      expect(error.message).toBe(NOT_FOUND_MESSAGE);
    } finally {
      await app.close();
    }
  });

  it("rejects unknown names and non-directory names with not-found", async () => {
    const { app, directory } = await buildStudioApp(monotonicClock());
    try {
      const importsRoot = join(directory, "imports");
      mkdirSync(importsRoot, { recursive: true });
      writeFileSync(join(importsRoot, "not-a-directory"), "text", "utf8");
      const jar = await ownerJar(app);
      for (const source of ["missing-workspace", "not-a-directory"]) {
        const response = await call(app, jar, "POST", "/api/imports/preview", { source });
        expect(response.statusCode, `${source}: ${response.body}`).toBe(404);
        expect(response.json().error.message).toBe(NOT_FOUND_MESSAGE);
      }
    } finally {
      await app.close();
    }
  });

  it("requires story.yaml inside a confined directory", async () => {
    const { app, directory } = await buildStudioApp(monotonicClock());
    try {
      mkdirSync(join(directory, "imports", "empty-story"), { recursive: true });
      const jar = await ownerJar(app);
      const response = await call(app, jar, "POST", "/api/imports/preview", {
        source: "empty-story",
      });
      expect(response.statusCode, response.body).toBe(422);
      const error = response.json().error;
      expect(error.code).toBe("INVALID_OPERATION");
      expect(error.message).toBe("Legacy workspace must contain story.yaml.");
    } finally {
      await app.close();
    }
  });
});
