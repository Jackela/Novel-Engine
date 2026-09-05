import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Studio project API client", () => {
  it("patches only supplied project fields and parses the scalar response", async () => {
    const response = {
      id: "project-1",
      title: "Renamed",
      description: "Kept by the server",
      settings: { provider: "mock" },
      import_hash: null,
      created_at: "2026-09-03T00:00:00Z",
      updated_at: "2026-09-03T00:00:00.001Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.updateProject("project-1", { title: "Renamed" })).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ title: "Renamed" }),
      }),
    );
  });

  it("rejects a body-bearing project PATCH response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "project-1",
            title: "Renamed",
            description: "",
            settings: {},
            import_hash: null,
            created_at: "2026-09-03T00:00:00Z",
            updated_at: "2026-09-03T00:00:00.001Z",
            documents: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(api.updateProject("project-1", { settings: {} })).rejects.toThrow(
      "Invalid project list item keys",
    );
  });

  it("uses the project contract and includes cookies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ projects: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.projects()).resolves.toEqual({ projects: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("rejects project payloads that do not match the API contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ projects: [{ id: "p1" }] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const error = await api.projects().catch((reason: unknown) => reason);
    expect(error).toMatchObject({ message: "Invalid projects[0].title" });
  });
});
