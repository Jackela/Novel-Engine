import { act, StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { DiagnosticsSummary } from "@/app/types/studio";
import { createMountHarness, deferred } from "@/test/harness";

import { useDiagnosticsDownload } from "./useDiagnosticsDownload";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();

  return {
    ...actual,
    api: {
      ...actual.api,
      diagnostics: vi.fn<typeof actual.api.diagnostics>(),
    },
  };
});

const diagnosticsSummary: DiagnosticsSummary = {
  generated_at: "2026-09-14T09:15:00Z",
  product: { name: "Novel Engine", version: "1.2.3" },
  runtime: { platform: "darwin", architecture: "arm64", node_version: "24.11.0" },
  configuration: {
    provider: { id: "mock", configured: true },
    keys: { session_secret: true, dashscope_api_key: false, openai_compatible_api_key: false },
  },
  database: {
    quick_check: "ok",
    journal_mode: "wal",
    foreign_keys: true,
    owner_configured: true,
  },
  recent_errors: [],
};

interface HarnessSnapshot {
  readonly diagnosticsError: ReturnType<typeof useDiagnosticsDownload>["diagnosticsError"];
  readonly exportDiagnostics: ReturnType<typeof useDiagnosticsDownload>["exportDiagnostics"];
  readonly isExportingDiagnostics: ReturnType<
    typeof useDiagnosticsDownload
  >["isExportingDiagnostics"];
}

const mountHarness = createMountHarness();

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-09-14T10:30:00Z"));
});

afterEach(() => {
  mountHarness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
  vi.restoreAllMocks();
});

function renderDiagnosticsHook(
  projectId = "project-1",
  strict = false,
): {
  readonly result: () => HarnessSnapshot;
} {
  let current: HarnessSnapshot | undefined;
  function Wrapper(): null {
    const { exportDiagnostics, isExportingDiagnostics, diagnosticsError } =
      useDiagnosticsDownload(projectId);
    current = { diagnosticsError, exportDiagnostics, isExportingDiagnostics };
    return null;
  }
  mountHarness.mount(
    strict ? (
      <StrictMode>
        <Wrapper />
      </StrictMode>
    ) : (
      <Wrapper />
    ),
  );
  return {
    result: () => {
      if (current === undefined) throw new Error("Expected hook result after render.");
      return current;
    },
  };
}

function installDownloadSpies(blobUrl = "blob:diagnostics-1") {
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

describe("useDiagnosticsDownload", () => {
  it("downloads the summary as JSON with the client-derived filename", async () => {
    // Given
    const download = installDownloadSpies();
    vi.mocked(api.diagnostics).mockResolvedValue(diagnosticsSummary);
    const harness = renderDiagnosticsHook("project-1");
    let pending!: Promise<void>;

    // When
    act(() => {
      pending = harness.result().exportDiagnostics();
    });
    await vi.waitFor(() => expect(download.click).toHaveBeenCalledTimes(1));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
      await pending;
    });

    // Then: the only request targets the Studio's own diagnostics endpoint
    // for the current project.
    expect(api.diagnostics).toHaveBeenCalledTimes(1);
    expect(api.diagnostics).toHaveBeenCalledWith("project-1", expect.anything());
    expect(download.clickedHref()).toBe("blob:diagnostics-1");
    expect(download.clickedDownload()).toBe("novel-engine-diagnostics-2026-09-14.json");
    const blob = download.createObjectURL.mock.calls[0]?.[0];
    if (blob === undefined) throw new Error("Expected the diagnostics blob.");
    await expect(blob.text()).resolves.toBe(`${JSON.stringify(diagnosticsSummary, null, 2)}\n`);
    expect(blob.type).toBe("application/json");
    expect(download.revokeObjectURL).toHaveBeenCalledWith("blob:diagnostics-1");
    expect(harness.result().isExportingDiagnostics).toBe(false);
    expect(harness.result().diagnosticsError).toBeNull();
  });

  it("surfaces the failure and retries through the same command", async () => {
    // Given
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click");
    vi.mocked(api.diagnostics).mockRejectedValueOnce(new Error("diagnostics unavailable"));
    vi.mocked(api.diagnostics).mockResolvedValueOnce(diagnosticsSummary);
    const download = installDownloadSpies();
    const harness = renderDiagnosticsHook();

    // When
    await act(async () => {
      await harness.result().exportDiagnostics();
    });

    // Then
    expect(harness.result().diagnosticsError).toBe("diagnostics unavailable");
    expect(click).not.toHaveBeenCalled();

    await act(async () => {
      await harness.result().exportDiagnostics();
    });
    expect(download.click).toHaveBeenCalledTimes(1);
    expect(harness.result().diagnosticsError).toBeNull();
    expect(harness.result().isExportingDiagnostics).toBe(false);
  });

  it("guards duplicate submission while one export is in flight", async () => {
    // Given
    const response = deferred<DiagnosticsSummary>();
    vi.mocked(api.diagnostics).mockReturnValue(response.promise);
    const download = installDownloadSpies();
    const harness = renderDiagnosticsHook();
    let first!: Promise<void>;

    // When
    act(() => {
      first = harness.result().exportDiagnostics();
      void harness.result().exportDiagnostics();
    });

    // Then
    expect(api.diagnostics).toHaveBeenCalledTimes(1);
    expect(harness.result().isExportingDiagnostics).toBe(true);

    act(() => {
      response.resolve(diagnosticsSummary);
    });
    await vi.waitFor(() => expect(download.click).toHaveBeenCalledTimes(1));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
      await first;
    });
    expect(harness.result().isExportingDiagnostics).toBe(false);
  });

  it("keeps the command idempotent across the StrictMode lifecycle replay", async () => {
    // Given
    const download = installDownloadSpies();
    vi.mocked(api.diagnostics).mockResolvedValue(diagnosticsSummary);
    const harness = renderDiagnosticsHook("project-1", true);
    let pending!: Promise<void>;

    // When
    act(() => {
      pending = harness.result().exportDiagnostics();
    });
    await vi.waitFor(() => expect(download.click).toHaveBeenCalledTimes(1));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
      await pending;
    });

    // Then
    expect(api.diagnostics).toHaveBeenCalledTimes(1);
    expect(download.click).toHaveBeenCalledTimes(1);
  });
});
