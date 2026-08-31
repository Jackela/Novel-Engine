import { describe, expect, it } from "vitest";

import { resolveStudioRoute, studioInspectorPath } from "./studioRouteState";

describe("Studio route state", () => {
  it("derives route-owned and local Inspector selections from the URL", () => {
    expect(resolveStudioRoute("project 1", "review", "?inspector=jobs")).toEqual({
      section: "review",
      inspector: "review",
      canonicalPath: "/projects/project%201/review",
    });
    expect(resolveStudioRoute("project 1", "outline", "?inspector=jobs")).toEqual({
      section: "outline",
      inspector: "jobs",
      canonicalPath: "/projects/project%201/outline?inspector=jobs",
    });
  });

  it("fails closed to canonical Manuscript and Copilot routes", () => {
    expect(resolveStudioRoute("project-1", "unknown", "?inspector=usage")).toEqual({
      section: "manuscript",
      inspector: "copilot",
      canonicalPath: "/projects/project-1/manuscript",
    });
    expect(resolveStudioRoute("project-1", "world", "?inspector=review")).toEqual({
      section: "world",
      inspector: "copilot",
      canonicalPath: "/projects/project-1/world",
    });
    expect(resolveStudioRoute("project-1", "characters", "?inspector=copilot")).toEqual({
      section: "characters",
      inspector: "copilot",
      canonicalPath: "/projects/project-1/characters",
    });
  });

  it("builds route-owned and local Inspector destinations", () => {
    expect(studioInspectorPath("project-1", "outline", "review")).toBe(
      "/projects/project-1/review",
    );
    expect(studioInspectorPath("project-1", "outline", "jobs")).toBe(
      "/projects/project-1/outline?inspector=jobs",
    );
    expect(studioInspectorPath("project-1", "history", "usage")).toBe(
      "/projects/project-1/manuscript?inspector=usage",
    );
    expect(studioInspectorPath("project-1", "export", "copilot")).toBe(
      "/projects/project-1/manuscript",
    );
  });
});
