import { type FormEvent, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { DocumentSummary } from "@/app/types/studio";
import type { LoreSegmentState } from "../hooks/useLorebookWizard";

interface LorebookWizardSegmentsProps {
  readonly documents: DocumentSummary[];
  readonly segments: LoreSegmentState[];
  readonly onSubmitPaste: (text: string) => void | Promise<void>;
  readonly onSubmitDocument: (document: DocumentSummary) => void | Promise<void>;
  readonly onRetrySegment: (segmentId: string) => void | Promise<void>;
}

/**
 * The wizard's input step (#614): one paste box plus one picker over the
 * already-imported chapter documents — each submission becomes its own
 * extraction segment — and the per-segment progress/failure list. Nothing is
 * persisted here; the segments are session state backed by audit-only jobs.
 */
export function LorebookWizardSegments({
  documents,
  segments,
  onSubmitPaste,
  onSubmitDocument,
  onRetrySegment,
}: LorebookWizardSegmentsProps) {
  const { t } = useTranslation();
  const [paste, setPaste] = useState("");
  const [documentId, setDocumentId] = useState("");
  const chapters = documents.filter((document) => document.kind === "chapter");
  const anyRunning = segments.some((segment) => segment.status === "running");
  const trimmed = paste.trim();

  const submitPaste = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (trimmed === "") return;
    setPaste("");
    void onSubmitPaste(paste);
  };

  const submitDocument = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const selected = chapters.find((document) => document.id === documentId);
    if (selected === undefined) return;
    void onSubmitDocument(selected);
  };

  return (
    <section aria-label={t("lore.input.heading")} className="lore-wizard__section">
      <h3>{t("lore.input.heading")}</h3>
      <form
        aria-label={t("lore.input.paste")}
        className="lore-wizard__paste"
        onSubmit={submitPaste}
      >
        <textarea
          aria-label={t("lore.input.paste")}
          aria-busy={anyRunning}
          onChange={(event) => setPaste(event.target.value)}
          rows={5}
          value={paste}
        />
        <button className="ui-command ui-command--primary" disabled={trimmed === ""} type="submit">
          {t("lore.input.action.extract")}
        </button>
      </form>
      {chapters.length > 0 ? (
        <form
          aria-label={t("lore.input.documents")}
          className="lore-wizard__documents"
          onSubmit={submitDocument}
        >
          <select
            aria-label={t("lore.input.documents")}
            onChange={(event) => setDocumentId(event.target.value)}
            value={documentId}
          >
            <option value="">{t("lore.input.documentsChoose")}</option>
            {chapters.map((chapter) => (
              <option key={chapter.id} value={chapter.id}>
                {chapter.title}
              </option>
            ))}
          </select>
          <button className="ui-command" disabled={documentId === ""} type="submit">
            {t("lore.input.action.extractDocument")}
          </button>
        </form>
      ) : (
        <p className="lore-wizard__muted">{t("lore.input.documentsNone")}</p>
      )}
      {segments.length > 0 ? (
        <ul aria-label={t("lore.segments.heading")} className="lore-wizard__segments">
          {segments.map((segment) => (
            <li key={segment.id}>
              <LoreSegmentRow segment={segment} onRetry={() => onRetrySegment(segment.id)} />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

interface LoreSegmentRowProps {
  readonly segment: LoreSegmentState;
  readonly onRetry: () => void | Promise<void>;
}

function LoreSegmentRow({ segment, onRetry }: LoreSegmentRowProps) {
  const { t } = useTranslation();
  const count = segment.candidates.length;
  return (
    <div className="lore-wizard__segment">
      <span>{segment.label}</span>
      {segment.status === "running" ? (
        <span aria-live="polite" className="lore-wizard__muted">
          {t("lore.segment.status.running")}
        </span>
      ) : null}
      {segment.status === "completed" ? (
        <span className="lore-wizard__muted">
          {t("lore.segment.status.completed", { count: String(count) })}
        </span>
      ) : null}
      {segment.status === "failed" ? (
        <>
          <span className="lore-wizard__error" role="alert">
            {segment.error ?? t("lore.segment.status.failed")}
          </span>
          <button className="ui-command" onClick={() => void onRetry()} type="button">
            {t("lore.segment.action.retry")}
          </button>
        </>
      ) : null}
    </div>
  );
}
