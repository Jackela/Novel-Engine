import { type ReactNode, useLayoutEffect, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import { reportUnexpectedError } from "../hooks/reportUnexpectedError";

interface ClipboardCopyButtonProps {
  readonly text: string;
  readonly children?: ReactNode;
}

/** Resets feedback whenever the displayed text changes, including A/B/A switches. */
export function ClipboardCopyButton({ text, children }: ClipboardCopyButtonProps) {
  return (
    <ClipboardCopyAttempt key={text} text={text}>
      {children}
    </ClipboardCopyAttempt>
  );
}

/**
 * Copies only on explicit activation. Missing clipboard support and browser
 * permission refusals retain a readable manual-copy fallback; unexpected
 * failures also reach the diagnostic channel. Only the latest mounted attempt
 * may publish feedback, so a late permission result cannot follow another text.
 */
function ClipboardCopyAttempt({ text, children }: ClipboardCopyButtonProps) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<"copied" | "failed" | null>(null);
  const sequenceRef = useRef(0);
  useLayoutEffect(
    () => () => {
      sequenceRef.current += 1;
    },
    [],
  );

  const copy = async () => {
    const sequence = ++sequenceRef.current;
    setStatus(null);
    if (typeof navigator.clipboard?.writeText !== "function") {
      setStatus("failed");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      if (sequenceRef.current === sequence) setStatus("copied");
    } catch (reason) {
      if (
        !(reason instanceof DOMException) ||
        (reason.name !== "NotAllowedError" && reason.name !== "SecurityError")
      ) {
        reportUnexpectedError("Unexpected clipboard write failure.", reason);
      }
      if (sequenceRef.current === sequence) setStatus("failed");
    }
  };

  return (
    <>
      <button className="ui-command" onClick={() => void copy()} type="button">
        {children ?? t("common.action.copy")}
      </button>
      {status === "failed" ? (
        <p className="ui-form-error" role="alert">
          {t("common.copy.failed")}
        </p>
      ) : status === "copied" ? (
        <p role="status">{t("common.copy.copied")}</p>
      ) : null}
    </>
  );
}
