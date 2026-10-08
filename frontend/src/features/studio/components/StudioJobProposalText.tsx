import { useTranslation } from "@/app/i18n/useTranslation";

/** Read-only job proposal text; copying never modifies the document. */
export function StudioJobProposalText({
  text,
  error,
}: {
  readonly text: string | null;
  readonly error: string | null;
}) {
  const { t } = useTranslation();
  return (
    <div className="studio-inspector__proposal">
      {error !== null ? (
        <p role="alert">{error}</p>
      ) : text !== null ? (
        <>
          <pre>{text}</pre>
          <button
            className="ui-command"
            onClick={() => {
              void navigator.clipboard.writeText(text);
            }}
            type="button"
          >
            {t("jobs.proposal.copy")}
          </button>
        </>
      ) : (
        <p role="status">{t("jobs.proposal.loading")}</p>
      )}
    </div>
  );
}
