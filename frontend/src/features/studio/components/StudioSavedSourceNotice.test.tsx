import { act } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { createMountHarness } from "@/test/harness";
import { StudioInspectorTabPanels } from "./StudioInspectorTabPanels";
import { buildInspectorModel } from "./studioInspectorModel.fixture";

const harness = createMountHarness();
afterEach(() => harness.cleanup());

it("keeps Review and Export available while explaining that unsaved chapter edits are excluded", () => {
  const base = buildInspectorModel();
  const onExport = vi.fn();
  const model = { ...base, export: { ...base.export, onExport }, hasUnsavedChapter: true };
  const pending = {
    proposal: { running: false, accepting: false },
    review: false,
    jobs: { loading: false, retrying: false },
    settings: false,
  };
  const render = (hasUnsavedChapter: boolean) => (
    <StudioInspectorTabPanels
      inspector="review"
      model={{ ...model, hasUnsavedChapter }}
      pending={pending}
      tabId={(tab) => `tab-${tab}`}
      panelId={(tab) => `panel-${tab}`}
    />
  );
  const mounted = harness.mount(render(true));
  for (const id of ["review", "export"]) {
    const panel = mounted.container.querySelector(`#panel-${id}`);
    expect(panel?.textContent).toContain("Your current chapter has unsaved changes.");
    expect(panel?.textContent).toContain("Save first to include these changes.");
  }
  const reviewButton = mounted.container.querySelector<HTMLButtonElement>(
    'button[aria-label="Run review"]',
  );
  const exportButton = mounted.container.querySelector<HTMLButtonElement>(".studio-inspector__export-format");
  expect(reviewButton).not.toBeDisabled();
  expect(exportButton).not.toBeDisabled();
  act(() => {
    reviewButton?.click();
    exportButton?.click();
  });
  expect(base.review.onRunReview).toHaveBeenCalledTimes(1);
  expect(onExport).toHaveBeenCalledWith("markdown");
  act(() => mounted.root.render(render(false)));
  expect(mounted.container.textContent).not.toContain("Your current chapter has unsaved changes.");
});
