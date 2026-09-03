import { act } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project } from "@/app/types/studio";
import { project } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";

import { useStudioProject } from "./useStudioProject";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn<typeof actual.api.project>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderProject(projectValue: Project) {
  let current: ReturnType<typeof useStudioProject> | undefined;
  vi.mocked(api.project).mockResolvedValue(projectValue);
  vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
  vi.mocked(api.exports).mockResolvedValue({ exports: [] });

  function Probe(): null {
    current = useStudioProject(projectValue.id);
    return null;
  }
  harness.mount(
    <MemoryRouter>
      <Probe />
    </MemoryRouter>,
  );
  return () => current;
}

describe("useStudioProject shell authority", () => {
  it("rejects a shell read captured before a local shell mutation", async () => {
    const initial = project({ id: "project-1", title: "Initial title" });
    const result = renderProject(initial);
    await flushEffects();
    const capture = result()?.captureProjectShellRead();
    expect(capture).toBeDefined();

    act(() =>
      result()?.setProject((current) =>
        current ? { ...current, title: "Locally committed title" } : current,
      ),
    );
    let published = true;
    act(() => {
      if (capture)
        published =
          result()?.publishProjectShellRead(capture, {
            ...initial,
            title: "Stale read title",
          }) ?? true;
    });

    expect(published).toBe(false);
    expect(result()?.project?.title).toBe("Locally committed title");
  });
});
