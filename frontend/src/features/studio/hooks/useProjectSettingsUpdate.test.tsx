import { act, type FormEvent, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Project, ProjectListItem } from "@/app/types/studio";
import { project as projectFixture, volume } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";
import type { SettingsFormState } from "../studioInspectorTypes";
import { useProjectSettingsUpdate } from "./useProjectSettingsUpdate";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: { ...actual.api, updateProject: vi.fn<typeof actual.api.updateProject>() },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function scalar(project: Project, overrides: Partial<ProjectListItem> = {}): ProjectListItem {
  const { documents: _documents, volumes: _volumes, ...item } = project;
  return { ...item, ...overrides };
}

function renderSettings(projectValue = projectFixture()) {
  let current:
    | {
        project: Project | null;
        form: SettingsFormState;
        error: string | null;
        mutation: ReturnType<typeof useProjectSettingsUpdate>;
        setForm: React.Dispatch<React.SetStateAction<SettingsFormState>>;
      }
    | undefined;
  const onSessionLost = vi.fn();
  const onProjectMissing = vi.fn();

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(projectValue);
    const [form, setForm] = useState<SettingsFormState>({
      title: projectValue.title,
      description: projectValue.description,
      provider: String(projectValue.settings.provider ?? "mock"),
    });
    const [error, setError] = useState<string | null>(null);
    current = {
      project,
      form,
      error,
      setForm,
      mutation: useProjectSettingsUpdate({
        project,
        projectId: projectValue.id,
        settingsForm: form,
        setProject,
        setSettingsForm: setForm,
        setSettingsError: setError,
        onSessionLost,
        onProjectMissing,
      }),
    };
    return null;
  }

  const mounted = harness.mount(<Wrapper />);
  const result = () => {
    if (current === undefined) throw new Error("Expected settings mutation result.");
    return current;
  };
  const submit = () =>
    result().mutation.updateProjectSettings({
      preventDefault: vi.fn(),
    } as unknown as FormEvent);
  return { mounted, onProjectMissing, onSessionLost, result, submit };
}

describe("useProjectSettingsUpdate", () => {
  it("merges only mutable scalars and synchronizes the form", async () => {
    const original = projectFixture({
      import_hash: "immutable-import",
      settings: { provider: "mock", temperature: 0.3 },
      volumes: [volume("volume-1", 0)],
    });
    const view = renderSettings(original);
    act(() => {
      view.result().setForm({
        title: "Updated Harbor",
        description: "Updated description",
        provider: "dashscope",
      });
    });
    vi.mocked(api.updateProject).mockResolvedValue(
      scalar(original, {
        id: original.id,
        title: "Updated Harbor",
        description: "Updated description",
        settings: { provider: "dashscope", temperature: 0.3 },
        import_hash: "hostile-response-import",
        created_at: "hostile-response-created-at",
        updated_at: "2026-09-03T00:00:00.001Z",
      }),
    );

    await act(view.submit);

    expect(view.result().project).toEqual({
      ...original,
      title: "Updated Harbor",
      description: "Updated description",
      settings: { provider: "dashscope", temperature: 0.3 },
      updated_at: "2026-09-03T00:00:00.001Z",
    });
    expect(view.result().form).toEqual({
      title: "Updated Harbor",
      description: "Updated description",
      provider: "dashscope",
    });
    expect(view.result().error).toBeNull();
    expect(view.result().mutation.isUpdatingSettings).toBe(false);
    expect(api.updateProject).toHaveBeenCalledWith(
      original.id,
      {
        title: "Updated Harbor",
        description: "Updated description",
        settings: { provider: "dashscope", temperature: 0.3 },
      },
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("lets a newer changed intent win when responses settle in reverse", async () => {
    const first = deferred<ProjectListItem>();
    const second = deferred<ProjectListItem>();
    vi.mocked(api.updateProject)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const original = projectFixture({ settings: { provider: "mock", retained: true } });
    const view = renderSettings(original);

    act(() => {
      view.result().setForm({ title: "First", description: "First", provider: "mock" });
    });
    let firstSave!: Promise<void>;
    act(() => {
      firstSave = view.submit();
    });
    act(() => {
      view.result().setForm({ title: "Second", description: "Second", provider: "dashscope" });
    });
    let secondSave!: Promise<void>;
    act(() => {
      secondSave = view.submit();
    });

    await act(async () => {
      second.resolve(
        scalar(original, {
          title: "Second",
          description: "Second",
          settings: { provider: "dashscope", retained: true },
          updated_at: "2026-09-03T00:00:00.002Z",
        }),
      );
      await secondSave;
    });
    await act(async () => {
      first.resolve(
        scalar(original, {
          title: "First",
          description: "First",
          updated_at: "2026-09-03T00:00:00.001Z",
        }),
      );
      await firstSave;
    });

    expect(view.result().project).toMatchObject({ title: "Second", description: "Second" });
    expect(view.result().form).toMatchObject({ title: "Second", description: "Second" });
    expect(view.result().mutation.isUpdatingSettings).toBe(false);
  });

  it("blocks duplicate activation and aborts the owned request on unmount", async () => {
    const pending = deferred<ProjectListItem>();
    vi.mocked(api.updateProject).mockReturnValue(pending.promise);
    const original = projectFixture();
    const view = renderSettings(original);

    let save!: Promise<void>;
    act(() => {
      save = view.submit();
      void view.submit();
    });

    expect(api.updateProject).toHaveBeenCalledTimes(1);
    expect(view.result().mutation.isUpdatingSettings).toBe(true);
    const signal = vi.mocked(api.updateProject).mock.calls[0]?.[2]?.signal;
    harness.unmount(view.mounted.container);
    expect(signal?.aborted).toBe(true);
    pending.resolve(scalar(original));
    await save;
  });

  it("reports wrong response identity without merging", async () => {
    const original = projectFixture();
    const view = renderSettings(original);
    vi.mocked(api.updateProject).mockResolvedValue(scalar(original, { id: "project-other" }));

    await act(view.submit);

    expect(view.result().project).toEqual(original);
    expect(view.result().error).toBe("Invalid project settings response identity.");
  });

  it.each([
    [401, "session", "Sign in required."],
    [404, "project", "Project not found."],
  ] as const)("routes a %i without leaving a panel error", async (status, destination, message) => {
    const view = renderSettings();
    vi.mocked(api.updateProject).mockRejectedValue(new HttpError(message, status));

    await act(view.submit);

    expect(view.result().error).toBeNull();
    expect(view.onSessionLost).toHaveBeenCalledTimes(destination === "session" ? 1 : 0);
    expect(view.onProjectMissing).toHaveBeenCalledTimes(destination === "project" ? 1 : 0);
  });

  it("keeps an operational failure readable and makes the next submit retryable", async () => {
    const original = projectFixture();
    const view = renderSettings(original);
    vi.mocked(api.updateProject)
      .mockRejectedValueOnce(new HttpError("Persistence unavailable.", 503))
      .mockResolvedValueOnce(scalar(original, { title: "Recovered" }));

    await act(view.submit);
    expect(view.result().error).toBe("Persistence unavailable.");
    expect(view.result().mutation.isUpdatingSettings).toBe(false);

    await act(view.submit);
    expect(api.updateProject).toHaveBeenCalledTimes(2);
    expect(view.result().error).toBeNull();
  });
});
