import { getByRole, queryByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { setActiveLanguage } from "@/app/i18n/language";
import { createMountHarness, deferred } from "@/test/harness";
import { ClipboardCopyButton } from "./ClipboardCopyButton";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.unstubAllGlobals();
  setActiveLanguage("en");
});

describe("ClipboardCopyButton", () => {
  it("reports a refusal, retains retry, and clears the error after success", async () => {
    const writeText = vi
      .fn<(text: string) => Promise<void>>()
      .mockRejectedValueOnce(new DOMException("Denied", "NotAllowedError"))
      .mockResolvedValueOnce(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const mounted = harness.mount(<ClipboardCopyButton text="Preserved text." />);
    const copy = getByRole(mounted.container, "button", { name: "Copy" });
    await act(async () => copy.click());
    expect(getByRole(mounted.container, "alert").textContent).toContain("copy it manually");
    expect(copy.hasAttribute("disabled")).toBe(false);
    await act(async () => copy.click());
    expect(queryByRole(mounted.container, "alert")).toBeNull();
    expect(getByRole(mounted.container, "status").textContent).toBe("Copied.");
    expect(writeText).toHaveBeenNthCalledWith(2, "Preserved text.");
  });

  it("offers manual copying in Chinese when the API is unavailable", async () => {
    vi.stubGlobal("navigator", {});
    setActiveLanguage("zh");
    const mounted = harness.mount(<ClipboardCopyButton text="保留的正文" />);
    await act(async () => getByRole(mounted.container, "button", { name: "复制" }).click());
    expect(getByRole(mounted.container, "alert").textContent).toBe(
      "复制失败。请手动选择文本复制，或重试。",
    );
  });

  it("drops settled feedback on text changes and discards late results", async () => {
    const pending = deferred<void>();
    const writeText = vi
      .fn<(text: string) => Promise<void>>()
      .mockResolvedValueOnce(undefined)
      .mockImplementationOnce(() => pending.promise);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const mounted = harness.mount(<ClipboardCopyButton text="First text." />);
    await act(async () => getByRole(mounted.container, "button", { name: "Copy" }).click());
    expect(getByRole(mounted.container, "status").textContent).toBe("Copied.");
    act(() => mounted.root.render(<ClipboardCopyButton text="Second text." />));
    expect(queryByRole(mounted.container, "status")).toBeNull();
    act(() => getByRole(mounted.container, "button", { name: "Copy" }).click());
    act(() => mounted.root.render(<ClipboardCopyButton text="First text." />));
    await act(async () => {
      pending.resolve();
      await pending.promise;
    });
    expect(queryByRole(mounted.container, "status")).toBeNull();
    expect(queryByRole(mounted.container, "alert")).toBeNull();
  });

  it("does not let an older failed attempt replace a newer success", async () => {
    let rejectFirst!: (reason: unknown) => void;
    const first = new Promise<void>((_resolve, reject) => {
      rejectFirst = reject;
    });
    const writeText = vi
      .fn<(text: string) => Promise<void>>()
      .mockReturnValueOnce(first)
      .mockResolvedValueOnce(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const mounted = harness.mount(<ClipboardCopyButton text="Same text." />);
    const copy = getByRole(mounted.container, "button", { name: "Copy" });
    act(() => copy.click());
    await act(async () => copy.click());
    await act(async () => {
      rejectFirst(new DOMException("Denied", "NotAllowedError"));
      await first.catch(() => undefined);
    });
    expect(queryByRole(mounted.container, "alert")).toBeNull();
    expect(getByRole(mounted.container, "status").textContent).toBe("Copied.");
  });

  it("reports unexpected programming failures through diagnostics", async () => {
    const problem = new TypeError("Unexpected implementation bug");
    const reportError = vi.fn();
    vi.stubGlobal("reportError", reportError);
    vi.stubGlobal("navigator", { clipboard: { writeText: vi.fn().mockRejectedValue(problem) } });
    const mounted = harness.mount(<ClipboardCopyButton text="Preserved text." />);
    await act(async () => getByRole(mounted.container, "button", { name: "Copy" }).click());
    expect(reportError).toHaveBeenCalledWith(problem);
    expect(getByRole(mounted.container, "alert").textContent).toContain("copy it manually");
  });
});
