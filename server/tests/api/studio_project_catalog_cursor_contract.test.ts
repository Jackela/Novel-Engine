import { describe, expect, it } from "vitest";

import {
  decodeProjectCatalogCursor,
  encodeProjectCatalogCursor,
} from "../../src/contexts/studio/interface/http/project_catalog_cursor.js";
import { buildStudioApp, call, monotonicClock, ownerJar, seedProject } from "./studio_helpers.js";

interface Statement {
  query: string;
  params: unknown[];
}

describe("project catalog cursor contract", () => {
  it("round-trips only canonical owner-bound cursor positions", () => {
    const token = encodeProjectCatalogCursor("owner-a", {
      updatedAtMs: 1_725_000_000_123,
      id: "project-a",
    });
    expect(token).toBe("WzEsIm93bmVyLWEiLDE3MjUwMDAwMDAxMjMsInByb2plY3QtYSJd");
    expect(decodeProjectCatalogCursor(token ?? "", "owner-a")).toEqual({
      updatedAtMs: 1_725_000_000_123,
      id: "project-a",
    });

    const invalidTokens = [
      "not+base64url",
      Buffer.from('[1, "owner-a", 1, "project-a"]', "utf8").toString("base64url"),
      Buffer.from('[1,"owner-a",1e0,"project-a"]', "utf8").toString("base64url"),
      Buffer.from('[1,"owner\\u002da",1,"project-a"]', "utf8").toString("base64url"),
      Buffer.from(JSON.stringify([2, "owner-a", 1, "project-a"])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "owner-a", -1, "project-a"])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "owner-a", 1, ""])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "owner-a", 1, "x".repeat(129)])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "owner-a", 1, "project-a", "extra"])).toString("base64url"),
    ];
    for (const invalid of invalidTokens) {
      expect(() => decodeProjectCatalogCursor(invalid, "owner-a")).toThrowError(
        expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
      );
    }
    expect(() => decodeProjectCatalogCursor(token ?? "", "owner-b")).toThrowError(
      expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
    );
  });

  it("rejects invalid cursors before any catalog read", async () => {
    const statements: Statement[] = [];
    const { app } = await buildStudioApp(monotonicClock(), {
      databaseQueryLogger: {
        logQuery: (query, params) => statements.push({ query, params }),
      },
    });
    try {
      const owner = await ownerJar(app);
      await seedProject(app, owner, "Cursor scope");
      const crossOwner = encodeProjectCatalogCursor("another-owner", {
        updatedAtMs: 1,
        id: "project-a",
      });
      const unknownVersion = Buffer.from(
        JSON.stringify([2, "current-owner", 1, "project-a"]),
      ).toString("base64url");

      for (const cursor of [crossOwner ?? "", unknownVersion, "a".repeat(1025)]) {
        statements.length = 0;
        const response = await call(
          app,
          owner,
          "GET",
          `/api/projects?cursor=${encodeURIComponent(cursor)}`,
        );
        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
        expect(response.json().error.details.errors[0].field).toBe("cursor");
        expect(statements.some(({ query }) => query.includes('"projects"'))).toBe(false);
      }
    } finally {
      await app.close();
    }
  });
});
