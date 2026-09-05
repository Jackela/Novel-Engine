import { act, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { ExportsPage } from "@/app/apiWorkflowContract";
import type { Project, StudioJob } from "@/app/types/studio";
import { job, project, studioExport } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useExportDownload } from "./useExportDownload";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      createExport: vi.fn<typeof actual.api.createExport>(),
      exports: vi.fn<typeof actual.api.exports>(),
      download: vi.fn<typeof actual.api.download>(),
    },
  };
});

interface HarnessSnapshot {
  readonly exports: ExportsPage["exports"];
  readonly error: string | null;
  readonly exportError: ReturnType<typeof useExportDownload>["exportError"];
  readonly exportProject: ReturnType<typeof useExportDownload>["exportProject"];
  readonly retryExport: ReturnType<typeof useExportDownload>["retryExport"];
  readonly exportingFormat: ReturnType<typeof useExportDownload>["exportingFormat"];
  readonly retryingFormat: ReturnType<typeof useExportDownload>["retryingFormat"];
  readonly failedFormat: ReturnType<typeof useExportDownload>["failedFormat"];
  readonly clearSharedError: () => void;
}

const mountHarness = createMountHarness();
const projectA = project();
const exportA = studioExport({ project_id: projectA.id });
const exportJobA = job({ project_id: projectA.id, result: { export_id: exportA.id } });
const projectB = project({ id: "project-2", title: "Glass Archive" });
const exportB = studioExport({
  id: "export-2",
  project_id: projectB.id,
  format: "docx",
  download_url: "/downloads/export-2",
});
const exportJobB = job({ project_id: projectB.id, result: { export_id: exportB.id } });

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  mountHarness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
  vi.restoreAllMocks();
});

function renderExportHook(): {
  readonly result: () => HarnessSnapshot;
  readonly rerender: (nextProject: Project) => void;
  readonly unmount: () => void;
} {
  let selectedProject = projectA;
  let current: HarnessSnapshot | undefined;

  function Wrapper(): null {
    const [exports, setExports] = useState<ExportsPage["exports"]>([]);
    const [error, setError] = useState<string | null>(null);
    const applyPage = (page: ExportsPage): void => setExports(page.exports);
    const hook = useExportDownload(selectedProject, selectedProject.id, applyPage);
    current = { exports, error, clearSharedError: () => setError(null), ...hook };
    return null;
  }

  const { container, root } = mountHarness.mount(<Wrapper />);
  return {
    result: () => {
      if (current === undefined) throw new Error("Expected hook result after render.");
      return current;
    },
    rerender: (nextProject) => {
      selectedProject = nextProject;
      act(() => root.render(<Wrapper />));
    },
    unmount: () => mountHarness.unmount(container),
  };
}

function installDownloadSpies(blobUrl = "blob:export-1") {
  const createObjectURL = vi.fn<(value: Blob) => string>().mockReturnValue(blobUrl);
  const revokeObjectURL = vi.fn<(value: string) => void>();
  let clickedDownload = "";
  vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    clickedDownload = this.download;
  });
  return { click, createObjectURL, revokeObjectURL, clickedDownload: () => clickedDownload };
}

describe("useExportDownload lifecycle", () => {
  it("keeps a failed export retryable after an unrelated workflow clears the shared error", async () => {
    vi.mocked(api.createExport).mockRejectedValue(new Error("export unavailable"));
    const harness = renderExportHook();

    await act(async () => {
      await harness.result().exportProject("docx");
    });
    act(() => {
      harness.result().clearSharedError();
    });

    expect(harness.result().error).toBeNull();
    expect(harness.result().exportError).toBe("export unavailable");
    expect(harness.result().failedFormat).toBe("docx");
  });

  it("identifies a retry separately from a normal export while it is pending", async () => {
    const retryResponse = deferred<StudioJob>();
    vi.mocked(api.createExport)
      .mockRejectedValueOnce(new Error("export unavailable"))
      .mockReturnValueOnce(retryResponse.promise);
    const harness = renderExportHook();

    await act(async () => {
      await harness.result().exportProject("docx");
    });
    let pending!: Promise<void>;
    act(() => {
      pending = harness.result().retryExport("docx");
    });

    expect(harness.result().exportingFormat).toBe("docx");
    expect(harness.result().retryingFormat).toBe("docx");
    expect(harness.result().exportError).toBe("export unavailable");
    expect(harness.result().failedFormat).toBe("docx");

    await act(async () => {
      retryResponse.resolve({ ...exportJobA, status: "failed", error: "retry unavailable" });
      await pending;
    });
    expect(harness.result().retryingFormat).toBeNull();
  });

  it("binds pending cleanup to the invocation epoch across an A to B switch", async () => {
    const projectAResponse = deferred<StudioJob>();
    const projectBResponse = deferred<StudioJob>();
    vi.mocked(api.createExport)
      .mockReturnValueOnce(projectAResponse.promise)
      .mockReturnValueOnce(projectBResponse.promise);
    vi.mocked(api.exports).mockResolvedValue({ exports: [exportB], next_cursor: null });
    vi.mocked(api.download).mockResolvedValue(new Blob(["glass"]));
    const download = installDownloadSpies("blob:export-2");
    const harness = renderExportHook();
    let projectAPending!: Promise<void>;
    let projectBPending!: Promise<void>;

    act(() => {
      projectAPending = harness.result().exportProject("markdown");
    });
    const projectASignal = vi.mocked(api.createExport).mock.calls[0]?.[2]?.signal;
    harness.rerender(projectB);
    expect(projectASignal?.aborted).toBe(true);
    act(() => {
      projectBPending = harness.result().exportProject("docx");
    });

    await act(async () => {
      projectAResponse.resolve(exportJobA);
      await projectAPending;
    });
    expect(harness.result().exportingFormat).toBe("docx");
    expect(api.exports).not.toHaveBeenCalled();

    act(() => {
      projectBResponse.resolve(exportJobB);
    });
    await vi.waitFor(() => expect(download.click).toHaveBeenCalledTimes(1));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
      await projectBPending;
    });
    expect(harness.result().exports).toEqual([exportB]);
    expect(harness.result().error).toBeNull();
    expect(harness.result().failedFormat).toBeNull();
    expect(download.clickedDownload()).toBe("Glass Archive.docx");
    expect(download.createObjectURL).toHaveBeenCalledTimes(1);
  });

  it("aborts a stale catalog and does not publish or continue its completion", async () => {
    const catalogResponse = deferred<ExportsPage>();
    vi.mocked(api.createExport).mockResolvedValue(exportJobA);
    vi.mocked(api.exports).mockReturnValue(catalogResponse.promise);
    const download = installDownloadSpies();
    const harness = renderExportHook();
    const pending = harness.result().exportProject("markdown");
    await vi.waitFor(() => expect(api.exports).toHaveBeenCalledTimes(1));
    const catalogSignal = vi.mocked(api.exports).mock.calls[0]?.[1]?.signal;

    harness.rerender(projectB);
    expect(catalogSignal?.aborted).toBe(true);
    await act(async () => {
      catalogResponse.resolve({ exports: [exportA], next_cursor: null });
      await pending;
    });

    expect(harness.result().exports).toEqual([]);
    expect(harness.result().error).toBeNull();
    expect(api.download).not.toHaveBeenCalled();
    expect(download.createObjectURL).not.toHaveBeenCalled();
  });

  it("does not publish an error from the previous project owner", async () => {
    let rejectProjectA!: (reason: unknown) => void;
    vi.mocked(api.createExport).mockReturnValue(
      new Promise((_resolve, reject) => {
        rejectProjectA = reject;
      }),
    );
    const harness = renderExportHook();
    let pending!: Promise<void>;
    act(() => {
      pending = harness.result().exportProject("markdown");
    });

    harness.rerender(projectB);
    await act(async () => {
      rejectProjectA(new Error("late project A failure"));
      await pending;
    });

    expect(harness.result().error).toBeNull();
    expect(harness.result().failedFormat).toBeNull();
    expect(harness.result().exportingFormat).toBeNull();
  });

  it("aborts an unmounted blob transport and never creates or clicks a stale URL", async () => {
    const blobResponse = deferred<Blob>();
    vi.mocked(api.createExport).mockResolvedValue(exportJobA);
    vi.mocked(api.exports).mockResolvedValue({ exports: [exportA], next_cursor: null });
    vi.mocked(api.download).mockReturnValue(blobResponse.promise);
    const download = installDownloadSpies();
    const harness = renderExportHook();
    const pending = harness.result().exportProject("markdown");
    await vi.waitFor(() => expect(api.download).toHaveBeenCalledTimes(1));
    const blobSignal = vi.mocked(api.download).mock.calls[0]?.[1]?.signal;

    harness.unmount();
    expect(blobSignal?.aborted).toBe(true);
    await act(async () => {
      blobResponse.resolve(new Blob(["stale"]));
      await pending;
    });

    expect(download.createObjectURL).not.toHaveBeenCalled();
    expect(download.click).not.toHaveBeenCalled();
  });

  it("revokes a created URL immediately when its project owner changes", async () => {
    vi.mocked(api.createExport).mockResolvedValue(exportJobA);
    vi.mocked(api.exports).mockResolvedValue({ exports: [exportA], next_cursor: null });
    vi.mocked(api.download).mockResolvedValue(new Blob(["draft"]));
    const download = installDownloadSpies();
    const harness = renderExportHook();
    let pending!: Promise<void>;

    act(() => {
      pending = harness.result().exportProject("markdown");
    });
    await vi.waitFor(() => expect(download.click).toHaveBeenCalledTimes(1));

    harness.rerender(projectB);
    expect(download.revokeObjectURL).toHaveBeenCalledWith("blob:export-1");
    expect(harness.result().exportingFormat).toBeNull();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
      await pending;
    });
  });
});
