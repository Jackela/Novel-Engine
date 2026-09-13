import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { ProjectCatalogItem, Session } from "@/app/types/studio";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { useProjectLibraryBootstrap } from "./useProjectLibraryBootstrap";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      session: vi.fn<typeof actual.api.session>(),
      projects: vi.fn<typeof actual.api.projects>(),
    },
  };
});

const harness = createMountHarness();
const session: Session = {
  session_id: "session-1",
  kind: "owner",
  owner_id: "owner-1",
  expires_at: null,
};

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function catalogItem(id: string): ProjectCatalogItem {
  return { id, title: `Project ${id}`, description: "", created_at: "", updated_at: "" };
}

function renderBootstrap() {
  let current: ReturnType<typeof useProjectLibraryBootstrap> | undefined;
  const onUnauthenticated = vi.fn();

  function Probe(): null {
    current = useProjectLibraryBootstrap(onUnauthenticated);
    return null;
  }

  harness.mount(<Probe />);
  return {
    result: () => {
      if (!current) throw new Error("Expected project library bootstrap hook result.");
      return current;
    },
    onUnauthenticated,
  };
}

describe("useProjectLibraryBootstrap", () => {
  it("settles the first-page busy flag when an older request races an in-flight reload", async () => {
    vi.mocked(api.session).mockResolvedValueOnce(session);
    vi.mocked(api.projects).mockResolvedValueOnce({
      projects: [catalogItem("project-1")],
      next_cursor: "cursor-1",
    });
    const mounted = renderBootstrap();
    await flushEffects();
    expect(mounted.result().isLoading).toBe(false);
    expect(mounted.result().nextCursor).toBe("cursor-1");

    // A loadOlder closure captured before the retry must not strand the
    // first-page busy flag: reload keeps its request currency and the busy
    // cleanup lands even for a superseded read.
    const staleLoadOlder = mounted.result().loadOlder;
    const retrySession = deferred<Session>();
    vi.mocked(api.session).mockReturnValueOnce(retrySession.promise);
    vi.mocked(api.projects).mockResolvedValueOnce({
      projects: [catalogItem("project-2"), catalogItem("project-1")],
      next_cursor: null,
    });
    let reloadPromise!: Promise<void>;
    act(() => {
      reloadPromise = mounted.result().reload();
    });
    await act(async () => {
      await staleLoadOlder();
    });
    await act(async () => {
      retrySession.resolve(session);
      await reloadPromise;
    });

    expect(mounted.result().isLoading).toBe(false);
    expect(mounted.result().projects.map((item) => item.id)).toEqual(["project-2", "project-1"]);
    expect(api.projects).toHaveBeenCalledTimes(2);
  });
});
