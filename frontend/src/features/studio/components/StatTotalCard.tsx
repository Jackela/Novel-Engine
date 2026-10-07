import type { MessageKey } from "@/app/i18n/dictionaries/en";
import { formatCount } from "@/app/i18n/format";
import { useTranslation } from "@/app/i18n/useTranslation";

interface StatTotalCardContract {
  /** The BEM block `usage.css` / `stats.css` style for this family's cards. */
  readonly className: string;
  /** The `{label}: {value}` template naming one card for assistive technology. */
  readonly ariaLabelKey: MessageKey;
}

/** Per-family card contract: the block and the a11y template never vary per card. */
const CARD_CONTRACTS = {
  usage: { className: "usage__total-card", ariaLabelKey: "usage.total.cardLabel" },
  stats: { className: "stats__total-card", ariaLabelKey: "stats.cardLabel" },
} as const satisfies Record<string, StatTotalCardContract>;

/** The panel family a card renders under (Usage #377, Writing stats #653). */
export type StatTotalCardFamily = keyof typeof CARD_CONTRACTS;

interface StatTotalCardProps {
  readonly family: StatTotalCardFamily;
  /** The visible label under the figure; the accessible name repeats it. */
  readonly labelKey: MessageKey;
  readonly value: number;
}

/**
 * One numeric summary card shared by the Usage (#377) and Writing stats
 * (#653) panels: the grouped figure over its label. The card is not a form
 * control, so it keeps `role="group"` with an explicit accessible name
 * instead of a `<fieldset>`, and that name spells the pair out (`{label}:
 * {value}`) because the visual order leads with the figure.
 *
 * Failure semantics: the value is always a defined number the owner has
 * already reduced — a missing figure is the owner's zero, never a placeholder
 * here — and `formatCount` groups it in the active language.
 */
export function StatTotalCard({ family, labelKey, value }: StatTotalCardProps) {
  const { t } = useTranslation();
  const label = t(labelKey);
  const contract = CARD_CONTRACTS[family];
  return (
    // biome-ignore lint/a11y/useSemanticElements: this stat card is not a form control group; <fieldset> would misrepresent semantics and drag in default fieldset styling.
    <div
      aria-label={t(contract.ariaLabelKey, { label, value: formatCount(value) })}
      className={contract.className}
      role="group"
    >
      <strong>{formatCount(value)}</strong>
      <span>{label}</span>
    </div>
  );
}
