import type { FormEvent } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { chapter, projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { StudioNavigator } from "./StudioNavigator";

const harness = createMountHarness();
const opening = chapter("doc-1", { title: "Opening", position: 1 });
const second = chapter("doc-2", { title: "Second", position: 2 });
const project = projectWith([opening, second]);

afterEach(() => harness.cleanup());

function navigator(overrides: {
  creatingDocumentKind?: "character";
  isCreatingDocument?: boolean;
  isMovingDocument?: boolean;
  movingDocument?: { documentId: string; direction: -1 | 1 };
}) {
  return harness.mount(
    <StudioNavigator
      project={project}
      section="manuscript"
      activeId={opening.id}
      search=""
      isSearching={false}
      searchResults={[]}
      onSearchChange={() => undefined}
      onSearchSubmit={(event: FormEvent) => event.preventDefault()}
      onNavigateSection={() => undefined}
      onSelectDocument={() => undefined}
      onCreateDocument={() => undefined}
      onMoveDocument={() => undefined}
      {...overrides}
    />,
  ).container;
}

describe("StudioNavigator pending command identity", () => {
  it("marks only the initiating create button busy while disabling its conflict group", () => {
    const container = navigator({
      creatingDocumentKind: "character",
      isCreatingDocument: true,
    });
    const initiator = container.querySelector<HTMLButtonElement>(
      '.studio-nav__document-group header button[aria-label="Adding Characters"]',
    );
    const conflicting = container.querySelector<HTMLButtonElement>(
      '.studio-nav__document-group header button[aria-label="Add Manuscript"]',
    );

    expect(initiator).toBeDisabled();
    expect(initiator).toHaveAttribute("aria-busy", "true");
    expect(conflicting).toBeDisabled();
    expect(conflicting).not.toHaveAttribute("aria-busy");
    expect(
      container.querySelectorAll('.studio-nav__document-group header button[aria-busy="true"]'),
    ).toHaveLength(1);
    expect(container.querySelectorAll(".document-row__order button:enabled")).toHaveLength(0);
  });

  it("marks only the exact move command busy while retaining every other command name", () => {
    const container = navigator({
      isMovingDocument: true,
      movingDocument: { documentId: opening.id, direction: 1 },
    });
    const initiator = container.querySelector<HTMLButtonElement>(
      'button[aria-label="Moving Opening down"]',
    );
    const conflicting = container.querySelector<HTMLButtonElement>(
      'button[aria-label="Move Second up"]',
    );

    expect(initiator).toBeDisabled();
    expect(initiator).toHaveAttribute("aria-busy", "true");
    expect(conflicting).toBeDisabled();
    expect(conflicting).not.toHaveAttribute("aria-busy");
    expect(
      container.querySelectorAll('.document-row__order button[aria-busy="true"]'),
    ).toHaveLength(1);
    expect(
      container.querySelectorAll('.studio-nav__document-group header button[aria-busy="true"]'),
    ).toHaveLength(0);
    expect(
      container.querySelectorAll(".studio-nav__document-group header button:enabled"),
    ).toHaveLength(0);
  });
});
