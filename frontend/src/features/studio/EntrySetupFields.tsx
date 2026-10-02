import { useTranslation } from "@/app/i18n/useTranslation";

interface EntrySetupFieldsProps {
  readonly busy: boolean;
  readonly confirmPassword: string;
  readonly mismatchVisible: boolean;
  readonly onConfirmPasswordChange: (value: string) => void;
  readonly onSetupTokenChange: (value: string) => void;
  readonly setupToken: string;
}

/**
 * First-run-only entry fields: the password confirmation that catches a
 * mistyped single-account lockout before it reaches the server (DR-019), and
 * the optional DR-008 first-start setup token the browser previously could
 * not send. Rendered only while no Owner exists; the mismatch message is a
 * client-side refusal, never a server round trip. Failure semantics: the
 * confirmation never gates the login form, which has no confirmation field.
 */
export function EntrySetupFields({
  busy,
  confirmPassword,
  mismatchVisible,
  onConfirmPasswordChange,
  onSetupTokenChange,
  setupToken,
}: EntrySetupFieldsProps) {
  const { t } = useTranslation();
  return (
    <>
      <label>
        <span>{t("entry.field.confirmPassword")}</span>
        <input
          autoComplete="new-password"
          disabled={busy}
          minLength={10}
          onChange={(event) => onConfirmPasswordChange(event.target.value)}
          required
          type="password"
          value={confirmPassword}
        />
      </label>
      {mismatchVisible ? (
        <p aria-live="assertive" className="ui-form-error" role="alert">
          {t("entry.error.passwordMismatch")}
        </p>
      ) : null}
      <label>
        <span>{t("entry.field.setupToken")}</span>
        <input
          autoComplete="off"
          disabled={busy}
          onChange={(event) => onSetupTokenChange(event.target.value)}
          value={setupToken}
        />
      </label>
      <p className="entry__hint">{t("entry.hint.setupToken")}</p>
    </>
  );
}
