import type { FormEvent } from "react";
import { useRef, useState } from "react";

import type { LoreStatus, StudioDocument } from "@/app/types/studio";

import { isLoreEntryKind } from "../studioConstants";

const LORE_STATUS_OPTIONS: Array<{ value: LoreStatus; label: string }> = [
  { value: "draft", label: "Draft (not injected)" },
  { value: "stable", label: "Stable (injected)" },
  { value: "deprecated", label: "Deprecated (not injected)" },
];

interface StudioLoreStatusPanelProps {
  document: StudioDocument | null;
  isSaving?: boolean;
  onStatusChange: (status: LoreStatus) => void | Promise<void>;
}

/**
 * The lore lifecycle-status selector (#444, ADR-0006): visible whenever the
 * active document is a lore entry (character/world). Status is document-level
 * state saved through the revision-free lore-status surface; only `stable`
 * entries join generation prompts.
 */
export function StudioLoreStatusPanel({
  document,
  isSaving = false,
  onStatusChange,
}: StudioLoreStatusPanelProps) {
  const saveButtonRef = useRef<HTMLButtonElement>(null);
  // Remounted per document via `key`; the saved status stays the source of
  // truth while the select drafts the next value.
  const [selectedStatus, setSelectedStatus] = useState<LoreStatus>(
    document?.lore_status ?? "draft",
  );

  if (document === null || !isLoreEntryKind(document.kind)) {
    return null;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await onStatusChange(selectedStatus);
    } finally {
      saveButtonRef.current?.focus();
    }
  };

  return (
    <form
      aria-busy={isSaving}
      aria-label="Lore status"
      className="studio-lore-status"
      onSubmit={(event) => void handleSubmit(event)}
    >
      <label className="studio-inspector__settings-field">
        <span>Lore status</span>
        <select
          aria-label="Lore status"
          disabled={isSaving}
          onChange={(event) => setSelectedStatus(event.target.value as LoreStatus)}
          value={selectedStatus}
        >
          {LORE_STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <p className="studio-lore-status__hint">
        Only stable entries are injected into generation prompts.
      </p>
      <div className="studio-inspector__actions">
        <button
          aria-busy={isSaving}
          className="ui-command ui-command--primary"
          disabled={isSaving || selectedStatus === document.lore_status}
          ref={saveButtonRef}
          type="submit"
        >
          {isSaving ? "Saving…" : "Save status"}
        </button>
      </div>
      <p aria-live="polite" className="sr-only">
        {isSaving ? "Saving lore status." : ""}
      </p>
    </form>
  );
}
