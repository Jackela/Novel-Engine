import { fireEvent, getByRole } from "@testing-library/dom";
import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { LoreStatus } from "@/app/types/studio";
import { createMountHarness, deferred } from "@/test/harness";

import { StudioLoreStatusPanel } from "./StudioLoreStatusPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

interface LoreLifecycle {
  readonly isSaving: boolean;
  readonly attemptedStatus: LoreStatus | null;
}

function renderSwitchingPanel(save: ReturnType<typeof deferred<void>>) {
  let showDocument!: (documentId: "a" | "b") => void;

  function Probe() {
    const [activeDocument, setActiveDocument] = useState<"a" | "b">("a");
    const [savedA, setSavedA] = useState<LoreStatus>("draft");
    const [lifecycleA, setLifecycleA] = useState<LoreLifecycle>({
      isSaving: false,
      attemptedStatus: null,
    });
    showDocument = setActiveDocument;

    if (activeDocument === "b") {
      return (
        <StudioLoreStatusPanel
          documentId="world-b"
          savedStatus="stable"
          onSubmit={vi.fn().mockResolvedValue(undefined)}
        />
      );
    }

    return (
      <StudioLoreStatusPanel
        documentId="character-a"
        savedStatus={savedA}
        attemptedStatus={lifecycleA.attemptedStatus}
        isSaving={lifecycleA.isSaving}
        onSubmit={async (status) => {
          setLifecycleA({ isSaving: true, attemptedStatus: status });
          await save.promise;
          setSavedA(status);
          setLifecycleA({ isSaving: false, attemptedStatus: null });
        }}
      />
    );
  }

  const mounted = harness.mount(<Probe />);
  return { ...mounted, showDocument: (documentId: "a" | "b") => showDocument(documentId) };
}

describe("StudioLoreStatusPanel document focus identity", () => {
  it("restores to the returning origin document's selector after its trigger was replaced", async () => {
    const save = deferred<void>();
    const view = renderSwitchingPanel(save);
    const firstSelect = getByRole(view.container, "combobox", {
      name: "Lore status",
    }) as HTMLSelectElement;
    firstSelect.value = "stable";
    fireEvent.change(firstSelect);
    const firstSave = getByRole(view.container, "button", { name: "Save status" });
    firstSave.focus();

    act(() => {
      fireEvent.submit(firstSave);
    });
    await act(async () => {
      await Promise.resolve();
    });

    act(() => view.showDocument("b"));
    expect(getByRole(view.container, "combobox", { name: "Lore status" })).toHaveValue("stable");

    act(() => view.showDocument("a"));
    const returningSelect = getByRole(view.container, "combobox", { name: "Lore status" });
    expect(returningSelect).not.toBe(firstSelect);
    expect(returningSelect).toHaveValue("stable");
    expect(returningSelect).toBeDisabled();

    await act(async () => {
      save.resolve();
      await save.promise;
      await Promise.resolve();
    });

    expect(getByRole(view.container, "button", { name: "Save status" })).toBeDisabled();
    expect(document.activeElement).toBe(returningSelect);
  });

  it("does not use document B's selector as the fallback for document A", async () => {
    const save = deferred<void>();
    const view = renderSwitchingPanel(save);
    const select = getByRole(view.container, "combobox", {
      name: "Lore status",
    }) as HTMLSelectElement;
    select.value = "stable";
    fireEvent.change(select);
    const saveButton = getByRole(view.container, "button", { name: "Save status" });
    saveButton.focus();

    act(() => fireEvent.submit(saveButton));
    await act(async () => {
      await Promise.resolve();
    });
    act(() => view.showDocument("b"));
    const worldSelect = getByRole(view.container, "combobox", { name: "Lore status" });
    expect(document.activeElement).toBe(document.body);

    await act(async () => {
      save.resolve();
      await save.promise;
      await Promise.resolve();
    });

    expect(document.activeElement).toBe(document.body);
    expect(document.activeElement).not.toBe(worldSelect);
  });
});
