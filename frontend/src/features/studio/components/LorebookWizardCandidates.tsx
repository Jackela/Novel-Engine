import { useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import {
  LORE_ALIAS_MAX_COUNT,
  LORE_ALIAS_MAX_LENGTH,
  loreAliasLimitError,
} from "../hooks/lorebookConfirm";
import type { MergedLoreCandidate } from "../hooks/loreCandidateMerge";

interface LorebookWizardCandidatesProps {
  readonly candidates: MergedLoreCandidate[];
  readonly deselected: ReadonlySet<string>;
  readonly selectedCount: number;
  readonly aliasDrafts: Record<string, string>;
  readonly isConfirming: boolean;
  readonly aliasesFor: (candidate: MergedLoreCandidate) => string[];
  readonly onToggle: (key: string) => void;
  readonly onAliasDraft: (key: string, value: string) => void;
  readonly onConfirm: () => void | Promise<void>;
  readonly onAbandon: () => void;
}

/**
 * The wizard's review step (#614): the merged candidate list — kind, title,
 * editable aliases, summary preview — with per-candidate selection and the
 * confirm/abandon commands. Suggestions are session state only; confirming
 * runs the two existing steps per selected candidate, abandoning leaves the
 * project untouched. Confirming first pre-checks the alias write's fixed
 * limits so the author is told before the entry exists, instead of waiting
 * for the write's 422.
 */
export function LorebookWizardCandidates({
  candidates,
  deselected,
  selectedCount,
  aliasDrafts,
  isConfirming,
  aliasesFor,
  onToggle,
  onAliasDraft,
  onConfirm,
  onAbandon,
}: LorebookWizardCandidatesProps) {
  const { t } = useTranslation();
  const [confirmError, setConfirmError] = useState<string | null>(null);

  if (candidates.length === 0) return null;

  const confirm = (): void => {
    for (const candidate of candidates) {
      if (deselected.has(candidate.key)) continue;
      const limit = loreAliasLimitError(aliasesFor(candidate));
      if (limit !== null) {
        setConfirmError(
          limit === "count"
            ? t("lore.candidates.error.aliasCount", {
                title: candidate.title,
                count: String(LORE_ALIAS_MAX_COUNT),
              })
            : t("lore.candidates.error.aliasLength", {
                title: candidate.title,
                count: String(LORE_ALIAS_MAX_LENGTH),
              }),
        );
        return;
      }
    }
    setConfirmError(null);
    void onConfirm();
  };

  return (
    <section aria-label={t("lore.candidates.heading")} className="lore-wizard__section">
      <h3>{t("lore.candidates.heading")}</h3>
      <p className="lore-wizard__muted">{t("lore.candidates.hint")}</p>
      <ul className="lore-wizard__candidates">
        {candidates.map((candidate, index) => (
          <LoreCandidateRow
            key={candidate.key}
            aliasDraft={aliasDrafts[candidate.key] ?? candidate.aliases.join(", ")}
            candidate={candidate}
            isConfirming={isConfirming}
            isSelected={!deselected.has(candidate.key)}
            labelId={`lore-candidate-${index}`}
            onAliasDraft={onAliasDraft}
            onToggle={onToggle}
          />
        ))}
      </ul>
      {confirmError ? (
        <p aria-live="assertive" className="lore-wizard__error" role="alert">
          {confirmError}
        </p>
      ) : null}
      <div className="studio-inspector__actions">
        <button
          aria-busy={isConfirming}
          className="ui-command ui-command--primary"
          disabled={isConfirming || selectedCount === 0}
          onClick={confirm}
          type="button"
        >
          {isConfirming
            ? t("lore.candidates.action.confirming")
            : t("lore.candidates.action.confirm", { count: String(selectedCount) })}
        </button>
        <button className="ui-command" disabled={isConfirming} onClick={onAbandon} type="button">
          {t("lore.candidates.action.abandon")}
        </button>
      </div>
      <p aria-live="polite" className="sr-only">
        {isConfirming ? t("lore.candidates.action.confirming") : ""}
      </p>
    </section>
  );
}

interface LoreCandidateRowProps {
  readonly candidate: MergedLoreCandidate;
  readonly aliasDraft: string;
  readonly isConfirming: boolean;
  readonly isSelected: boolean;
  /** The checkbox's label target; index-based so a title can never mint an id with whitespace. */
  readonly labelId: string;
  readonly onToggle: (key: string) => void;
  readonly onAliasDraft: (key: string, value: string) => void;
}

function LoreCandidateRow({
  candidate,
  aliasDraft,
  isConfirming,
  isSelected,
  labelId,
  onToggle,
  onAliasDraft,
}: LoreCandidateRowProps) {
  const { t } = useTranslation();
  return (
    <li className="lore-wizard__candidate">
      <label className="lore-wizard__candidate-select">
        <input
          aria-labelledby={labelId}
          checked={isSelected}
          disabled={isConfirming}
          onChange={() => onToggle(candidate.key)}
          type="checkbox"
        />
        <span>
          <strong id={labelId}>{candidate.title}</strong>
          <span className="lore-wizard__muted">
            {candidate.kind === "character"
              ? t("lore.candidates.kind.character")
              : t("lore.candidates.kind.world")}
          </span>
        </span>
      </label>
      <label className="lore-wizard__candidate-aliases">
        <span>{t("lore.candidates.field.aliases")}</span>
        <input
          aria-label={`${t("lore.candidates.field.aliases")} — ${candidate.title}`}
          disabled={isConfirming}
          onChange={(event) => onAliasDraft(candidate.key, event.target.value)}
          type="text"
          value={aliasDraft}
        />
      </label>
      <details className="lore-wizard__candidate-summary">
        <summary>{t("lore.candidates.summary")}</summary>
        <p>{candidate.summary}</p>
      </details>
    </li>
  );
}
