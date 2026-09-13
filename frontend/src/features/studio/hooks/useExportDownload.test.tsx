import { act, StrictMode, useState } from "react";
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
  readonly exportError: ReturnType<typeof useExportDownload>["exportError"];
  readonly exportProject: ReturnType<typeof useExportDownload>["exportProject"];
  readonly exportingFormat: ReturnType<typeof useExportDownload>["exportingFormat"];
}

const mountHarness = createMountHarness();
const projectFixture = project({
  description: "A harbor of brass clocks.",
});
const exportFixture = studioExport({ project_id: projectFixture.id });
const exportJob = job({
  project_id: projectFixture.id,
  document_id: null,
  kind: "export",
  operation: "export",
  result: { export_id: exportFixture.id },
});
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

function renderExportHook(
  initialProject: Project | null = projectFixture,
  strict = false,
): {
  readonly result: () => HarnessSnapshot;
} {
  const selectedProject = initialProject;
  let current: HarnessSnapshot | undefined;

  function Wrapper(): null {
    const [exports, setExports] = useState<ExportsPage["exports"]>([]);
    const applyPage = (page: ExportsPage): void => setExports(page.exports);
    const { exportProject, exportingFormat, exportError } = useExportDownload(
      selectedProject,
      selectedProject?.id ?? projectFixture.id,
      applyPage,
    );
    current = { exports, exportError, exportProject, exportingFormat };
    return null;
  }

  const content = () =>
    strict ? (
      <StrictMode>
        <Wrapper />
      </StrictMode>
    ) : (
      <Wrapper />
    );
  mountHarness.mount(content());

  return {
    result: () => {
      if (current === undefined) {
        throw new Error("Expected hook result after render.");
      }
      return current;
    },
  };
}

function installDownloadSpies(blobUrl = "blob:export-1") {
  const createObjectURL = vi.fn<(value: Blob) => string>().mockReturnValue(blobUrl);
  const revokeObjectURL = vi.fn<(value: string) => void>();
  let clickedHref = "";
  let clickedDownload = "";
  vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    clickedHref = this.href;
    clickedDownload = this.download;
  });
  return {
    click,
    createObjectURL,
    revokeObjectURL,
    clickedHref: () => clickedHref,
    clickedDownload: () => clickedDownload,
  };
}

describe("useExportDownload", () => {
  it("downloads markdown with an md filename and revokes the object URL", async () => {
    // Given
    const blob = new Blob(["# Clockwork Harbor"], { type: "text/markdown" });
    const download = installDownloadSpies();
    vi.mocked(api.createExport).mockResolvedValue(exportJob);
    vi.mocked(api.exports).mockResolvedValue({ exports: [exportFixture], next_cursor: null });
    vi.mocked(api.download).mockResolvedValue(blob);
    const harness = renderExportHook();
    let pending!: Promise<void>;

    // When
    act(() => {
      pending = harness.result().exportProject("markdown");
    });
    await vi.waitFor(() => expect(download.click).toHaveBeenCalledTimes(1));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
      await pending;
    });

    // Then
    expect(harness.result().exports).toEqual([exportFixture]);
    expect(download.clickedHref()).toBe("blob:export-1");
    expect(download.clickedDownload()).toBe("Clockwork Harbor.md");
    expect(download.createObjectURL).toHaveBeenCalledWith(blob);
    expect(download.revokeObjectURL).toHaveBeenCalledWith("blob:export-1");
  });

  it("reports the export error without creating a download link", async () => {
    // Given
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click");
    vi.mocked(api.createExport).mockRejectedValue(new Error("export unavailable"));
    const harness = renderExportHook();

    // When
    await act(async () => {
      await harness.result().exportProject("docx");
    });

    // Then
    expect(harness.result().exportError).toBe("export unavailable");
    expect(harness.result().exports).toEqual([]);
    expect(click).not.toHaveBeenCalled();
    expect(api.download).not.toHaveBeenCalled();
  });

  it("revokes the object URL when link creation throws", async () => {
    const blob = new Blob(["draft"], { type: "text/markdown" });
    const download = installDownloadSpies();
    vi.mocked(api.createExport).mockResolvedValue(exportJob);
    vi.mocked(api.exports).mockResolvedValue({ exports: [exportFixture], next_cursor: null });
    vi.mocked(api.download).mockResolvedValue(blob);
    const harness = renderExportHook();
    vi.spyOn(document.body, "appendChild").mockImplementationOnce(() => {
      throw new Error("link unavailable");
    });
    let pending!: Promise<void>;

    act(() => {
      pending = harness.result().exportProject("markdown");
    });
    await vi.waitFor(() => expect(download.createObjectURL).toHaveBeenCalledWith(blob));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
      await pending;
    });

    expect(download.revokeObjectURL).toHaveBeenCalledWith("blob:export-1");
    expect(download.click).not.toHaveBeenCalled();
    expect(harness.result().exportError).toBe("link unavailable");
  });

  it("reports a failed export job without refreshing the catalog", async () => {
    // Given
    const failedJob: StudioJob = {
      ...exportJob,
      status: "failed",
      error: "A project needs at least one chapter before export.",
    };
    vi.mocked(api.createExport).mockResolvedValue(failedJob);
    const harness = renderExportHook();

    // When
    await act(async () => {
      await harness.result().exportProject("markdown");
    });

    // Then
    expect(harness.result().exportError).toBe(
      "A project needs at least one chapter before export.",
    );
    expect(harness.result().exports).toEqual([]);
    expect(api.exports).not.toHaveBeenCalled();
    expect(api.download).not.toHaveBeenCalled();
  });

  it("does nothing when no project is selected", async () => {
    // Given
    const harness = renderExportHook(null);

    // When
    await act(async () => {
      await harness.result().exportProject("epub");
    });

    // Then
    expect(harness.result().exports).toEqual([]);
    expect(harness.result().exportError).toBeNull();
    expect(api.createExport).not.toHaveBeenCalled();
  });

  it("blocks a duplicate command before the pending-state render commits", async () => {
    const createResponse = deferred<StudioJob>();
    const blob = new Blob(["draft"], { type: "text/markdown" });
    vi.mocked(api.createExport).mockReturnValue(createResponse.promise);
    vi.mocked(api.exports).mockResolvedValue({ exports: [exportFixture], next_cursor: null });
    vi.mocked(api.download).mockResolvedValue(blob);
    const download = installDownloadSpies();
    const harness = renderExportHook();
    let first!: Promise<void>;

    act(() => {
      first = harness.result().exportProject("markdown");
      void harness.result().exportProject("docx");
    });

    expect(api.createExport).toHaveBeenCalledTimes(1);
    expect(harness.result().exportingFormat).toBe("markdown");

    act(() => {
      createResponse.resolve(exportJob);
    });
    await vi.waitFor(() => expect(download.click).toHaveBeenCalledTimes(1));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
      await first;
    });
    expect(api.download).toHaveBeenCalledTimes(1);
    expect(harness.result().exportingFormat).toBeNull();
  });

  it("keeps the command owner active after the StrictMode lifecycle replay", async () => {
    const blob = new Blob(["draft"], { type: "text/markdown" });
    vi.mocked(api.createExport).mockResolvedValue(exportJob);
    vi.mocked(api.exports).mockResolvedValue({ exports: [exportFixture], next_cursor: null });
    vi.mocked(api.download).mockResolvedValue(blob);
    const download = installDownloadSpies();
    const harness = renderExportHook(projectFixture, true);
    let pending!: Promise<void>;

    act(() => {
      pending = harness.result().exportProject("markdown");
    });
    await vi.waitFor(() => expect(download.click).toHaveBeenCalledTimes(1));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
      await pending;
    });

    expect(api.createExport).toHaveBeenCalledTimes(1);
    expect(download.click).toHaveBeenCalledTimes(1);
    expect(harness.result().exportingFormat).toBeNull();
  });
});
