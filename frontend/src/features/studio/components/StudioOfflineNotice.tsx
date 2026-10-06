import { useSyncExternalStore } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

/**
 * DR-046: the studio shell's connectivity banner. `navigator.onLine` plus the
 * window `online`/`offline` events own the state, and the banner renders only
 * while the browser reports offline — recovery needs no dismiss action, the
 * notice disappears when the connection returns and the author retries the
 * failed action. Failure semantics: environments without `navigator` report
 * online, so a missing global can never fake an offline state.
 */
function subscribeConnectivity(listener: () => void): () => void {
  window.addEventListener("online", listener);
  window.addEventListener("offline", listener);
  return () => {
    window.removeEventListener("online", listener);
    window.removeEventListener("offline", listener);
  };
}

function isOnline(): boolean {
  return typeof navigator === "undefined" || navigator.onLine;
}

export function StudioOfflineNotice() {
  const online = useSyncExternalStore(subscribeConnectivity, isOnline);
  const { t } = useTranslation();
  if (online) return null;
  return (
    <div aria-live="polite" className="studio-offline" role="status">
      {t("shell.offline.notice")}
    </div>
  );
}
