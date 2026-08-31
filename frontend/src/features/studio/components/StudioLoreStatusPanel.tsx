import type { FormEvent, RefObject } from "react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { LORE_STATUS_OPTIONS } from "@/app/loreStatus";
import type { LoreStatus } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

interface StudioLoreStatusPanelProps {
  documentId: string;
  savedStatus: LoreStatus;
  attemptedStatus?: LoreStatus | null;
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
  attemptedStatus = null,
  isSaving = false,
  onSubmit,
}: StudioLoreStatusPanelProps) {
  const saveButtonRef = useRef<HTMLButtonElement>(null);
  const selectRef = useRef<HTMLSelectElement>(null);
  const activeDocumentIdRef = useRef(documentId);
  const runWithFocusRestoration = useCommandFocusRestoration(isSaving);

  useLayoutEffect(() => {
    activeDocumentIdRef.current = documentId;
  }, [documentId]);

  const submitWithFocusRestoration = useCallback(
    (trigger: HTMLButtonElement, status: LoreStatus) => {
      const originDocumentId = documentId;
      void runWithFocusRestoration(
        trigger,
        () => onSubmit(status),
        () => (activeDocumentIdRef.current === originDocumentId ? selectRef.current : null),
      );
    },
    [documentId, onSubmit, runWithFocusRestoration],
  );

  // The keyed form resets local selection at the document boundary, while the
  // persistent owner above can resolve a returning document's semantic target.
  return (
    <LoreStatusEntryForm
      key={documentId}
      savedStatus={savedStatus}
      attemptedStatus={attemptedStatus}
      isSaving={isSaving}
      onSubmit={submitWithFocusRestoration}
      saveButtonRef={saveButtonRef}
      selectRef={selectRef}
    />
  );
}

interface LoreStatusEntryFormProps {
  readonly savedStatus: LoreStatus;
  readonly attemptedStatus: LoreStatus | null;
  readonly isSaving: boolean;
  readonly onSubmit: (trigger: HTMLButtonElement, status: LoreStatus) => void;
  readonly saveButtonRef: RefObject<HTMLButtonElement | null>;
  readonly selectRef: RefObject<HTMLSelectElement | null>;
}

function LoreStatusEntryForm({
  savedStatus,
  attemptedStatus,
  isSaving,
  onSubmit,
  saveButtonRef,
  selectRef,
}: LoreStatusEntryFormProps) {
  const [selectedStatus, setSelectedStatus] = useState<LoreStatus>(attemptedStatus ?? savedStatus);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const saveButton = saveButtonRef.current;
    if (saveButton === null) {
      return;
    }
    onSubmit(saveButton, selectedStatus);
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
          ref={selectRef}
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
