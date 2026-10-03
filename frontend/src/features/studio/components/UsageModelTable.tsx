import { useTranslation } from "@/app/i18n/useTranslation";
import type { UsageModelRow } from "@/app/types/studio";

const formatCount = (value: number) => value.toLocaleString("en-US");

/**
 * Per-model usage detail table for the Usage inspector panel (#377, DR-028).
 * Token and request counts use locale thousands separators; completed
 * attempts, failed attempts, and estimated counts are separate columns so a
 * failure or an estimate is never folded into a provider token total.
 */
export function UsageModelTable({ rows }: { rows: UsageModelRow[] }) {
  const { t } = useTranslation();
  return (
    <table aria-label={t("usage.table.label")} className="usage__table">
      <thead>
        <tr>
          <th scope="col">{t("usage.table.model")}</th>
          <th scope="col">{t("usage.total.requests")}</th>
          <th scope="col">{t("usage.total.failedAttempts")}</th>
          <th scope="col">{t("usage.total.estimatedRequests")}</th>
          <th scope="col">{t("usage.total.promptTokens")}</th>
          <th scope="col">{t("usage.total.completionTokens")}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.model}>
            <th scope="row">{row.model}</th>
            <td>{formatCount(row.requests)}</td>
            <td>{formatCount(row.failed_attempts)}</td>
            <td>{formatCount(row.estimated_requests)}</td>
            <td>{formatCount(row.prompt_tokens)}</td>
            <td>{formatCount(row.completion_tokens)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
