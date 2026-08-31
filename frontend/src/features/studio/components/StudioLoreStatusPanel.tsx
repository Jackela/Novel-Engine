import type { FormEvent } from "react";
import { useEffect, useRef, useState } from "react";

import { LORE_STATUS_OPTIONS } from "@/app/loreStatus";
import type { LoreStatus } from "@/app/types/studio";

interface StudioLoreStatusPanelProps {
  documentId: string;
  savedStatus: LoreStatus;
  isSaving?: boolean;
  onSubmit: (status: LoreStatus) => Promise<void>;
}

/**
 * The lore lifecycle-status selector (#444, ADR-0006): visible whenever the
 * active document is a lore entry (character/world). Status is document-level
 * state saved through the revision-free lore-status surface; only `stable`
 * entries join generation prompts.
 */
export function StudioLoreStatusPanel({
  documentId,
  savedStatus,
  isSaving = false,
  onSubmit,
}: StudioLoreStatusPanelProps) {
  // Identity is enforced inside the public module; callers cannot forget the
  // reset boundary when the active Lore document changes.
  return (
    <LoreStatusEntryForm
      key={documentId}
      savedStatus={savedStatus}
      isSaving={isSaving}
      onSubmit={onSubmit}
    />
  );
}

type LoreStatusEntryFormProps = Omit<StudioLoreStatusPanelProps, "documentId">;

function LoreStatusEntryForm({
  savedStatus,
  isSaving = false,
  onSubmit,
}: LoreStatusEntryFormProps) {
  const saveButtonRef = useRef<HTMLButtonElement>(null);
  const handledFocusRequestRef = useRef(0);
  const [focusRequest, setFocusRequest] = useState(0);
  const [selectedStatus, setSelectedStatus] = useState<LoreStatus>(savedStatus);

  useEffect(() => {
    if (focusRequest !== handledFocusRequestRef.current && !isSaving) {
      handledFocusRequestRef.current = focusRequest;
      saveButtonRef.current?.focus();
    }
  }, [focusRequest, isSaving]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await onSubmit(selectedStatus);
    } finally {
      // The mutation Promise may settle before React commits isSaving=false.
      // Request focus through an effect so disabled controls are never targeted.
      setFocusRequest((request) => request + 1);
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
          disabled={isSaving || selectedStatus === savedStatus}
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
