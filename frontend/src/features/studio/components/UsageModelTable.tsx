import type { UsageModelRow } from "@/app/types/studio";

const formatCount = (value: number) => value.toLocaleString("en-US");

/**
 * Per-model usage detail table for the Usage inspector panel (#377).
 * Token and request counts use locale thousands separators.
 */
export function UsageModelTable({ rows }: { rows: UsageModelRow[] }) {
  return (
    <table aria-label="Usage per model" className="usage__table">
      <thead>
        <tr>
          <th scope="col">Model</th>
          <th scope="col">Requests</th>
          <th scope="col">Prompt tokens</th>
          <th scope="col">Completion tokens</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.model}>
            <th scope="row">{row.model}</th>
            <td>{formatCount(row.requests)}</td>
            <td>{formatCount(row.prompt_tokens)}</td>
            <td>{formatCount(row.completion_tokens)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
