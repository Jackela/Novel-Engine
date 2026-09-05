import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { LoreStatus, Project } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { useStudioActions } from "./useStudioActions";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: { ...actual.api, saveLoreStatus: vi.fn<typeof actual.api.saveLoreStatus>() },
  };
});

interface Rejectable<T> {
  readonly promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
}

function rejectable<T>(): Rejectable<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolveValue, rejectValue) => {
    resolve = resolveValue;
    reject = rejectValue;
  });
  return { promise, resolve, reject };
}

const character = chapter("character-a", {
  kind: "character",
  title: "Mara",
  lore_status: "draft",
});
const world = chapter("world-b", {
  kind: "world",
  title: "Harbor",
  lore_status: "stable",
});
const projectFixture = projectWith([character, world]);
const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderActions(initialProject: Project = projectFixture) {
  let current:
    | {
        actions: ReturnType<typeof useStudioActions>;
        project: Project | null;
        error: string | null;
      }
    | undefined;

  function Probe(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    const [error, setError] = useState<string | null>("Previous error.");
    const actions = useStudioActions({
      project,
      projectId: initialProject.id,
      setProject,
      setReviewPage: vi.fn(),
      setError,
      setActiveId: vi.fn(),
      settingsForm: {
        title: initialProject.title,
        description: initialProject.description,
        provider: "mock",
      },
      loadJobs: vi.fn().mockResolvedValue(undefined),
    });
    current = { actions, project, error };
    return null;
  }

  const mounted = harness.mount(<Probe />);
  return {
    ...mounted,
    result: () => {
      if (current === undefined) throw new Error("Expected Studio actions.");
      return current;
    },
  };
}

function renderObservedActions() {
  let current: ReturnType<typeof useStudioActions> | undefined;
  const setProject = vi.fn();
  const setError = vi.fn();

  function Probe({ value }: { value: Project }): null {
    current = useStudioActions({
      project: value,
      projectId: value.id,
      setProject,
      setReviewPage: vi.fn(),
      setError,
      setActiveId: vi.fn(),
      settingsForm: { title: value.title, description: value.description, provider: "mock" },
      loadJobs: vi.fn().mockResolvedValue(undefined),
    });
    return null;
  }

  const mounted = harness.mount(<Probe value={projectFixture} />);
  return {
    ...mounted,
    Probe,
    setProject,
    setError,
    result: () => {
      if (current === undefined) throw new Error("Expected Studio actions.");
      return current;
    },
  };
}

describe("useStudioActions Lore document identity", () => {
  it("keeps document A's pending and failure state off B, then restores it for A", async () => {
    const request = rejectable<{ lore_status: LoreStatus }>();
    vi.mocked(api.saveLoreStatus).mockReturnValue(request.promise);
    const view = renderActions();
    let save!: Promise<void>;

    act(() => {
      save = view.result().actions.changeLoreStatus(character.id, "stable");
    });

    expect(view.result().actions.loreStatusFor(character.id)).toEqual({
      isSaving: true,
      error: null,
      attemptedStatus: "stable",
    });
    expect(view.result().actions.loreStatusFor(world.id)).toEqual({
      isSaving: false,
      error: null,
      attemptedStatus: null,
    });

    await act(async () => {
      request.reject(new Error("Mara status was rejected."));
      await save;
    });

    expect(view.result().actions.loreStatusFor(world.id).error).toBeNull();
    expect(view.result().actions.loreStatusFor(character.id)).toEqual({
      isSaving: false,
      error: "Mara status was rejected.",
      attemptedStatus: "stable",
    });
    expect(view.result().error).toBeNull();
  });

  it("deduplicates same-document saves before React can render pending state", async () => {
    const request = rejectable<{ lore_status: LoreStatus }>();
    vi.mocked(api.saveLoreStatus).mockReturnValue(request.promise);
    const view = renderActions();
    let first!: Promise<void>;
    let duplicate!: Promise<void>;

    act(() => {
      first = view.result().actions.changeLoreStatus(character.id, "stable");
      duplicate = view.result().actions.changeLoreStatus(character.id, "deprecated");
    });

    expect(api.saveLoreStatus).toHaveBeenCalledTimes(1);

    await act(async () => {
      request.resolve({ lore_status: "stable" });
      await Promise.all([first, duplicate]);
    });
  });

  it("patches concurrent document results by origin even when B finishes before A", async () => {
    const characterRequest = rejectable<{ lore_status: LoreStatus }>();
    const worldRequest = rejectable<{ lore_status: LoreStatus }>();
    vi.mocked(api.saveLoreStatus).mockImplementation((_projectId, documentId) =>
      documentId === character.id ? characterRequest.promise : worldRequest.promise,
    );
    const view = renderActions();
    let saveCharacter!: Promise<void>;
    let saveWorld!: Promise<void>;

    act(() => {
      saveCharacter = view.result().actions.changeLoreStatus(character.id, "stable");
      saveWorld = view.result().actions.changeLoreStatus(world.id, "deprecated");
    });

    expect(view.result().actions.loreStatusFor(character.id).isSaving).toBe(true);
    expect(view.result().actions.loreStatusFor(world.id).isSaving).toBe(true);

    await act(async () => {
      worldRequest.resolve({ lore_status: "deprecated" });
      await saveWorld;
    });

    expect(view.result().actions.loreStatusFor(character.id).isSaving).toBe(true);
    expect(view.result().project?.documents?.find(({ id }) => id === world.id)?.lore_status).toBe(
      "deprecated",
    );
    expect(
      view.result().project?.documents?.find(({ id }) => id === character.id)?.lore_status,
    ).toBe("draft");

    await act(async () => {
      characterRequest.resolve({ lore_status: "stable" });
      await saveCharacter;
    });

    expect(
      view.result().project?.documents?.find(({ id }) => id === character.id)?.lore_status,
    ).toBe("stable");
    expect(view.result().project?.documents?.find(({ id }) => id === world.id)?.lore_status).toBe(
      "deprecated",
    );
  });

  it.each(["project switch", "unmount"] as const)(
    "does not publish a late Lore result after %s",
    async (transition) => {
      const request = rejectable<{ lore_status: LoreStatus }>();
      vi.mocked(api.saveLoreStatus).mockReturnValue(request.promise);
      const view = renderObservedActions();
      let save!: Promise<void>;

      act(() => {
        save = view.result().changeLoreStatus(character.id, "stable");
      });
      view.setProject.mockClear();
      view.setError.mockClear();

      if (transition === "project switch") {
        const nextProject = projectWith([], { id: "project-2", title: "Second project" });
        act(() => {
          view.root.render(<view.Probe value={nextProject} />);
        });
      } else {
        harness.unmount(view.container);
      }

      await act(async () => {
        request.reject(new Error("Late Lore failure."));
        await save;
      });

      expect(view.setProject).not.toHaveBeenCalled();
      expect(view.setError).not.toHaveBeenCalled();
    },
  );
});
