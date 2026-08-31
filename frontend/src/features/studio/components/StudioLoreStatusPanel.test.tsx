import { fireEvent, getByRole, queryByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { chapter } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { StudioLoreStatusPanel } from "./StudioLoreStatusPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

function render(element: React.ReactElement): HTMLDivElement {
  return harness.mount(element).container;
}

describe("StudioLoreStatusPanel (#444)", () => {
  const character = chapter("doc-1", { kind: "character", title: "Mara", lore_status: "draft" });

  it("renders nothing without an active document", () => {
    const container = render(<StudioLoreStatusPanel document={null} onStatusChange={vi.fn()} />);
    expect(queryByRole(container, "combobox", { name: "Lore status" })).toBeNull();
  });

  it("renders nothing for non-lore kinds — the semantics never leak beyond lore", () => {
    const note = chapter("doc-2", { kind: "note", title: "Scratch", lore_status: null });
    const container = render(<StudioLoreStatusPanel document={note} onStatusChange={vi.fn()} />);
    expect(queryByRole(container, "combobox", { name: "Lore status" })).toBeNull();
  });

  it("offers exactly the closed lifecycle set for a lore document", () => {
    const container = render(
      <StudioLoreStatusPanel document={character} onStatusChange={vi.fn()} />,
    );

    const select = getByRole(container, "combobox", { name: "Lore status" }) as HTMLSelectElement;
    expect(select.value).toBe("draft");
    const options = Array.from(select.options).map((option) => option.value);
    expect(options).toEqual(["draft", "stable", "deprecated"]);
  });

  it("submits the selected status and disables the control while saving", async () => {
    const onStatusChange = vi.fn(async () => {
      await Promise.resolve();
    });
    const container = render(
      <StudioLoreStatusPanel document={character} onStatusChange={onStatusChange} />,
    );

    const select = getByRole(container, "combobox", { name: "Lore status" }) as HTMLSelectElement;
    select.value = "stable";
    fireEvent.change(select);

    await act(async () => {
      fireEvent.submit(getByRole(container, "button", { name: "Save status" }));
    });

    expect(onStatusChange).toHaveBeenCalledTimes(1);
    expect(onStatusChange).toHaveBeenCalledWith("stable");
    // Focus returns to the save button after the update completes.
    expect(document.activeElement).toBe(getByRole(container, "button", { name: "Save status" }));
  });

  it("disables the save button while saving or when nothing changed", () => {
    // Unchanged selection: the save button stays disabled even while idle.
    const idle = render(<StudioLoreStatusPanel document={character} onStatusChange={vi.fn()} />);
    const idleSave = getByRole(idle, "button", { name: "Save status" }) as HTMLButtonElement;
    expect(idleSave.disabled).toBe(true);

    const saving = render(
      <StudioLoreStatusPanel document={character} isSaving onStatusChange={vi.fn()} />,
    );
    const savingSave = getByRole(saving, "button", { name: "Saving…" }) as HTMLButtonElement;
    expect(savingSave.disabled).toBe(true);
    const select = getByRole(saving, "combobox", { name: "Lore status" }) as HTMLSelectElement;
    expect(select.disabled).toBe(true);
  });
});
