import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness, deferred } from "@/test/harness";

import { StudioExportPanel } from "./StudioExportPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

describe("StudioExportPanel", () => {
  it("marks only the retry command busy when a failed format is retried", () => {
    const mounted = harness.mount(
      <StudioExportPanel
        error="Unable to export the project."
        exportingFormat="docx"
        exports={[]}
        failedFormat="docx"
        onExport={vi.fn()}
        onRetry={vi.fn()}
        retryingFormat="docx"
      />,
    );
    const formatButtons = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>(".export-format"),
    );
    const retry = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Retry docx export"]',
    );

    expect(formatButtons.map((button) => button.getAttribute("aria-busy"))).toEqual([
      "false",
      "false",
      "false",
    ]);
    expect(retry).toHaveAttribute("aria-busy", "true");
  });

  it("marks only the selected format busy for a normal export", () => {
    const mounted = harness.mount(
      <StudioExportPanel exportingFormat="epub" exports={[]} onExport={vi.fn()} />,
    );
    const formatButtons = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>(".export-format"),
    );

    expect(formatButtons.map((button) => button.getAttribute("aria-busy"))).toEqual([
      "false",
      "false",
      "true",
    ]);
  });

  it("does not steal focus after export when the author moved elsewhere", async () => {
    const completion = deferred<void>();
    const onExport = vi.fn(() => completion.promise);
    const mounted = harness.mount(<StudioExportPanel exports={[]} onExport={onExport} />);
    const formatButtons = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>(".export-format"),
    );
    const wordButton = formatButtons.find((button) =>
      button.textContent?.includes("Word document"),
    );
    if (wordButton === undefined) throw new Error("Expected the Word document button.");

    act(() => {
      wordButton.click();
      mounted.root.render(
        <StudioExportPanel exports={[]} onExport={onExport} exportingFormat="docx" />,
      );
    });
    const otherButton = document.createElement("button");
    document.body.appendChild(otherButton);
    otherButton.focus();

    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });
    expect(document.activeElement).toBe(otherButton);

    act(() => {
      mounted.root.render(
        <StudioExportPanel
          exports={[]}
          onExport={onExport}
          exportingFormat={null}
          error="Unable to export the project."
          failedFormat="docx"
          onRetry={vi.fn()}
        />,
      );
    });
    expect(document.activeElement).toBe(otherButton);
    otherButton.remove();
  });

  it("moves orphaned retry focus to the corresponding format after recovery", async () => {
    const completion = deferred<void>();
    const onRetry = vi.fn(() => completion.promise);
    const content = (exportingFormat: "docx" | null, error: string | null) => (
      <StudioExportPanel
        exports={[]}
        onExport={vi.fn()}
        exportingFormat={exportingFormat}
        error={error}
        failedFormat={error ? "docx" : null}
        onRetry={onRetry}
      />
    );
    const mounted = harness.mount(content(null, "Unable to export the project."));
    const retry = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Retry docx export"]',
    );
    const wordButton = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>(".export-format"),
    ).find((button) => button.textContent?.includes("Word document"));
    if (retry === null || wordButton === undefined) {
      throw new Error("Expected the retry and Word export commands.");
    }

    retry.focus();
    act(() => {
      retry.click();
      mounted.root.render(content("docx", "Unable to export the project."));
    });
    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });
    act(() => mounted.root.render(content(null, null)));

    expect(document.activeElement).toBe(wordButton);
  });
});
