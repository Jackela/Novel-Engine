import { act, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project, StudioExport, StudioJob } from "@/app/types/studio";
import { job, project, studioExport } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

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
  readonly exports: StudioExport[];
  readonly error: string | null;
  readonly exportProject: ReturnType<typeof useExportDownload>["exportProject"];
}

const harness = createMountHarness();
const projectFixture = project({
  description: "A harbor of brass clocks.",
});
const exportFixture = studioExport({ project_id: projectFixture.id });
const exportJob = job({
  project_id: projectFixture.id,
  document_id: null,
  kind: "export",
  operation: "export",
  provider: "studio",
  model: "",
  request: { format: "markdown" },
  result: { export_id: "export-1" },
  events: [
    {
      id: "event-1",
      status: "completed",
      details: { export_id: "export-1" },
      created_at: "2026-08-27T00:01:00Z",
    },
  ],
});

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  harness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
  vi.restoreAllMocks();
});

function renderExportHook(selectedProject: Project | null = projectFixture): {
  readonly result: () => HarnessSnapshot;
} {
  let current: HarnessSnapshot | undefined;

  function Wrapper(): null {
    const [exports, setExports] = useState<StudioExport[]>([]);
    const [error, setError] = useState<string | null>(null);
    const { exportProject } = useExportDownload(
      selectedProject,
      projectFixture.id,
      setExports,
      setError,
    );
    current = { exports, error, exportProject };
    return null;
  }

  harness.mount(<Wrapper />);

  return {
    result: () => {
      if (current === undefined) {
        throw new Error("Expected hook result after render.");
      }
      return current;
    },
  };
}

describe("useExportDownload", () => {
  it("downloads markdown with an md filename and revokes the object URL", async () => {
    // Given
    const blob = new Blob(["# Clockwork Harbor"], { type: "text/markdown" });
    const createObjectURL = vi.fn<(value: Blob) => string>().mockReturnValue("blob:export-1");
    const revokeObjectURL = vi.fn<(value: string) => void>();
    let clickedHref = "";
    let clickedDownload = "";
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clickedHref = this.href;
      clickedDownload = this.download;
    });
    vi.mocked(api.createExport).mockResolvedValue(exportJob);
    vi.mocked(api.exports).mockResolvedValue({ exports: [exportFixture] });
    vi.mocked(api.download).mockResolvedValue(blob);
    const harness = renderExportHook();

    // When
    await act(async () => {
      await harness.result().exportProject("markdown");
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    // Then
    expect(harness.result().exports).toEqual([exportFixture]);
    expect(clickedHref).toBe("blob:export-1");
    expect(clickedDownload).toBe("Clockwork Harbor.md");
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:export-1");
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
    expect(harness.result().error).toBe("export unavailable");
    expect(harness.result().exports).toEqual([]);
    expect(click).not.toHaveBeenCalled();
    expect(api.download).not.toHaveBeenCalled();
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
    expect(harness.result().error).toBe("A project needs at least one chapter before export.");
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
    expect(harness.result().error).toBeNull();
    expect(api.createExport).not.toHaveBeenCalled();
  });
});
