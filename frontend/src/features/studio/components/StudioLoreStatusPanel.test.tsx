import { fireEvent, getByRole } from "@testing-library/dom";
import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness, deferred } from "@/test/harness";

import { StudioLoreStatusPanel } from "./StudioLoreStatusPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

function render(element: React.ReactElement): HTMLDivElement {
  return harness.mount(element).container;
}

function PendingLoreStatusHarness({ save }: { save: ReturnType<typeof deferred<void>> }) {
  const [isSaving, setIsSaving] = useState(false);
  return (
    <StudioLoreStatusPanel
      documentId="doc-1"
      savedStatus="draft"
      isSaving={isSaving}
      onSubmit={async () => {
        setIsSaving(true);
        try {
          await save.promise;
        } finally {
          setIsSaving(false);
        }
      }}
    />
  );
}

describe("StudioLoreStatusPanel (#444)", () => {
  const character = { documentId: "doc-1", savedStatus: "draft" as const };

  it("offers exactly the closed lifecycle set for a lore document", () => {
    const container = render(<StudioLoreStatusPanel {...character} onSubmit={vi.fn()} />);

    const select = getByRole(container, "combobox", { name: "Lore status" }) as HTMLSelectElement;
    expect(select.value).toBe("draft");
    const options = Array.from(select.options).map((option) => option.value);
    expect(options).toEqual(["draft", "stable", "deprecated"]);
  });

  it("discards document A's unsaved selection when document B becomes active", () => {
    const world = { documentId: "doc-2", savedStatus: "stable" as const };
    const { container, root } = harness.mount(
      <StudioLoreStatusPanel {...character} onSubmit={vi.fn()} />,
    );
    const characterSelect = getByRole(container, "combobox", {
      name: "Lore status",
    }) as HTMLSelectElement;
    act(() => {
      characterSelect.value = "deprecated";
      fireEvent.change(characterSelect);
    });

    act(() => {
      root.render(<StudioLoreStatusPanel {...world} onSubmit={vi.fn()} />);
    });

    const worldSelect = getByRole(container, "combobox", {
      name: "Lore status",
    }) as HTMLSelectElement;
    expect(worldSelect.value).toBe("stable");
    const saveButton = getByRole(container, "button", {
      name: "Save status",
    }) as HTMLButtonElement;
    expect(saveButton.disabled).toBe(true);
  });

  it("submits the selected status and disables the control while saving", async () => {
    const onSubmit = vi.fn(async () => {
      await Promise.resolve();
    });
    const container = render(<StudioLoreStatusPanel {...character} onSubmit={onSubmit} />);

    const select = getByRole(container, "combobox", { name: "Lore status" }) as HTMLSelectElement;
    select.value = "stable";
    fireEvent.change(select);

    await act(async () => {
      fireEvent.submit(getByRole(container, "button", { name: "Save status" }));
    });

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("stable");
    // Focus returns to the save button after the update completes.
    expect(document.activeElement).toBe(getByRole(container, "button", { name: "Save status" }));
  });

  it("restores focus only after the save Promise settles", async () => {
    const save = deferred<void>();
    const container = render(
      <StudioLoreStatusPanel {...character} onSubmit={() => save.promise} />,
    );
    const select = getByRole(container, "combobox", { name: "Lore status" }) as HTMLSelectElement;
    select.value = "stable";
    fireEvent.change(select);
    select.focus();

    act(() => {
      fireEvent.submit(getByRole(container, "button", { name: "Save status" }));
    });
    expect(document.activeElement).toBe(select);

    await act(async () => {
      save.resolve();
      await save.promise;
    });
    expect(document.activeElement).toBe(getByRole(container, "button", { name: "Save status" }));
  });

  it("restores focus after the committed pending-to-idle render", async () => {
    const save = deferred<void>();
    const container = render(<PendingLoreStatusHarness save={save} />);
    const select = getByRole(container, "combobox", { name: "Lore status" }) as HTMLSelectElement;
    select.value = "stable";
    fireEvent.change(select);
    select.focus();

    act(() => {
      fireEvent.submit(getByRole(container, "button", { name: "Save status" }));
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(
      (getByRole(container, "button", { name: "Saving…" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(document.activeElement).toBe(select);

    await act(async () => {
      save.resolve();
      await save.promise;
    });

    const saveButton = getByRole(container, "button", { name: "Save status" });
    expect((saveButton as HTMLButtonElement).disabled).toBe(false);
    expect(document.activeElement).toBe(saveButton);
  });

  it("does not steal focus when document A settles after document B becomes active", async () => {
    const save = deferred<void>();
    const { container, root } = harness.mount(
      <StudioLoreStatusPanel {...character} onSubmit={() => save.promise} />,
    );
    const characterSelect = getByRole(container, "combobox", {
      name: "Lore status",
    }) as HTMLSelectElement;
    characterSelect.value = "deprecated";
    fireEvent.change(characterSelect);
    act(() => {
      fireEvent.submit(getByRole(container, "button", { name: "Save status" }));
    });

    act(() => {
      root.render(
        <>
          <button type="button">Document B focus target</button>
          <StudioLoreStatusPanel
            documentId="doc-2"
            savedStatus="stable"
            isSaving
            onSubmit={vi.fn().mockResolvedValue(undefined)}
          />
        </>,
      );
    });
    const focusTarget = getByRole(container, "button", { name: "Document B focus target" });
    focusTarget.focus();

    await act(async () => {
      save.resolve();
      await save.promise;
    });

    expect(document.activeElement).toBe(focusTarget);
    expect(
      (getByRole(container, "combobox", { name: "Lore status" }) as HTMLSelectElement).value,
    ).toBe("stable");
  });

  it("keeps an attempted status available for retry while the saved baseline is unchanged", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const container = render(<StudioLoreStatusPanel {...character} onSubmit={onSubmit} />);
    const select = getByRole(container, "combobox", { name: "Lore status" }) as HTMLSelectElement;
    select.value = "deprecated";
    fireEvent.change(select);

    await act(async () => {
      fireEvent.submit(getByRole(container, "button", { name: "Save status" }));
      await Promise.resolve();
    });

    expect(select.value).toBe("deprecated");
    expect(
      (getByRole(container, "button", { name: "Save status" }) as HTMLButtonElement).disabled,
    ).toBe(false);

    await act(async () => {
      fireEvent.submit(getByRole(container, "button", { name: "Save status" }));
      await Promise.resolve();
    });
    expect(onSubmit).toHaveBeenCalledTimes(2);
    expect(onSubmit).toHaveBeenLastCalledWith("deprecated");
  });

  it("disables the save button while saving or when nothing changed", () => {
    // Unchanged selection: the save button stays disabled even while idle.
    const idle = render(<StudioLoreStatusPanel {...character} onSubmit={vi.fn()} />);
    const idleSave = getByRole(idle, "button", { name: "Save status" }) as HTMLButtonElement;
    expect(idleSave.disabled).toBe(true);

    const saving = render(<StudioLoreStatusPanel {...character} isSaving onSubmit={vi.fn()} />);
    const savingSave = getByRole(saving, "button", { name: "Saving…" }) as HTMLButtonElement;
    expect(savingSave.disabled).toBe(true);
    const select = getByRole(saving, "combobox", { name: "Lore status" }) as HTMLSelectElement;
    expect(select.disabled).toBe(true);
  });
});
