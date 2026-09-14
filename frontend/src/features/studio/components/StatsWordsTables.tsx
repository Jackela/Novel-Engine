import type { MessageKey } from "@/app/i18n/dictionaries/en";
import { useTranslation } from "@/app/i18n/useTranslation";
import type {
  WritingStatsDayRow,
  WritingStatsWeekRow,
  WritingStatsWords,
} from "@/app/types/studio";

const formatCount = (value: number) => value.toLocaleString("en-US");

function totalWords(words: WritingStatsWords): number {
  return words.author + words.ai_accepted + words.restore;
}

/**
 * A bucket is active when any source moved — a net-zero day (an author
 * write offset by a restore rollback) still shows its split, because the
 * movement itself is the content; only never-touched buckets stay implicit.
 */
function hasSourceMovement(words: WritingStatsWords): boolean {
  return words.author !== 0 || words.ai_accepted !== 0 || words.restore !== 0;
}

interface StatsWordsTableProps {
  /** The visible heading above the table. */
  headingKey: MessageKey;
  /** The accessible name of the table region. */
  regionKey: MessageKey;
  /** The first column's header (a UTC day key or the week's first day). */
  firstColumnKey: MessageKey;
  rows: ReadonlyArray<{ label: string; words: WritingStatsWords }>;
}

/**
 * One attributed-words table (#653): a calendar key plus the three-source
 * split and its total. Deltas are shown as-is — a negative author figure is
 * an honest cut, not an error.
 */
function StatsWordsTable({ headingKey, regionKey, firstColumnKey, rows }: StatsWordsTableProps) {
  const { t } = useTranslation();
  return (
    <section className="stats__section">
      <h3>{t(headingKey)}</h3>
      <table aria-label={t(regionKey)} className="stats__table">
        <thead>
          <tr>
            <th scope="col">{t(firstColumnKey)}</th>
            <th scope="col">{t("stats.words.author")}</th>
            <th scope="col">{t("stats.words.accepted")}</th>
            <th scope="col">{t("stats.words.restored")}</th>
            <th scope="col">{t("stats.words.total")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td>{row.label}</td>
              <td>{formatCount(row.words.author)}</td>
              <td>{formatCount(row.words.ai_accepted)}</td>
              <td>{formatCount(row.words.restore)}</td>
              <td>{formatCount(totalWords(row.words))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

interface StatsWordsTablesProps {
  /** The trailing-30-UTC-day rows, oldest first. */
  daily: WritingStatsDayRow[];
  /** The complete 7-UTC-day rollups within that window, oldest first. */
  weekly: WritingStatsWeekRow[];
}

/**
 * The daily and weekly attributed-words sections of the stats panel (#653).
 * Only buckets with source movement render — zero-filled days are the
 * aggregation's alignment contract, not content — and an entirely quiet
 * window renders the panel's defined empty state instead of two all-zero
 * tables. Both tables apply the same movement rule, so a net-zero day (an
 * author write offset by a restore rollback) stays visible in the daily
 * table while its week keeps rolling the signed figures into one sum.
 */
export function StatsWordsTables({ daily, weekly }: StatsWordsTablesProps) {
  const { t } = useTranslation();
  const activeDays = daily.filter((day) => hasSourceMovement(day.words));
  const activeWeeks = weekly.filter((week) => hasSourceMovement(week.words));
  if (activeDays.length === 0) {
    return <p className="studio-inspector__empty">{t("stats.empty")}</p>;
  }
  return (
    <>
      <StatsWordsTable
        headingKey="stats.daily.heading"
        regionKey="stats.daily.region"
        firstColumnKey="stats.table.day"
        rows={activeDays.map((day) => ({ label: day.date, words: day.words }))}
      />
      <StatsWordsTable
        headingKey="stats.weekly.heading"
        regionKey="stats.weekly.region"
        firstColumnKey="stats.table.week"
        rows={activeWeeks.map((week) => ({ label: week.start_date, words: week.words }))}
      />
    </>
  );
}
