import { fireEvent, getByRole } from "@testing-library/dom";
import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness, deferred } from "@/test/harness";

import { StudioBeatPanel } from "./StudioBeatPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

function render(element: React.ReactElement): HTMLDivElement {
  return harness.mount(element).container;
}

/**
 * The command owner's committed lifecycle: pending while the request runs,
 * then the successful command's normalized value becomes the stored reference
 * (#466) — which is exactly what disables the initiating control.
 */
function SuccessfulBeatHarness({
  save,
  initialBeatRef,
}: {
  save: ReturnType<typeof deferred<void>>;
  initialBeatRef: string | null;
}) {
  const [isSaving, setIsSaving] = useState(false);
  const [beatRef, setBeatRef] = useState<string | null>(initialBeatRef);
  return (
    <StudioBeatPanel
      documentId="doc-1"
      beatRef={beatRef}
      isSaving={isSaving}
      onLink={async (beat) => {
        setIsSaving(true);
        await save.promise;
        setBeatRef(beat);
        setIsSaving(false);
      }}
    />
  );
}

describe("StudioBeatPanel (#466)", () => {
  it("moves focus to the beat input when a successful link disables the submit button", async () => {
    const save = deferred<void>();
    const container = render(<SuccessfulBeatHarness initialBeatRef={null} save={save} />);
    const input = getByRole(container, "textbox", { name: "Beat title" }) as HTMLInputElement;
    const linkButton = getByRole(container, "button", { name: "Link beat" });
    fireEvent.change(input, { target: { value: "The Harbor" } });

    linkButton.focus();
    act(() => fireEvent.submit(linkButton));
    await act(async () => {
      save.resolve(undefined);
      await save.promise;
    });

    // Success keeps the submit command disabled (`requested === beatRef`),
    // so the input is the semantic landing zone.
    expect(getByRole(container, "button", { name: "Link beat" })).toBeDisabled();
    expect(document.activeElement).toBe(input);
  });

  it("moves focus to the beat input when a successful clear disables the clear button", async () => {
    const save = deferred<void>();
    const container = render(<SuccessfulBeatHarness initialBeatRef="The Harbor" save={save} />);
    const input = getByRole(container, "textbox", { name: "Beat title" }) as HTMLInputElement;
    const clearButton = getByRole(container, "button", { name: "Clear" });

    clearButton.focus();
    await act(async () => {
      fireEvent.click(clearButton);
      await Promise.resolve();
    });
    await act(async () => {
      save.resolve(undefined);
      await save.promise;
    });

    expect(getByRole(container, "button", { name: "Clear" })).toBeDisabled();
    expect(document.activeElement).toBe(input);
  });

  it("does not override focus the author moved during a beat save", async () => {
    const save = deferred<void>();
    const container = render(
      <StudioBeatPanel documentId="doc-1" beatRef={null} onLink={() => save.promise} />,
    );
    const input = getByRole(container, "textbox", { name: "Beat title" }) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "The Harbor" } });
    const linkButton = getByRole(container, "button", { name: "Link beat" });
    const otherButton = document.createElement("button");
    document.body.appendChild(otherButton);
    linkButton.focus();

    act(() => fireEvent.submit(linkButton));
    otherButton.focus();
    await act(async () => {
      save.resolve(undefined);
      await save.promise;
    });

    expect(document.activeElement).toBe(otherButton);
    otherButton.remove();
  });

  it("does not steal focus when document A settles after document B becomes active", async () => {
    const save = deferred<void>();
    const content = (documentId: string) => (
      <StudioBeatPanel documentId={documentId} beatRef={null} onLink={() => save.promise} />
    );
    const { container, root } = harness.mount(content("doc-1"));
    const inputA = getByRole(container, "textbox", { name: "Beat title" }) as HTMLInputElement;
    fireEvent.change(inputA, { target: { value: "The Harbor" } });
    const linkButton = getByRole(container, "button", { name: "Link beat" });
    linkButton.focus();
    act(() => fireEvent.submit(linkButton));

    // The same persistent owner now carries document B; its keyed form
    // remounts, and the author's focus belongs to the new document.
    act(() => root.render(content("doc-2")));
    const inputB = getByRole(container, "textbox", { name: "Beat title" }) as HTMLInputElement;
    inputB.focus();

    await act(async () => {
      save.resolve(undefined);
      await save.promise;
    });

    expect(document.activeElement).toBe(inputB);
  });

  it("announces failures assertively like every other error surface", () => {
    const container = render(
      <StudioBeatPanel
        documentId="doc-1"
        beatRef={null}
        error="Unable to update the chapter beat."
        onLink={vi.fn()}
      />,
    );
    const alert = getByRole(container, "alert");
    expect(alert.getAttribute("aria-live")).toBe("assertive");
  });
});
