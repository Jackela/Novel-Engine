import { Loader2 } from "lucide-react";
import type { RefObject } from "react";

interface ProjectLibraryLoadStateProps {
  readonly error: string | null;
  readonly isLoading: boolean;
  readonly commandsLocked: boolean;
  readonly headingRef: RefObject<HTMLHeadingElement | null>;
  readonly onRetry: (target: HTMLButtonElement, heading: () => HTMLElement | null) => void;
}

/** The pre-load surface: either the retryable bootstrap failure or the loader. */
export function ProjectLibraryLoadState({
  error,
  isLoading,
  commandsLocked,
  headingRef,
  onRetry,
}: ProjectLibraryLoadStateProps) {
  if (error !== null) {
    return (
      <div className="library__load-state">
        <p aria-live="assertive" className="ui-form-error" role="alert">
          {error}
        </p>
        <button
          aria-busy={isLoading || undefined}
          aria-label="Try again"
          className="ui-command ui-command--primary"
          disabled={isLoading || commandsLocked}
          onClick={(event) => onRetry(event.currentTarget, () => headingRef.current)}
          type="button"
        >
          {isLoading ? <Loader2 aria-hidden="true" className="ui-spin" /> : null}
          {isLoading ? "Trying again..." : "Try again"}
        </button>
      </div>
    );
  }
  return (
    <p aria-live="polite" className="library__load-state" role="status">
      <Loader2 aria-hidden="true" className="ui-spin" /> Loading projects...
    </p>
  );
}
