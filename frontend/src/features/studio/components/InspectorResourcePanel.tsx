import { RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

import type { MessageKey } from "@/app/i18n/dictionaries/en";
import { useTranslation } from "@/app/i18n/useTranslation";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

/**
 * Every string the shell renders: the tab's heading and hint, the refresh
 * command's idle and busy labels, and the two fallback states a panel shows
 * while it has no published value.
 */
export interface InspectorResourcePanelLabels {
  readonly heading: MessageKey;
  readonly hint: MessageKey;
  readonly refresh: MessageKey;
  readonly refreshing: MessageKey;
  readonly loading: MessageKey;
  readonly empty: MessageKey;
}

interface InspectorResourcePanelProps<T> {
  readonly labels: InspectorResourcePanelLabels;
  /** The published value; `null` renders the fallback instead of the body. */
  readonly data: T | null;
  readonly isLoading: boolean;
  readonly error: string | null;
  readonly onRefresh: () => void | Promise<void>;
  /** The panel body, narrowed so a panel can never render it without data. */
  readonly renderBody: (data: T) => ReactNode;
}

/**
 * The shell every lazily loaded Inspector resource panel shares (#377 usage,
 * #653 writing stats): heading, hint and refresh command in one header, the
 * assertive error block under it, and the loading/empty fallback. Each panel
 * contributes only its own body, so the tab chrome, the refresh command's
 * busy labelling and the focus-restoration contract are stated once.
 *
 * Failure semantics: `error` renders above the body and above the fallback, so
 * a failed refresh keeps the last published value on screen; the refresh
 * command is disabled while `isLoading` and is the only focus-restoration
 * trigger, so a completed refresh returns focus to it unless the author moved
 * elsewhere first.
 */
export function InspectorResourcePanel<T>({
  labels,
  data,
  isLoading,
  error,
  onRefresh,
  renderBody,
}: InspectorResourcePanelProps<T>) {
  const { t } = useTranslation();
  const runRefreshWithFocusRestoration = useCommandFocusRestoration(isLoading);

  return (
    <div aria-busy={isLoading} className="studio-inspector__panel">
      <header className="studio-inspector__heading">
        <div>
          <h2>{t(labels.heading)}</h2>
          <p>{t(labels.hint)}</p>
        </div>
        <button
          aria-busy={isLoading}
          aria-label={isLoading ? t(labels.refreshing) : t(labels.refresh)}
          className="ui-command--icon"
          disabled={isLoading}
          onClick={(event) => {
            void runRefreshWithFocusRestoration(event.currentTarget, onRefresh);
          }}
          title={t(labels.refresh)}
          type="button"
        >
          <RefreshCw />
        </button>
      </header>
      {error ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          {error}
        </div>
      ) : null}
      {data === null ? (
        <p className="studio-inspector__empty">{isLoading ? t(labels.loading) : t(labels.empty)}</p>
      ) : (
        renderBody(data)
      )}
    </div>
  );
}
