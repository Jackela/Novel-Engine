import { useLocation } from "react-router-dom";

import { useTranslation } from "@/app/i18n/useTranslation";
import { isSessionExpiredEntry } from "@/app/sessionExpiry";

/**
 * Entry-page explanation for the DR-020 forced return: a 401 on a signed-in
 * surface sends the author here, and the marker in the router state is the
 * only thing that tells this apart from a voluntary visit (first load or
 * sign-out), so those stay silent. Rendered for every entry state — even an
 * operational failure of the setup probe must not strand the author without
 * the reason they arrived. Failure semantics: an absent or malformed state
 * renders nothing rather than guessing.
 */
export function EntrySessionNotice() {
  const location = useLocation();
  const { t } = useTranslation();
  if (!isSessionExpiredEntry(location.state)) return null;
  return (
    <p aria-live="polite" className="entry__notice" role="status">
      {t("entry.notice.sessionExpired")}
    </p>
  );
}
