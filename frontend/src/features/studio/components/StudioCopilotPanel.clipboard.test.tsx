import { getByRole, queryByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness } from "@/test/harness";
import { StudioCopilotPanel } from "./StudioCopilotPanel";

const harness = createMountHarness();

function copilot(text: string) {
  return (
    <StudioCopilotPanel
      instruction=""
      setInstruction={vi.fn()}
      proposal={null}
      setProposal={vi.fn()}
      onRunProposal={vi.fn()}
      onAcceptProposal={vi.fn()}
      streamingText={text}
      streamingInterrupted
    />
  );
}

afterEach(() => {
  harness.cleanup();
  vi.unstubAllGlobals();
});

describe("StudioCopilotPanel clipboard recovery", () => {
  it("keeps interrupted text after a denied copy and clears the failure after retry", async () => {
    const denial = Promise.reject(new DOMException("Denied", "NotAllowedError"));
    void denial.catch(() => undefined);
    const writeText = vi
      .fn<(text: string) => Promise<void>>()
      .mockReturnValueOnce(denial)
      .mockResolvedValueOnce(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const mounted = harness.mount(copilot("Preserved scene."));
    const copy = getByRole(mounted.container, "button", { name: "Copy" });
    await act(async () => copy.click());
    expect(getByRole(mounted.container, "alert").textContent).toContain("copy it manually");
    expect(mounted.container.querySelector("pre")?.textContent).toBe("Preserved scene.");
    await act(async () => copy.click());
    expect(queryByRole(mounted.container, "alert")).toBeNull();
    expect(getByRole(mounted.container, "status").textContent).toBe("Copied.");
    expect(writeText).toHaveBeenNthCalledWith(2, "Preserved scene.");
  });

  it("offers manual copying without the API and resets feedback for new text", async () => {
    vi.stubGlobal("navigator", {});
    const mounted = harness.mount(copilot("First scene."));
    await act(async () => getByRole(mounted.container, "button", { name: "Copy" }).click());
    expect(getByRole(mounted.container, "alert").textContent).toContain("copy it manually");
    expect(mounted.container.querySelector("pre")?.textContent).toBe("First scene.");
    act(() => mounted.root.render(copilot("Second scene.")));
    expect(queryByRole(mounted.container, "alert")).toBeNull();
    expect(queryByRole(mounted.container, "status")).toBeNull();
    expect(mounted.container.querySelector("pre")?.textContent).toBe("Second scene.");
  });
});
