import { afterEach, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
it("sends the CLI permission option with owner credentials and CSRF", async () => {
  vi.spyOn(document, "cookie", "get").mockReturnValue("novel_engine_csrf=test-csrf");
  const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetcher);
  const controller = new AbortController();
  await api.respondAiPermission("project", "operation", "permission", "allow-session", {
    signal: controller.signal,
  });
  expect(fetcher).toHaveBeenCalledWith(
    "/api/projects/project/ai-operations/operation/permissions/permission",
    expect.objectContaining({
      method: "POST",
      credentials: "include",
      headers: expect.objectContaining({ "X-CSRF-Token": "test-csrf" }),
      body: '{"option_id":"allow-session"}',
      signal: expect.any(AbortSignal),
    }),
  );
});
